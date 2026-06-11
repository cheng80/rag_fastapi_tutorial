from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import time
from typing import Any

import requests


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.services.tourism_context_classifier import CONTEXT_LABELS  # noqa: E402
from scripts.eval_tourism_context_classifier import (  # noqa: E402
    DEFAULT_INPUT,
    DEFAULT_TRAIN,
    evaluate_predictions,
    load_rows,
    predict_hybrid_linear,
    train_linear_model,
)


DEFAULT_MODEL = "hf.co/mradermacher/supergemma4-e4b-abliterated-i1-GGUF:Q4_K_M"
DEFAULT_OUTPUT = PROJECT_ROOT / "data" / "generated" / "tour_api" / "supergemma_context_eval_latest.json"

LABEL_DESCRIPTIONS = {
    "strict_and": "둘 다/모두/반드시 만족해야 하는 조건",
    "soft_and": "여러 조건을 말했지만 일부만 만족해도 되는 완화 조건",
    "or_condition": "A 또는 B, 하나라도 되면 되는 조건",
    "add_condition": "이전 추천에 조건을 추가하는 후속 발화",
    "replace_condition": "이전 지역/조건/선호를 새 기준으로 교체하는 발화",
    "exclude_condition": "특정 조건/장소 유형을 제외하는 발화",
    "family_context": "아이/가족/영유아/동반자 맥락",
    "mobility_context": "걷기 힘듦/이동 편함/계단 회피/휠체어/유모차 이동 맥락",
    "specific_facility_required": "점자블록/주차/화장실/수유실처럼 카드 근거가 필요한 세부 시설 요구",
}


def extract_json_object(text: str) -> dict[str, Any] | None:
    stripped = text.strip()
    start = stripped.find("{")
    end = stripped.rfind("}")
    if start < 0 or end < start:
        return None
    try:
        parsed = json.loads(stripped[start : end + 1])
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


def normalize_labels(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    labels = []
    for item in value:
        if isinstance(item, str) and item in CONTEXT_LABELS and item not in labels:
            labels.append(item)
    return [label for label in CONTEXT_LABELS if label in labels]


def build_prompt(text: str, baseline_labels: list[str]) -> str:
    descriptions = "\n".join(f"- {label}: {LABEL_DESCRIPTIONS[label]}" for label in CONTEXT_LABELS)
    return f"""너는 한국어 관광 챗봇의 문맥 라벨러다.
사용자 발화에 해당하는 라벨만 고른다. 근거가 애매하면 라벨을 붙이지 않는다.
반드시 JSON 객체 하나만 출력한다.

가능한 라벨:
{descriptions}

주의:
- 장소 유형인 박물관/공원/시장 자체는 specific_facility_required가 아니다.
- 유모차는 문맥에 따라 family_context 또는 mobility_context가 될 수 있다.
- "A 또는 B", "없으면 B라도"는 or_condition이다.
- "둘 다", "모두", "반드시", "없으면 안 돼"만 strict_and다.
- "주차 말고 주제가 독특한 곳"은 주차 시설 제외가 아니라 표현상 대비일 수 있다.
- "A도 있으면 좋지만 필수는 아니야"는 soft_and 쪽이다.
- "A 조건은 내려놓고 B", "A 얘기는 그만하고 B", "A 대신 B", "B 기준으로 다시"는 replace_condition이다.
- replace_condition 문장에는 exclude_condition/add_condition을 같이 붙이지 않는다.
- 새 기준 B가 휠체어/유모차여도 이동성 설명이 목적이 아니면 mobility_context를 붙이지 않는다.
- 새 기준 B가 오디오가이드/자막/화장실이어도 카드 근거를 반드시 요구하는 표현이 아니면 specific_facility_required를 붙이지 않는다.
- 라벨은 필요한 최소 개수만 선택한다.

예시:
- "시장 얘기는 그만하고 오디오가이드 있는 후보만" -> {{"labels":["replace_condition"]}}
- "점자블록이나 오디오가이드 중 하나면 돼" -> {{"labels":["or_condition","specific_facility_required"]}}
- "아이랑 오래 걷지 않는 곳" -> {{"labels":["family_context","mobility_context"]}}
- "유모차 기준으로 동선 짧은 곳" -> {{"labels":["mobility_context"]}}
- "기저귀 교환대 근거가 있는 곳만" -> {{"labels":["specific_facility_required"]}}

참고용 기존 예측: {baseline_labels}
사용자 발화: {text}

출력 형식:
{{"labels":["label1"],"reason":"짧은 한국어 이유"}}"""


def call_ollama(base_url: str, model: str, prompt: str, timeout: float, num_predict: int) -> tuple[dict[str, Any] | None, str | None, float]:
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "keep_alive": "10m",
        "options": {"temperature": 0.0, "num_predict": num_predict},
    }
    started = time.perf_counter()
    try:
        response = requests.post(f"{base_url.rstrip('/')}/api/generate", json=payload, timeout=timeout)
        elapsed_ms = (time.perf_counter() - started) * 1000
        response.raise_for_status()
        data = response.json()
    except requests.RequestException as exc:
        elapsed_ms = (time.perf_counter() - started) * 1000
        return None, str(exc), elapsed_ms
    return data, None, elapsed_ms


def percentile(values: list[float], ratio: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, round((len(ordered) - 1) * ratio)))
    return round(ordered[index], 1)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate SuperGemma4 context labeling on hybrid LogisticRegression mismatches.")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--train", type=Path, default=DEFAULT_TRAIN)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--base-url", default="http://localhost:11434")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--timeout", type=float, default=120.0)
    parser.add_argument("--num-predict", type=int, default=160)
    parser.add_argument("--max-cases", type=int, default=0, help="0 means all hybrid mismatches.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    rows = load_rows(args.input)
    train_rows = load_rows(args.train)
    bundle = train_linear_model(train_rows, "logistic_regression")

    baseline_predictions: dict[str, set[str]] = {}
    mismatches: list[dict[str, Any]] = []
    for row in rows:
        text = str(row.get("text") or "")
        expected = set(row.get("labels") or [])
        predicted = predict_hybrid_linear(text, bundle)
        row_id = str(row.get("id") or text)
        baseline_predictions[row_id] = predicted
        if predicted != expected:
            mismatch = dict(row)
            mismatch["baseline_labels"] = sorted(predicted, key=CONTEXT_LABELS.index)
            mismatches.append(mismatch)

    selected = mismatches[: args.max_cases] if args.max_cases > 0 else mismatches
    llm_predictions: dict[str, set[str]] = {}
    case_results: list[dict[str, Any]] = []
    latencies: list[float] = []

    for index, row in enumerate(selected, start=1):
        text = str(row.get("text") or "")
        row_id = str(row.get("id") or text)
        prompt = build_prompt(text, list(row.get("baseline_labels") or []))
        data, error, elapsed_ms = call_ollama(args.base_url, args.model, prompt, args.timeout, args.num_predict)
        latencies.append(elapsed_ms)
        response_text = str((data or {}).get("response") or "")
        parsed = extract_json_object(response_text)
        labels = normalize_labels((parsed or {}).get("labels"))
        llm_predictions[row_id] = set(labels)
        expected = set(row.get("labels") or [])
        baseline = set(row.get("baseline_labels") or [])
        case_results.append(
            {
                "index": index,
                "id": row.get("id"),
                "text": text,
                "expected": sorted(expected, key=CONTEXT_LABELS.index),
                "baseline_labels": sorted(baseline, key=CONTEXT_LABELS.index),
                "llm_labels": labels,
                "baseline_correct": baseline == expected,
                "llm_correct": set(labels) == expected,
                "json_parse_ok": parsed is not None,
                "reason": (parsed or {}).get("reason"),
                "error": error,
                "elapsed_ms": round(elapsed_ms, 1),
                "raw_response": response_text[:500],
            }
        )

    selected_ids = {str(row.get("id") or row.get("text") or "") for row in selected}

    def baseline_predict(text: str, row_id: str) -> set[str]:
        return baseline_predictions[row_id]

    def selective_predict(text: str, row_id: str) -> set[str]:
        if row_id in llm_predictions:
            return llm_predictions[row_id]
        return baseline_predictions[row_id]

    selected_prediction_by_text = {
        str(row.get("text") or ""): llm_predictions.get(str(row.get("id") or row.get("text") or ""), set())
        for row in selected
    }
    selected_metrics = evaluate_predictions(
        selected,
        "supergemma_on_hybrid_mismatches",
        lambda text: selected_prediction_by_text.get(text, set()),
    )

    selected_exact = 0
    selected_total = 0
    for row in selected:
        row_id = str(row.get("id") or row.get("text") or "")
        if set(row.get("labels") or []) == llm_predictions.get(row_id, set()):
            selected_exact += 1
        selected_total += 1

    full_baseline_correct = 0
    full_selective_correct = 0
    for row in rows:
        row_id = str(row.get("id") or row.get("text") or "")
        expected = set(row.get("labels") or [])
        baseline = baseline_predictions[row_id]
        selected_prediction = llm_predictions[row_id] if row_id in llm_predictions else baseline
        full_baseline_correct += int(baseline == expected)
        full_selective_correct += int(selected_prediction == expected)

    full_prediction_by_text: dict[str, set[str]] = {}
    for row in rows:
        row_id = str(row.get("id") or row.get("text") or "")
        full_prediction_by_text[str(row.get("text") or "")] = (
            llm_predictions[row_id] if row_id in llm_predictions else baseline_predictions[row_id]
        )

    selective_metrics = evaluate_predictions(
        rows,
        "hybrid_logistic_plus_supergemma_selected",
        lambda text: full_prediction_by_text.get(text, set()),
    )

    summary = {
        "model": args.model,
        "rows": len(rows),
        "hybrid_mismatch_rows": len(mismatches),
        "selected_rows": len(selected),
        "selected_exact_match": round(selected_exact / selected_total, 4) if selected_total else 0.0,
        "full_baseline_exact_match": round(full_baseline_correct / len(rows), 4) if rows else 0.0,
        "full_selective_exact_match": round(full_selective_correct / len(rows), 4) if rows else 0.0,
        "selected_metrics": selected_metrics,
        "selective_metrics": selective_metrics,
        "latency": {
            "count": len(latencies),
            "mean_ms": round(sum(latencies) / len(latencies), 1) if latencies else None,
            "p50_ms": percentile(latencies, 0.50),
            "p95_ms": percentile(latencies, 0.95),
            "max_ms": round(max(latencies), 1) if latencies else None,
        },
        "cases": case_results,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps({key: value for key, value in summary.items() if key != "cases"}, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
