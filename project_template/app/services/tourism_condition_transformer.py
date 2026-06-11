from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Sequence

from app.core.config import Settings


logger = logging.getLogger(__name__)


class TourismConditionTransformer:
    """Local multi-label condition classifier candidate.

    This is disabled by default. It is intended for controlled eval runs before
    any runtime adoption, because over-predicting conditions can harm card
    quality more than it helps label recall.
    """

    def __init__(self, settings: Settings, labels: Sequence[str]):
        self.settings = settings
        self.labels = list(labels)
        self.model_name = settings.tourism_condition_transformer_model
        self.metrics_path = settings.tourism_condition_transformer_metrics_path
        self.thresholds = self._load_thresholds(self.metrics_path)
        self._loaded = False
        self._load_error: str | None = None
        self._tokenizer = None
        self._model = None
        self._torch = None
        self._device = "cpu"

    def predict(self, text: str) -> dict[str, Any]:
        raw = str(text or "").strip()
        if not raw:
            return {"labels": [], "confidence_by_label": {}, "reason": "empty"}
        if not self._ensure_loaded():
            return {"labels": [], "confidence_by_label": {}, "reason": f"load_failed:{self._load_error or 'unknown'}"}
        encoding = self._tokenizer(
            raw,
            return_tensors="pt",
            truncation=True,
            max_length=self.settings.tourism_condition_transformer_max_length,
        )
        inputs = {key: value.to(self._device) for key, value in encoding.items()}
        with self._torch.no_grad():
            output = self._model(**inputs)
        probabilities = self._torch.sigmoid(output.logits)[0].detach().cpu().tolist()
        confidence_by_label = {label: float(probability) for label, probability in zip(self.labels, probabilities, strict=True)}
        labels = [
            label
            for label, probability in confidence_by_label.items()
            if probability >= self.thresholds.get(label, 0.5)
        ]
        return {"labels": labels, "confidence_by_label": confidence_by_label, "reason": "ok"}

    def _ensure_loaded(self) -> bool:
        if self._loaded:
            return True
        if self._load_error:
            return False
        model_path = Path(self.model_name)
        if not model_path.exists():
            self._load_error = "local_model_missing"
            return False
        try:
            import torch
            from transformers import AutoModelForSequenceClassification, AutoTokenizer

            self._torch = torch
            self._tokenizer = AutoTokenizer.from_pretrained(self.model_name, local_files_only=True)
            self._model = AutoModelForSequenceClassification.from_pretrained(self.model_name, local_files_only=True)
            self._device = self._resolve_device()
            self._model.to(self._device)
            self._model.eval()
            self._loaded = True
            return True
        except Exception as exc:  # pragma: no cover - optional local model setup
            self._load_error = exc.__class__.__name__
            logger.warning("Tourism condition transformer failed to load: %s", exc)
            return False

    def _resolve_device(self) -> str:
        configured = self.settings.tourism_condition_transformer_device
        if configured != "auto":
            return configured
        if self._torch.cuda.is_available():
            return "cuda"
        if getattr(self._torch.backends, "mps", None) and self._torch.backends.mps.is_available():
            return "mps"
        return "cpu"

    def _load_thresholds(self, metrics_path: Path) -> dict[str, float]:
        if not metrics_path.exists():
            return {label: 0.5 for label in self.labels}
        try:
            payload = json.loads(metrics_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {label: 0.5 for label in self.labels}
        raw_thresholds = payload.get("thresholds") or {}
        return {label: float(raw_thresholds.get(label, 0.5)) for label in self.labels}
