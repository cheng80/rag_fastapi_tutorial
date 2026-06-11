from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import sys
import time
from typing import Any, Callable


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.services.korean_query_normalizer import KoreanQueryNormalizer  # noqa: E402
from app.services.tourism_context_classifier import CONTEXT_LABELS, TourismContextClassifier  # noqa: E402


DEFAULT_INPUT = PROJECT_ROOT / "data" / "processed" / "tourism_context_llm_hard_training_20260517_human_light_1000.valid.jsonl"
DEFAULT_OUTPUT = PROJECT_ROOT / "data" / "generated" / "tour_api" / "korean_correction_candidates" / "audit.json"
DEFAULT_SAMPLES_OUTPUT = PROJECT_ROOT / "data" / "generated" / "tour_api" / "korean_correction_candidates" / "samples.jsonl"
DEFAULT_HF_MODEL = "j5ng/et5-typos-corrector"

PROTECTED_TERMS = [
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


def project_relative(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path)


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        rows.append(json.loads(line))
    return rows


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        for row in rows:
            file.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def compact(text: str) -> str:
    return "".join(str(text or "").split()).lower()


def load_region_terms() -> list[str]:
    path = PROJECT_ROOT / "data" / "processed" / "tour_area_codes.json"
    if not path.exists():
        return []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    terms: set[str] = set()
    for area in payload.get("areas") or []:
        area_name = str(area.get("name") or "").strip()
        if area_name:
            terms.add(area_name)
        for sigungu in area.get("sigungu") or []:
            name = str(sigungu.get("name") or "").strip()
            if name:
                terms.add(name)
                if area_name:
                    terms.add(f"{area_name} {name}")
    return sorted(terms, key=len, reverse=True)


def damaged_terms(before: str, after: str, protected_terms: list[str]) -> list[str]:
    before_compact = compact(before)
    after_compact = compact(after)
    damaged: list[str] = []
    for term in protected_terms:
        normalized_term = compact(term)
        if normalized_term and normalized_term in before_compact and normalized_term not in after_compact:
            damaged.append(term)
    return damaged


class HuggingFaceTypoCorrector:
    def __init__(self, model_name: str, device: str, max_length: int, num_beams: int):
        import torch
        from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

        self.torch = torch
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModelForSeq2SeqLM.from_pretrained(model_name)
        self.max_length = max_length
        self.num_beams = num_beams
        self.device = self._resolve_device(device)
        self.model.to(self.device)
        self.model.eval()

    def _resolve_device(self, device: str) -> str:
        if device != "auto":
            return device
        if self.torch.cuda.is_available():
            return "cuda"
        if getattr(self.torch.backends, "mps", None) and self.torch.backends.mps.is_available():
            return "mps"
        return "cpu"

    def __call__(self, text: str) -> str:
        prompt = "맞춤법을 고쳐주세요: " + text
        encoding = self.tokenizer(prompt, return_tensors="pt", truncation=True, max_length=self.max_length)
        input_ids = encoding.input_ids.to(self.device)
        attention_mask = encoding.attention_mask.to(self.device)
        with self.torch.no_grad():
            output = self.model.generate(
                input_ids=input_ids,
                attention_mask=attention_mask,
                max_length=self.max_length,
                num_beams=self.num_beams,
                early_stopping=True,
            )
        return self.tokenizer.decode(output[0], skip_special_tokens=True).strip()


def metric_from_records(records: list[dict[str, Any]], key: str) -> dict[str, Any]:
    exact = 0
    total_expected = 0
    total_predicted = 0
    total_correct = 0
    per_label: dict[str, Counter[str]] = {label: Counter() for label in CONTEXT_LABELS}
    for record in records:
        expected = set(record["expected"])
        predicted = set(record[key])
        exact += int(expected == predicted)
        total_expected += len(expected)
        total_predicted += len(predicted)
        total_correct += len(expected & predicted)
        for label in CONTEXT_LABELS:
            if label in expected and label in predicted:
                per_label[label]["tp"] += 1
            elif label not in expected and label in predicted:
                per_label[label]["fp"] += 1
            elif label in expected and label not in predicted:
                per_label[label]["fn"] += 1
    precision = total_correct / total_predicted if total_predicted else 1.0
    recall = total_correct / total_expected if total_expected else 1.0
    f1 = (2 * precision * recall / (precision + recall)) if precision + recall else 0.0
    return {
        "exact_match": round(exact / len(records), 4) if records else 0.0,
        "micro_precision": round(precision, 4),
        "micro_recall": round(recall, 4),
        "micro_f1": round(f1, 4),
        "mismatch_rows": len(records) - exact,
        "per_label": {label: dict(counts) for label, counts in per_label.items()},
    }


def build_records(
    rows: list[dict[str, Any]],
    classifier: TourismContextClassifier,
    normalizer: KoreanQueryNormalizer,
    external_corrector: Callable[[str], str] | None,
    protected_terms: list[str],
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for row in rows:
        raw = str(row.get("text") or "")
        expected = [label for label in CONTEXT_LABELS if label in set(row.get("labels") or [])]
        domain = normalizer.normalize(raw)
        external = external_corrector(raw) if external_corrector else raw
        external_domain = normalizer.normalize(external)
        external_damage = damaged_terms(raw, external, protected_terms)
        external_domain_damage = damaged_terms(raw, external_domain.normalized_text, protected_terms)
        safe_external = raw if external_damage else external
        safe_external_domain = domain.normalized_text if external_domain_damage else external_domain.normalized_text

        raw_labels = classifier.predict(raw).labels
        domain_labels = classifier.predict(domain.normalized_text).labels
        external_labels = classifier.predict(external).labels
        external_domain_labels = classifier.predict(external_domain.normalized_text).labels
        safe_external_labels = classifier.predict(safe_external).labels
        safe_external_domain_labels = classifier.predict(safe_external_domain).labels
        records.append(
            {
                "id": row.get("id"),
                "category": row.get("category"),
                "risk_tags": row.get("risk_tags") or [],
                "raw_text": raw,
                "domain_normalized_text": domain.normalized_text,
                "external_corrected_text": external,
                "external_then_domain_text": external_domain.normalized_text,
                "safe_external_text": safe_external,
                "safe_external_then_domain_text": safe_external_domain,
                "domain_corrections": domain.corrections,
                "domain_risk_tags": domain.risk_tags,
                "external_damaged_terms": external_damage,
                "external_then_domain_damaged_terms": external_domain_damage,
                "expected": expected,
                "raw_labels": raw_labels,
                "domain_labels": domain_labels,
                "external_labels": external_labels,
                "external_then_domain_labels": external_domain_labels,
                "safe_external_labels": safe_external_labels,
                "safe_external_then_domain_labels": safe_external_domain_labels,
            }
        )
    return records


def summarize_changes(records: list[dict[str, Any]], key: str, text_key: str) -> dict[str, Any]:
    raw_exact = [set(record["raw_labels"]) == set(record["expected"]) for record in records]
    candidate_exact = [set(record[key]) == set(record["expected"]) for record in records]
    return {
        "changed_text_rows": sum(1 for record in records if record["raw_text"] != record[text_key]),
        "improved_rows_vs_raw": sum(1 for raw_ok, candidate_ok in zip(raw_exact, candidate_exact, strict=True) if not raw_ok and candidate_ok),
        "worsened_rows_vs_raw": sum(1 for raw_ok, candidate_ok in zip(raw_exact, candidate_exact, strict=True) if raw_ok and not candidate_ok),
        "label_changed_rows_vs_raw": sum(1 for record in records if set(record["raw_labels"]) != set(record[key])),
    }


def build_samples(records: list[dict[str, Any]], max_samples: int) -> list[dict[str, Any]]:
    damage_samples: list[dict[str, Any]] = []
    interesting: list[dict[str, Any]] = []
    for record in records:
        raw_ok = set(record["raw_labels"]) == set(record["expected"])
        external_ok = set(record["external_labels"]) == set(record["expected"])
        external_domain_ok = set(record["external_then_domain_labels"]) == set(record["expected"])
        if record["external_damaged_terms"] or record["external_then_domain_damaged_terms"]:
            damage_samples.append(record)
        elif (
            record["raw_text"] != record["external_corrected_text"]
            or raw_ok != external_ok
            or raw_ok != external_domain_ok
        ):
            interesting.append(record)
    return (damage_samples + interesting)[:max_samples]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate professional Korean typo/spacing correction candidates before runtime adoption.")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--samples-output", type=Path, default=DEFAULT_SAMPLES_OUTPUT)
    parser.add_argument("--limit", type=int, default=120)
    parser.add_argument("--sample-limit", type=int, default=80)
    parser.add_argument("--hf-model", default="")
    parser.add_argument("--use-default-hf-model", action="store_true")
    parser.add_argument("--device", default="auto")
    parser.add_argument("--max-length", type=int, default=128)
    parser.add_argument("--num-beams", type=int, default=3)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    rows = load_jsonl(args.input)
    if args.limit > 0:
        rows = rows[: args.limit]

    model_name = args.hf_model or (DEFAULT_HF_MODEL if args.use_default_hf_model else "")
    external_corrector: Callable[[str], str] | None = None
    external_status: dict[str, Any] = {"enabled": False}
    if model_name:
        started = time.perf_counter()
        external_corrector = HuggingFaceTypoCorrector(
            model_name=model_name,
            device=args.device,
            max_length=args.max_length,
            num_beams=args.num_beams,
        )
        external_status = {
            "enabled": True,
            "model": model_name,
            "load_seconds": round(time.perf_counter() - started, 3),
        }

    classifier = TourismContextClassifier()
    normalizer = KoreanQueryNormalizer()
    protected_terms = sorted(set(PROTECTED_TERMS + load_region_terms()), key=len, reverse=True)
    started = time.perf_counter()
    records = build_records(rows, classifier, normalizer, external_corrector, protected_terms)
    elapsed = time.perf_counter() - started

    metrics = {
        "raw": metric_from_records(records, "raw_labels"),
        "domain_normalizer": metric_from_records(records, "domain_labels"),
        "external_corrector": metric_from_records(records, "external_labels"),
        "external_then_domain": metric_from_records(records, "external_then_domain_labels"),
        "safe_external_corrector": metric_from_records(records, "safe_external_labels"),
        "safe_external_then_domain": metric_from_records(records, "safe_external_then_domain_labels"),
    }
    audit = {
        "input": project_relative(args.input),
        "rows": len(records),
        "elapsed_seconds": round(elapsed, 3),
        "seconds_per_row": round(elapsed / len(records), 4) if records else 0.0,
        "external_corrector": external_status,
        "protected_term_count": len(protected_terms),
        "metrics": metrics,
        "change_summary": {
            "domain_normalizer": summarize_changes(records, "domain_labels", "domain_normalized_text"),
            "external_corrector": summarize_changes(records, "external_labels", "external_corrected_text"),
            "external_then_domain": summarize_changes(records, "external_then_domain_labels", "external_then_domain_text"),
            "safe_external_corrector": summarize_changes(records, "safe_external_labels", "safe_external_text"),
            "safe_external_then_domain": summarize_changes(
                records,
                "safe_external_then_domain_labels",
                "safe_external_then_domain_text",
            ),
        },
        "damage_summary": {
            "external_damaged_rows": sum(1 for record in records if record["external_damaged_terms"]),
            "external_then_domain_damaged_rows": sum(1 for record in records if record["external_then_domain_damaged_terms"]),
            "top_external_damaged_terms": Counter(term for record in records for term in record["external_damaged_terms"]).most_common(20),
            "top_external_then_domain_damaged_terms": Counter(
                term for record in records for term in record["external_then_domain_damaged_terms"]
            ).most_common(20),
            "damage_samples": [
                {
                    "id": record.get("id"),
                    "raw_text": record["raw_text"],
                    "external_corrected_text": record["external_corrected_text"],
                    "external_then_domain_text": record["external_then_domain_text"],
                    "external_damaged_terms": record["external_damaged_terms"],
                    "external_then_domain_damaged_terms": record["external_then_domain_damaged_terms"],
                }
                for record in records
                if record["external_damaged_terms"] or record["external_then_domain_damaged_terms"]
            ][:20],
        },
        "adoption_policy": {
            "runtime_adoption": "do_not_adopt_automatically",
            "required_before_runtime": [
                "external_then_domain micro_f1 must exceed raw and domain_normalizer on a fresh blind set",
                "protected term damage must be zero or explicitly allow-listed",
                "actual /tourism/chat card evaluation must not regress",
            ],
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(audit, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    write_jsonl(args.samples_output, build_samples(records, args.sample_limit))
    print(
        json.dumps(
            {
                "output": project_relative(args.output),
                "samples_output": project_relative(args.samples_output),
                "rows": len(records),
                "external_enabled": bool(model_name),
                "metrics": metrics,
                "damage_summary": audit["damage_summary"],
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
