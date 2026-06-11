from __future__ import annotations

from dataclasses import dataclass
import logging
import os
from pathlib import Path
from typing import ClassVar, Sequence

from app.core.config import Settings


logger = logging.getLogger(__name__)

DEFAULT_PROTECTED_TERMS = [
    "휠체어",
    "전동휠체어",
    "유모차",
    "유아차",
    "무장애",
    "점자",
    "점자블록",
    "점자 안내",
    "촉지도",
    "수어",
    "수어 안내",
    "수화",
    "자막",
    "보조견",
    "안내견",
    "오디오가이드",
    "장애인",
    "장애인 화장실",
    "장애인 주차",
    "경사로",
    "엘리베이터",
    "승강기",
    "수유실",
    "기저귀",
    "청원군",
    "마산시",
    "진해시",
    "남제주군",
    "북제주군",
]


@dataclass(frozen=True)
class ExternalCorrectionResult:
    raw_text: str
    corrected_text: str
    accepted: bool
    provider: str
    model: str | None = None
    reason: str | None = None
    damaged_terms: list[str] | None = None

    @property
    def changed(self) -> bool:
        return self.raw_text != self.corrected_text


class ExternalKoreanCorrector:
    """Optional Korean typo/spacing corrector with domain term protection.

    The corrected text is a candidate input only. It must not replace the raw
    user text because sequence-to-sequence correctors can over-normalize names,
    accessibility terms, or intent markers.
    """

    _shared_load_errors: ClassVar[dict[tuple[str, bool], str]] = {}

    def __init__(self, settings: Settings):
        self.settings = settings
        self.provider = settings.tourism_korean_correction_provider
        self.model_name = settings.tourism_korean_correction_model
        self._loaded = False
        self._load_error: str | None = None
        self._tokenizer = None
        self._model = None
        self._torch = None
        self._device = "cpu"

    def correct(self, text: str, protected_terms: Sequence[str] | None = None) -> ExternalCorrectionResult:
        raw = " ".join(str(text or "").strip().split())
        if not raw:
            return ExternalCorrectionResult(raw, raw, False, provider=self.provider, model=self.model_name, reason="empty")
        if len(raw) > self.settings.tourism_korean_correction_max_chars:
            return ExternalCorrectionResult(raw, raw, False, provider=self.provider, model=self.model_name, reason="too_long")
        if self.provider == "quickspacer":
            corrected = self._quickspace(raw)
            accepted, reason, damaged = self._accept(raw, corrected, protected_terms or [])
            return ExternalCorrectionResult(
                raw_text=raw,
                corrected_text=corrected,
                accepted=accepted,
                provider=self.provider,
                model="quickspacer",
                reason=reason,
                damaged_terms=damaged,
            )
        if self.provider != "hf_seq2seq":
            return ExternalCorrectionResult(raw, raw, False, provider=self.provider, model=self.model_name, reason="provider_disabled")
        if not self._ensure_loaded():
            return ExternalCorrectionResult(
                raw,
                raw,
                False,
                provider=self.provider,
                model=self.model_name,
                reason=f"load_failed:{self._load_error or 'unknown'}",
            )

        corrected = self._generate(raw)
        accepted, reason, damaged = self._accept(raw, corrected, protected_terms or [])
        return ExternalCorrectionResult(
            raw_text=raw,
            corrected_text=corrected,
            accepted=accepted,
            provider=self.provider,
            model=self.model_name,
            reason=reason,
            damaged_terms=damaged,
        )

    def _ensure_loaded(self) -> bool:
        if self._loaded:
            return True
        if self._load_error:
            return False
        local_files_only = not self.settings.tourism_korean_correction_allow_download
        load_key = (self.model_name, local_files_only)
        if load_key in self._shared_load_errors:
            self._load_error = self._shared_load_errors[load_key]
            return False
        model_path = Path(self.model_name)
        if local_files_only and (model_path.is_absolute() or self.model_name.startswith("data/")):
            if not model_path.exists():
                self._load_error = "local_model_missing"
                self._shared_load_errors[load_key] = self._load_error
                return False
        try:
            if local_files_only:
                os.environ.setdefault("HF_HUB_OFFLINE", "1")
                os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
            import torch
            from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

            self._torch = torch
            self._tokenizer = AutoTokenizer.from_pretrained(self.model_name, local_files_only=local_files_only)
            use_safetensors = None
            if model_path.exists():
                has_safetensors = (model_path / "model.safetensors").exists()
                has_pytorch_bin = (model_path / "pytorch_model.bin").exists()
                use_safetensors = True if has_safetensors and not has_pytorch_bin else False
            self._model = AutoModelForSeq2SeqLM.from_pretrained(
                self.model_name,
                local_files_only=local_files_only,
                use_safetensors=use_safetensors,
            )
            self._device = self._resolve_device(self.settings.tourism_korean_correction_device)
            self._model.to(self._device)
            self._model.eval()
            self._loaded = True
            return True
        except Exception as exc:  # pragma: no cover - depends on optional local model setup
            self._load_error = exc.__class__.__name__
            self._shared_load_errors[load_key] = self._load_error
            logger.warning("Korean external correction model failed to load: %s", exc)
            return False

    def _quickspace(self, text: str) -> str:
        try:
            from quickspacer import Spacer

            if not hasattr(self, "_quickspacer"):
                self._quickspacer = Spacer()
            spaced = self._quickspacer.space([text])
            if isinstance(spaced, list):
                return str(spaced[0]).strip() if spaced else text
            return str(spaced).strip()
        except Exception as exc:  # pragma: no cover - optional candidate dependency
            logger.warning("quickspacer correction failed: %s", exc)
            return text

    def _resolve_device(self, configured_device: str) -> str:
        if configured_device != "auto":
            return configured_device
        if self._torch.cuda.is_available():
            return "cuda"
        if getattr(self._torch.backends, "mps", None) and self._torch.backends.mps.is_available():
            return "mps"
        return "cpu"

    def _generate(self, text: str) -> str:
        prompt = "맞춤법을 고쳐주세요: " + text
        encoding = self._tokenizer(
            prompt,
            return_tensors="pt",
            truncation=True,
            max_length=self.settings.tourism_korean_correction_max_length,
        )
        input_ids = encoding.input_ids.to(self._device)
        attention_mask = encoding.attention_mask.to(self._device)
        generation_kwargs = {
            "max_length": self.settings.tourism_korean_correction_max_length,
            "num_beams": self.settings.tourism_korean_correction_num_beams,
        }
        if self.settings.tourism_korean_correction_num_beams > 1:
            generation_kwargs["early_stopping"] = True
        with self._torch.no_grad():
            output = self._model.generate(
                input_ids=input_ids,
                attention_mask=attention_mask,
                **generation_kwargs,
            )
        return self._tokenizer.decode(output[0], skip_special_tokens=True).strip()

    @staticmethod
    def _accept(raw: str, corrected: str, protected_terms: Sequence[str]) -> tuple[bool, str, list[str]]:
        if not corrected:
            return False, "empty_correction", []
        raw_compact = _compact(raw)
        corrected_compact = _compact(corrected)
        if corrected_compact == raw_compact:
            return True, "unchanged_or_spacing_only", []
        if len(corrected_compact) < max(2, int(len(raw_compact) * 0.55)):
            return False, "too_short", []
        if len(corrected_compact) > max(8, int(len(raw_compact) * 1.8)):
            return False, "too_long", []
        damaged = damaged_terms(raw, corrected, protected_terms)
        if damaged:
            return False, "protected_term_damaged", damaged
        return True, "accepted", []


def damaged_terms(before: str, after: str, protected_terms: Sequence[str]) -> list[str]:
    before_compact = _compact(before)
    after_compact = _compact(after)
    damaged: list[str] = []
    for term in protected_terms:
        normalized_term = _compact(term)
        if normalized_term and normalized_term in before_compact and normalized_term not in after_compact:
            damaged.append(term)
    return damaged


def _compact(text: str) -> str:
    return "".join(str(text or "").split()).lower()
