from __future__ import annotations

import argparse
from collections import Counter
import json
import os
from pathlib import Path
import re
import sys
from time import sleep
from typing import Any

import requests
from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.services.tourism_intent_classifier import TourismIntentClassifier  # noqa: E402


DEFAULT_OUTPUT = PROJECT_ROOT / "data" / "eval" / "tourism_intent_gemini_holdout.jsonl"
DEFAULT_REPORT = PROJECT_ROOT / "data" / "generated" / "tour_api" / "gemini_holdout_report.json"
DEFAULT_MODEL = "gemini-2.5-flash"
GENERATE_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
INTENTS = [
    "recommend_places",
    "show_more",
    "live_topup",
    "ask_source",
    "add_condition",
    "replace_condition",
    "exclude_preference",
    "change_region",
    "narrow_region",
    "clarify_region",
    "unsupported_request",
]
REFERENCE_PATHS = [
    PROJECT_ROOT / "data" / "eval" / "tourism_100_questions.jsonl",
    PROJECT_ROOT / "data" / "eval" / "tourism_challenge_questions.jsonl",
    PROJECT_ROOT / "data" / "eval" / "tourism_conversation_challenge.jsonl",
    PROJECT_ROOT / "data" / "eval" / "tourism_expanded_questions.jsonl",
    PROJECT_ROOT / "data" / "eval" / "tourism_expanded_conversation_challenge.jsonl",
    PROJECT_ROOT / "data" / "eval" / "tourism_intent_seed_utterances.jsonl",
    PROJECT_ROOT / "data" / "eval" / "tourism_intent_generated_utterances.jsonl",
    PROJECT_ROOT / "data" / "eval" / "tourism_intent_aihub_utterances.jsonl",
    PROJECT_ROOT / "data" / "eval" / "tourism_intent_adversarial_holdout.jsonl",
    PROJECT_ROOT / "data" / "processed" / "tourism_intent_training.jsonl",
]


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower())


def load_reference_texts(paths: list[Path]) -> set[str]:
    texts = set()
    for path in paths:
        if not path.exists():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            payload = json.loads(line)
            turns = payload.get("turns")
            if isinstance(turns, list):
                for turn in turns:
                    message = str(turn.get("message") or turn.get("text") or "").strip()
                    if message:
                        texts.add(normalize_text(message))
                continue
            message = str(payload.get("message") or payload.get("text") or "").strip()
            if message:
                texts.add(normalize_text(message))
    return texts


def build_prompt(intent: str, count: int, batch_index: int) -> str:
    definitions = {
        "recommend_places": "새 관광지 추천 요청. 지역과 접근성/가족 조건이 포함될 수 있다.",
        "show_more": "이미 받은 추천에서 더 보기, 나머지 보기, 전체 보기 같은 후속 요청.",
        "live_topup": "현재/최신/새로 확인/더 찾아보기 같은 최신성 보강 요청. API라는 내부 용어는 쓰지 않는다.",
        "ask_source": "추천 카드나 답변의 근거, 출처, 원자료를 묻는 요청.",
        "add_condition": "이전 추천에 장애인 화장실, 주차, 수유실, 점자블록 등 조건을 추가하는 요청.",
        "replace_condition": "이전 조건을 다른 조건으로 바꾸는 요청. 예: 유모차 말고 휠체어.",
        "exclude_preference": "시장, 숙소, 카페, 식당 등 특정 유형을 빼 달라는 요청.",
        "change_region": "이전 지역이 아니라 새 광역/시군구 지역으로 바꾸는 요청.",
        "narrow_region": "상위 지역 안에서 중구/동구/해운대구 등 하위 지역으로 좁히는 요청.",
        "clarify_region": "중구, 남구, 고성군처럼 전국에 여러 곳이 있어 지역 선택이 필요한 모호 지역 요청.",
        "unsupported_request": "실시간 혼잡도, 영업 여부, 예약, 입장료, 교통요금, 병원/약국 등 현재 관광 카드 근거 밖 요청.",
    }
    return f"""
너는 한국어 관광 챗봇의 독립 holdout 평가셋을 만드는 문제 출제자다.
학습셋 문장을 베끼지 말고, 실제 사용자가 채팅창에 쓸 법한 짧고 다양한 한국어 발화를 만들어라.

목표 intent: {intent}
정의: {definitions[intent]}
생성 수: {count}
배치 번호: {batch_index}

필수 조건:
- JSON 배열만 출력한다. Markdown, 설명, 코드블록은 금지한다.
- 각 원소는 {{"text": "...", "intent": "{intent}"}} 형태다.
- intent 값은 반드시 "{intent}"만 사용한다.
- 기존 템플릿처럼 보이는 반복 문장을 피하고 문체를 다양화한다.
- 내부 구현 용어인 API, fallback, cache, Chroma, vector, RAG는 쓰지 않는다.
- 관광/무장애/가족 이동 맥락에서 자연스러운 표현만 만든다.
- 일부는 오타, 축약, 반말, 존댓말, 짧은 후속 질문을 섞어도 된다.
- 개인정보, 전화번호, 실제 민감정보는 만들지 않는다.
""".strip()


def extract_json_array(text: str) -> list[Any]:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?", "", cleaned).strip()
        cleaned = re.sub(r"```$", "", cleaned).strip()
    start = cleaned.find("[")
    end = cleaned.rfind("]")
    if start == -1 or end == -1 or end < start:
        raise ValueError("Gemini response did not include a JSON array")
    return json.loads(cleaned[start : end + 1])


def call_gemini(api_key: str, model: str, prompt: str, temperature: float, timeout: int) -> list[dict[str, str]]:
    response = requests.post(
        GENERATE_URL.format(model=model),
        headers={"x-goog-api-key": api_key, "Content-Type": "application/json"},
        json={
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": temperature,
                "responseMimeType": "application/json",
            },
        },
        timeout=timeout,
    )
    response.raise_for_status()
    payload = response.json()
    parts = payload.get("candidates", [{}])[0].get("content", {}).get("parts", [])
    text = "\n".join(str(part.get("text") or "") for part in parts)
    rows = extract_json_array(text)
    if not isinstance(rows, list):
        raise ValueError("Gemini response JSON must be an array")
    return rows


def validate_rows(raw_rows: list[dict[str, str]], reference_texts: set[str]) -> tuple[list[dict[str, str]], Counter[str]]:
    accepted = []
    rejected: Counter[str] = Counter()
    seen = set()
    for row in raw_rows:
        if not isinstance(row, dict):
            rejected["not_object"] += 1
            continue
        text = str(row.get("text") or "").strip()
        intent = str(row.get("intent") or "").strip()
        normalized = normalize_text(text)
        if intent not in INTENTS:
            rejected["unknown_intent"] += 1
            continue
        if len(text) < 4 or len(text) > 120:
            rejected["bad_length"] += 1
            continue
        if normalized in seen:
            rejected["duplicate_in_batch"] += 1
            continue
        if normalized in reference_texts:
            rejected["overlaps_reference"] += 1
            continue
        if any(term.lower() in normalized for term in ["api", "fallback", "cache", "chroma", "vector", "rag"]):
            rejected["internal_term"] += 1
            continue
        seen.add(normalized)
        accepted.append({"text": text, "intent": intent, "source": "gemini_independent_holdout"})
    return accepted, rejected


def classifier_report(rows: list[dict[str, str]]) -> dict[str, Any]:
    classifier = TourismIntentClassifier()
    by_intent: dict[str, dict[str, int]] = {intent: {"rows": 0, "correct": 0} for intent in INTENTS}
    misses = []
    for row in rows:
        prediction = classifier.predict(row["text"])
        actual = row["intent"]
        predicted = prediction.intent or "<none>"
        by_intent[actual]["rows"] += 1
        by_intent[actual]["correct"] += int(actual == predicted)
        if actual != predicted and len(misses) < 100:
            misses.append(
                {
                    "text": row["text"],
                    "actual": actual,
                    "predicted": predicted,
                    "confidence": prediction.confidence,
                }
            )
    total = sum(stats["rows"] for stats in by_intent.values())
    correct = sum(stats["correct"] for stats in by_intent.values())
    return {
        "rows": total,
        "accuracy": round(correct / total, 4) if total else 0.0,
        "by_intent": {
            intent: {
                "rows": stats["rows"],
                "accuracy": round(stats["correct"] / stats["rows"], 4) if stats["rows"] else 0.0,
            }
            for intent, stats in by_intent.items()
            if stats["rows"]
        },
        "sample_misses": misses,
    }


def write_jsonl(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        for row in rows:
            file.write(json.dumps(row, ensure_ascii=False) + "\n")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate an independent tourism intent holdout with Gemini.")
    parser.add_argument("--target", type=int, default=770, help="Accepted row target. 770 gives 70 rows per 11 intents.")
    parser.add_argument("--per-batch", type=int, default=35)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--temperature", type=float, default=0.95)
    parser.add_argument("--max-batches-per-intent", type=int, default=5)
    parser.add_argument("--timeout", type=int, default=60)
    parser.add_argument("--sleep", type=float, default=0.4)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    return parser.parse_args()


def main() -> None:
    load_dotenv(PROJECT_ROOT / ".env")
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise SystemExit("GEMINI_API_KEY or GOOGLE_API_KEY is required. Add it to .env or export it before running.")

    args = parse_args()
    output = args.output if args.output.is_absolute() else PROJECT_ROOT / args.output
    report_path = args.report if args.report.is_absolute() else PROJECT_ROOT / args.report
    reference_texts = load_reference_texts(REFERENCE_PATHS)
    rows_per_intent = max(1, args.target // len(INTENTS))
    all_rows = []
    rejected_total: Counter[str] = Counter()

    for intent in INTENTS:
        accepted_for_intent = []
        for batch_index in range(1, args.max_batches_per_intent + 1):
            prompt = build_prompt(intent, args.per_batch, batch_index)
            generated = call_gemini(api_key, args.model, prompt, args.temperature, args.timeout)
            accepted, rejected = validate_rows(generated, reference_texts)
            rejected_total.update(rejected)
            for row in accepted:
                if row["intent"] == intent and len(accepted_for_intent) < rows_per_intent:
                    accepted_for_intent.append(row)
            print(f"{intent} batch {batch_index}: accepted {len(accepted_for_intent)}/{rows_per_intent}")
            if len(accepted_for_intent) >= rows_per_intent:
                break
            sleep(args.sleep)
        all_rows.extend(accepted_for_intent)

    all_rows.sort(key=lambda row: (row["intent"], row["text"]))
    write_jsonl(output, all_rows)
    report = {
        "model": args.model,
        "target": args.target,
        "rows": len(all_rows),
        "counts": dict(Counter(row["intent"] for row in all_rows)),
        "rejected": dict(rejected_total),
        "classifier_baseline": classifier_report(all_rows),
        "notes": [
            "This is an AI-generated independent holdout, not a human-written holdout.",
            "Rows are not part of the default training set.",
            "Classifier baseline is diagnostic only and is not used to filter correctness.",
        ],
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    print(f"Wrote rows to {output.relative_to(PROJECT_ROOT)}")
    print(f"Wrote report to {report_path.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
