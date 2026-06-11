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


DEFAULT_INPUT = PROJECT_ROOT / "data" / "eval" / "tourism_intent_gemini_holdout.jsonl"
DEFAULT_OUTPUT = PROJECT_ROOT / "data" / "eval" / "tourism_intent_gemini_holdout_verified.jsonl"
DEFAULT_REPORT = PROJECT_ROOT / "data" / "generated" / "tour_api" / "gemini_holdout_verified_report.json"
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


def load_jsonl(path: Path) -> list[dict[str, str]]:
    rows = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        payload = json.loads(line)
        text = str(payload.get("text") or "").strip()
        intent = str(payload.get("intent") or "").strip()
        if not text or intent not in INTENTS:
            raise ValueError(f"{path}:{line_number} must include text and known intent")
        rows.append({"id": f"row-{line_number:04d}", "text": text, "intent": intent})
    return rows


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


def build_prompt(rows: list[dict[str, str]]) -> str:
    payload = [{"id": row["id"], "text": row["text"], "intent": row["intent"]} for row in rows]
    return f"""
너는 한국어 관광 챗봇 intent holdout의 라벨 검수자다.
아래 발화가 제시된 intent 라벨과 맞는지 판단하라.

라벨 정의:
- recommend_places: 새 관광지 추천 요청.
- show_more: 이미 받은 추천에서 더 보기, 나머지, 전체, 계속 보기 요청.
- live_topup: 현재/최신/최근/새로 확인/더 찾아보기 같은 최신성 보강 요청.
- ask_source: 근거, 출처, 원자료, 기준 자료를 묻는 요청.
- add_condition: 이전 추천에 접근성/가족/장소 조건을 추가하는 요청.
- replace_condition: 이전 조건을 새 조건으로 바꾸는 요청. 예: 유모차 말고 휠체어.
- exclude_preference: 특정 유형을 빼 달라는 요청.
- change_region: 이전 지역에서 다른 광역/시군구로 바꾸는 요청.
- narrow_region: 기존 상위 지역 안에서 구/군/시 등 하위 지역으로 좁히는 요청.
- clarify_region: 중구/남구/고성군처럼 어느 지역인지 선택이 필요한 모호 지역 요청.
- unsupported_request: 현재 관광 카드 근거 밖의 실시간/가격/예약/의료/교통 계산 요청.

검수 기준:
- JSON 배열만 출력한다.
- 각 원소는 {{"id":"...", "valid":true/false, "corrected_intent":"...", "confidence":0.0~1.0, "reason":"..."}} 형태다.
- corrected_intent는 위 라벨 중 하나여야 한다.
- valid=true는 원래 intent가 corrected_intent와 같고 confidence가 충분할 때만 둔다.
- 짧은 후속 질문은 이전 추천 대화가 있었다고 가정해도 된다.
- 그래도 여러 라벨이 비슷하게 맞으면 valid=false로 둔다.

검수 대상:
{json.dumps(payload, ensure_ascii=False)}
""".strip()


def call_gemini(
    api_key: str,
    model: str,
    rows: list[dict[str, str]],
    timeout: int,
    *,
    max_retries: int,
) -> list[dict[str, Any]]:
    last_error: Exception | None = None
    for attempt in range(1, max_retries + 1):
        try:
            response = requests.post(
                GENERATE_URL.format(model=model),
                headers={"x-goog-api-key": api_key, "Content-Type": "application/json"},
                json={
                    "contents": [{"role": "user", "parts": [{"text": build_prompt(rows)}]}],
                    "generationConfig": {
                        "temperature": 0.1,
                        "responseMimeType": "application/json",
                    },
                },
                timeout=timeout,
            )
            response.raise_for_status()
            payload = response.json()
            parts = payload.get("candidates", [{}])[0].get("content", {}).get("parts", [])
            text = "\n".join(str(part.get("text") or "") for part in parts)
            judgements = extract_json_array(text)
            if not isinstance(judgements, list):
                raise ValueError("Gemini response JSON must be an array")
            return judgements
        except (requests.RequestException, ValueError, json.JSONDecodeError) as error:
            last_error = error
            if attempt >= max_retries:
                break
            sleep(min(2.0 * attempt, 8.0))
    raise RuntimeError(f"Gemini verification failed after {max_retries} attempts") from last_error


def classifier_report(rows: list[dict[str, str]]) -> dict[str, Any]:
    classifier = TourismIntentClassifier()
    stats: dict[str, dict[str, int]] = {intent: {"rows": 0, "correct": 0} for intent in INTENTS}
    misses = []
    for row in rows:
        prediction = classifier.predict(row["text"])
        actual = row["intent"]
        predicted = prediction.intent or "<none>"
        stats[actual]["rows"] += 1
        stats[actual]["correct"] += int(actual == predicted)
        if actual != predicted and len(misses) < 80:
            misses.append(
                {
                    "text": row["text"],
                    "actual": actual,
                    "predicted": predicted,
                    "confidence": prediction.confidence,
                }
            )
    total = sum(item["rows"] for item in stats.values())
    correct = sum(item["correct"] for item in stats.values())
    return {
        "rows": total,
        "accuracy": round(correct / total, 4) if total else 0.0,
        "by_intent": {
            intent: {
                "rows": item["rows"],
                "accuracy": round(item["correct"] / item["rows"], 4) if item["rows"] else 0.0,
            }
            for intent, item in stats.items()
            if item["rows"]
        },
        "sample_misses": misses,
    }


def write_jsonl(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        for row in rows:
            file.write(json.dumps(row, ensure_ascii=False) + "\n")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Verify Gemini-generated tourism intent holdout labels with Gemini.")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--batch-size", type=int, default=35)
    parser.add_argument("--min-confidence", type=float, default=0.72)
    parser.add_argument("--timeout", type=int, default=60)
    parser.add_argument("--max-retries", type=int, default=3)
    parser.add_argument("--sleep", type=float, default=0.3)
    return parser.parse_args()


def main() -> None:
    load_dotenv(PROJECT_ROOT / ".env")
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise SystemExit("GEMINI_API_KEY or GOOGLE_API_KEY is required. Add it to .env or export it before running.")

    args = parse_args()
    input_path = args.input if args.input.is_absolute() else PROJECT_ROOT / args.input
    output_path = args.output if args.output.is_absolute() else PROJECT_ROOT / args.output
    report_path = args.report if args.report.is_absolute() else PROJECT_ROOT / args.report
    rows = load_jsonl(input_path)
    verified = []
    rejected = []
    judgement_by_id: dict[str, dict[str, Any]] = {}

    for start in range(0, len(rows), args.batch_size):
        batch = rows[start : start + args.batch_size]
        judgements = call_gemini(
            api_key,
            args.model,
            batch,
            args.timeout,
            max_retries=args.max_retries,
        )
        for judgement in judgements:
            if isinstance(judgement, dict) and judgement.get("id"):
                judgement_by_id[str(judgement["id"])] = judgement
        print(f"verified batch {start // args.batch_size + 1}: {min(start + len(batch), len(rows))}/{len(rows)}")
        sleep(args.sleep)

    for row in rows:
        judgement = judgement_by_id.get(row["id"]) or {}
        corrected = str(judgement.get("corrected_intent") or "").strip()
        confidence = float(judgement.get("confidence") or 0.0)
        is_valid = bool(judgement.get("valid")) and corrected == row["intent"] and confidence >= args.min_confidence
        output_row = {"text": row["text"], "intent": row["intent"], "source": "gemini_independent_holdout_verified"}
        if is_valid:
            verified.append(output_row)
        else:
            rejected.append({**output_row, "corrected_intent": corrected, "confidence": confidence, "reason": str(judgement.get("reason") or "")})

    verified.sort(key=lambda row: (row["intent"], row["text"]))
    write_jsonl(output_path, verified)
    report = {
        "model": args.model,
        "input_rows": len(rows),
        "verified_rows": len(verified),
        "rejected_rows": len(rejected),
        "verified_counts": dict(Counter(row["intent"] for row in verified)),
        "rejected_counts": dict(Counter(row["intent"] for row in rejected)),
        "min_confidence": args.min_confidence,
        "classifier_baseline": classifier_report(verified),
        "sample_rejections": rejected[:80],
        "notes": [
            "This is an AI-generated and AI-verified independent holdout, not a human-written holdout.",
            "Rows are not part of the default training set.",
            "Current classifier baseline is diagnostic only and is not used to filter rows.",
        ],
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    print(f"Wrote rows to {output_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote report to {report_path.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
