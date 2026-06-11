from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib import error, request


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

DEFAULT_INPUT = PROJECT_ROOT / "data" / "eval" / "tourism_20_questions.jsonl"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "data" / "generated" / "tour_api" / "eval_runs"
TOUR_API_OPERATIONS = ["areaBasedList2", "detailCommon2", "detailWithTour2"]
TERM_EQUIVALENTS = {
    "유모차": ["유모차", "유아용 의자", "휠체어", "무장애", "턱이 없어", "경사로", "출입통로", "접근로"],
    "고령자": ["고령자", "어르신", "노약자", "쉬어", "휴식", "의자", "휠체어", "장애인", "경사로", "접근로", "출입통로", "화장실", "대중교통", "무단차", "평탄"],
    "영유아": ["영유아", "유아용 의자"],
    "가족": ["가족", "유아용 의자"],
    "기저귀": ["기저귀", "유아용 의자"],
    "먹거리": ["먹거리", "음식", "식당", "음식점", "유아용 의자", "의자식 테이블"],
    "식당": ["식당", "음식점", "유아용 의자", "의자식 테이블"],
    "음식": ["음식", "음식점", "식당", "유아용 의자", "의자식 테이블"],
}


def load_eval_items(path: Path) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        item = json.loads(line)
        if "id" not in item:
            raise ValueError(f"{path}:{line_number} must include id")
        if "message" not in item and "turns" not in item:
            raise ValueError(f"{path}:{line_number} must include message or turns")
        if "turns" in item and not isinstance(item["turns"], list):
            raise ValueError(f"{path}:{line_number} turns must be a list")
        items.append(item)
    return items


def post_tourism_chat(base_url: str, message: str, session_id: str, timeout: float) -> tuple[int, dict[str, Any]]:
    payload = json.dumps({"message": message, "session_id": session_id}).encode("utf-8")
    req = request.Request(
        f"{base_url.rstrip('/')}/tourism/chat",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with request.urlopen(req, timeout=timeout) as response:
            body = response.read().decode("utf-8")
            return response.status, json.loads(body)
    except error.HTTPError as exc:
        body = exc.read().decode("utf-8")
        try:
            parsed: dict[str, Any] = json.loads(body)
        except json.JSONDecodeError:
            parsed = {"error": body}
        return exc.code, parsed


def post_tourism_chat_direct(message: str, session_id: str) -> tuple[int, dict[str, Any]]:
    from fastapi.testclient import TestClient

    from app.main import app

    payload = {"message": message, "session_id": session_id}
    with TestClient(app) as client:
        response = client.post("/tourism/chat", json=payload)
    return response.status_code, response.json()


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        for row in rows:
            file.write(json.dumps(row, ensure_ascii=False) + "\n")


def card_search_text(card: dict[str, Any]) -> str:
    parts = [
        str(card.get("title") or ""),
        str(card.get("address") or ""),
        str(card.get("recommendation_reason") or ""),
        " ".join(str(value) for value in card.get("accessibility_tags", []) if value),
        " ".join(str(value) for value in card.get("family_tags", []) if value),
    ]
    raw_fields = card.get("raw_fields")
    if isinstance(raw_fields, dict):
        parts.extend(f"{key} {value}" for key, value in raw_fields.items())
    return " ".join(parts)


def any_card_contains(cards: list[Any], terms: list[str]) -> bool:
    for card in cards:
        if not isinstance(card, dict):
            continue
        haystack = card_search_text(card)
        if any(term in haystack for term in terms):
            return True
    return False


def normalize_term_groups(raw_groups: Any) -> list[list[str]]:
    if not raw_groups:
        return []
    if isinstance(raw_groups, str):
        return [[raw_groups]]
    if isinstance(raw_groups, list):
        if all(not isinstance(group, list) for group in raw_groups):
            return [expand_equivalent_terms([str(group) for group in raw_groups])]
        return [
            expand_equivalent_terms([str(term) for term in group]) if isinstance(group, list) else expand_equivalent_terms([str(group)])
            for group in raw_groups
        ]
    return [expand_equivalent_terms([str(raw_groups)])]


def expand_equivalent_terms(terms: list[str]) -> list[str]:
    expanded: list[str] = []
    for term in terms:
        expanded.extend(TERM_EQUIVALENTS.get(term, [term]))
    return list(dict.fromkeys(expanded))


def classify_eval_failure_details(item: dict[str, Any], response_body: dict[str, Any]) -> dict[str, Any]:
    cards = response_body.get("cards", [])
    if not isinstance(cards, list):
        cards = []

    min_cards = item.get("min_cards")
    expected_min_cards = min_cards if isinstance(min_cards, int) else None
    required_groups = normalize_term_groups(item.get("must_include_any_card_terms"))
    missing_required_groups = [group for group in required_groups if not any_card_contains(cards, group)]

    classes: list[str] = []
    if expected_min_cards is not None:
        if not cards and expected_min_cards > 0:
            classes.append("no_card_output")
        elif len(cards) < expected_min_cards:
            classes.append("low_card_count")
    if missing_required_groups:
        if cards:
            classes.append("strict_evidence_mismatch")
        else:
            classes.append("strict_evidence_unverifiable_no_card")

    if not classes:
        classes.append("criteria_satisfied_or_non_card_failure")

    return {
        "classes": classes,
        "card_output_state": "no_cards" if not cards else "has_cards",
        "card_count": len(cards),
        "expected_min_cards": expected_min_cards,
        "required_group_count": len(required_groups),
        "missing_required_groups": missing_required_groups,
    }


def classify_eval_failures(item: dict[str, Any], status_code: int, response_body: dict[str, Any], error_message: str | None) -> list[str]:
    failures: list[str] = []
    if error_message:
        failures.append("request_error")
    if status_code >= 400:
        failures.append("http_error")

    cards = response_body.get("cards", [])
    if not isinstance(cards, list):
        cards = []
    answer = str(response_body.get("answer") or "")
    suggestions = response_body.get("suggested_messages", [])
    if not isinstance(suggestions, list):
        suggestions = []

    expected_lookup_mode = item.get("expected_lookup_mode")
    if expected_lookup_mode and response_body.get("lookup_mode") != expected_lookup_mode:
        failures.append("lookup_mode_mismatch")

    min_cards = item.get("min_cards")
    if isinstance(min_cards, int) and len(cards) < min_cards:
        failures.append("card_count_low")
    max_cards = item.get("max_cards")
    if isinstance(max_cards, int) and len(cards) > max_cards:
        failures.append("card_count_high")

    for title in item.get("must_include_titles", []) or []:
        if not any(title in str(card.get("title", "")) for card in cards if isinstance(card, dict)):
            failures.append("missing_expected_card")
            break

    for normalized_terms in normalize_term_groups(item.get("must_include_any_card_terms")):
        if not any_card_contains(cards, normalized_terms):
            failures.append("card_missing_required_terms")
            break

    first_card_terms = item.get("first_card_must_include_any_terms")
    if first_card_terms and cards:
        normalized_terms = [str(first_card_terms)] if isinstance(first_card_terms, str) else [str(term) for term in first_card_terms]
        first_card = cards[0] if isinstance(cards[0], dict) else {}
        if not any(term in card_search_text(first_card) for term in normalized_terms):
            failures.append("first_card_missing_required_terms")
    elif first_card_terms:
        failures.append("first_card_missing_required_terms")

    for normalized_terms in normalize_term_groups(item.get("must_not_include_card_terms")):
        if any_card_contains(cards, normalized_terms):
            failures.append("card_contains_forbidden_terms")
            break

    for region in item.get("must_not_include_regions", []) or []:
        if any(region in str(card.get("address", "")) for card in cards if isinstance(card, dict)):
            failures.append("wrong_region_card")
            break

    for term in item.get("must_contain_answer_terms", []) or []:
        if term not in answer:
            failures.append("answer_missing_term")
            break

    for term in item.get("must_not_contain_answer_terms", []) or []:
        if str(term) in answer:
            failures.append("answer_contains_forbidden_term")
            break

    answer_any_terms = item.get("must_include_answer_any_terms")
    if answer_any_terms:
        normalized_terms = [str(answer_any_terms)] if isinstance(answer_any_terms, str) else [str(term) for term in answer_any_terms]
        if not any(term in answer for term in normalized_terms):
            failures.append("answer_missing_any_term")

    expected_suggestions = item.get("expected_suggestions")
    if isinstance(expected_suggestions, list):
        for expected in expected_suggestions:
            if not any(str(expected) in str(suggestion) for suggestion in suggestions):
                failures.append("missing_suggestion")
                break
    for term in item.get("must_not_include_suggestion_terms", []) or []:
        if any(str(term) in str(suggestion) for suggestion in suggestions):
            failures.append("suggestion_contains_forbidden_term")
            break
    min_suggestions = item.get("min_suggestions")
    if isinstance(min_suggestions, int) and len(suggestions) < min_suggestions:
        failures.append("suggestion_count_low")

    if item.get("expect_clarification") and response_body.get("lookup_mode") != "clarification":
        failures.append("clarification_missing")
    if item.get("expect_no_cards") and cards:
        failures.append("unexpected_cards")
    return list(dict.fromkeys(failures))


def load_usage_snapshot() -> dict[str, Any]:
    from app.core.config import Settings
    from app.services.tour_api_usage import TourAPIUsageTracker

    settings = Settings()
    tracker = TourAPIUsageTracker(
        settings.resolved_tour_api_usage_log_path,
        daily_endpoint_limit=settings.tour_api_daily_endpoint_limit,
    )
    snapshot = tracker.snapshot()
    return {"date": snapshot.date, "limit": snapshot.limit, "counts": snapshot.counts}


def estimate_max_tour_api_calls(item_count: int) -> dict[str, int]:
    from app.core.config import Settings

    settings = Settings()
    if not settings.tourism_live_lookup_enabled or not settings.tour_api_service_key:
        return {operation: 0 for operation in TOUR_API_OPERATIONS}
    detail_calls = max(settings.tourism_live_max_detail_calls, 0)
    return {
        "areaBasedList2": item_count,
        "detailCommon2": item_count * detail_calls,
        "detailWithTour2": item_count * detail_calls,
    }


def assert_tour_api_budget_for_eval(item_count: int, strict: bool = False) -> dict[str, Any]:
    from app.core.config import Settings
    from app.services.tour_api_usage import TourAPIUsageTracker

    settings = Settings()
    tracker = TourAPIUsageTracker(
        settings.resolved_tour_api_usage_log_path,
        daily_endpoint_limit=settings.tour_api_daily_endpoint_limit,
    )
    snapshot = tracker.snapshot()
    estimated = estimate_max_tour_api_calls(item_count)
    for operation in TOUR_API_OPERATIONS:
        tracker.assert_available(operation, amount=0)
    return {"date": snapshot.date, "limit": snapshot.limit, "counts": snapshot.counts, "estimated_max": estimated}


def run_eval(
    input_path: Path,
    base_url: str,
    output_path: Path,
    timeout: float,
    direct: bool = False,
    strict_budget: bool = False,
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    items = load_eval_items(input_path)
    budget = assert_tour_api_budget_for_eval(len(items), strict=strict_budget)
    print(f"TourAPI usage {budget['date']} limit={budget['limit']} counts={budget['counts']} estimated_max={budget['estimated_max']}")
    for item in items:
        started = time.perf_counter()
        status_code = 0
        response_body: dict[str, Any]
        error_message: str | None = None
        turn_results: list[dict[str, Any]] = []
        try:
            session_id = f"eval-{item['id']}"
            if "turns" in item:
                response_body = {}
                for turn_index, turn in enumerate(item["turns"], start=1):
                    if direct:
                        status_code, response_body = post_tourism_chat_direct(
                            message=turn["message"],
                            session_id=session_id,
                        )
                    else:
                        status_code, response_body = post_tourism_chat(
                            base_url=base_url,
                            message=turn["message"],
                            session_id=session_id,
                            timeout=timeout,
                        )
                    turn_failures = classify_eval_failures(turn, status_code, response_body, None)
                    turn_failure_diagnostics = classify_eval_failure_details(turn, response_body)
                    turn_results.append(
                        {
                            "turn": turn_index,
                            "message": turn["message"],
                            "status_code": status_code,
                            "lookup_mode": response_body.get("lookup_mode"),
                            "card_count": len(response_body.get("cards", [])),
                            "suggested_message_count": len(response_body.get("suggested_messages", [])),
                            "answer": response_body.get("answer"),
                            "response": response_body,
                            "failure_reasons": turn_failures,
                            "failure_classes": turn_failure_diagnostics["classes"],
                            "failure_diagnostics": turn_failure_diagnostics,
                            "passed": not turn_failures,
                        }
                    )
            elif direct:
                status_code, response_body = post_tourism_chat_direct(
                    message=item["message"],
                    session_id=session_id,
                )
            else:
                status_code, response_body = post_tourism_chat(
                    base_url=base_url,
                    message=item["message"],
                    session_id=session_id,
                    timeout=timeout,
                )
        except Exception as exc:  # noqa: BLE001 - eval runner must keep going.
            response_body = {}
            error_message = str(exc)
        duration_ms = round((time.perf_counter() - started) * 1000, 1)
        if turn_results:
            failure_reasons = []
            for turn in turn_results:
                failure_reasons.extend(f"turn{turn['turn']}:{reason}" for reason in turn["failure_reasons"])
            if error_message:
                failure_reasons.append("request_error")
            if status_code >= 400:
                failure_reasons.append("http_error")
            failure_diagnostics = {
                "classes": list(
                    dict.fromkeys(
                        class_name
                        for turn in turn_results
                        for class_name in turn.get("failure_classes", [])
                        if class_name != "criteria_satisfied_or_non_card_failure"
                    )
                )
                or ["criteria_satisfied_or_non_card_failure"],
                "turns": [turn.get("failure_diagnostics", {}) for turn in turn_results],
            }
        else:
            failure_reasons = classify_eval_failures(item, status_code, response_body, error_message)
            failure_diagnostics = classify_eval_failure_details(item, response_body)
        results.append(
            {
                "id": item["id"],
                "category": item.get("category"),
                "message": item.get("message") or " / ".join(str(turn.get("message")) for turn in item.get("turns", [])),
                "expected_region": item.get("expected_region"),
                "expected_conditions": item.get("expected_conditions", []),
                "expected_behavior": item.get("expected_behavior"),
                "scoring_focus": item.get("scoring_focus", []),
                "status_code": status_code,
                "duration_ms": duration_ms,
                "lookup_mode": response_body.get("lookup_mode"),
                "degraded": response_body.get("degraded"),
                "warnings": response_body.get("warnings", []),
                "card_count": len(response_body.get("cards", [])),
                "suggested_message_count": len(response_body.get("suggested_messages", [])),
                "answer": response_body.get("answer"),
                "response": response_body,
                "turn_results": turn_results,
                "error": error_message,
                "failure_reasons": failure_reasons,
                "failure_classes": failure_diagnostics["classes"],
                "failure_diagnostics": failure_diagnostics,
                "passed": not failure_reasons,
            }
        )
        failed = ",".join(failure_reasons) if failure_reasons else "ok"
        print(f"{item['id']} {status_code} {duration_ms}ms cards={results[-1]['card_count']} mode={results[-1]['lookup_mode']} {failed}")
    write_jsonl(output_path, results)
    return results


def default_output_path() -> Path:
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    return DEFAULT_OUTPUT_DIR / f"tourism_eval_{timestamp}.jsonl"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a tourism eval JSONL set against /tourism/chat.")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--base-url", default=os.environ.get("TOURISM_EVAL_BASE_URL", "http://127.0.0.1:8000"))
    parser.add_argument("--output", type=Path, default=default_output_path())
    parser.add_argument("--timeout", type=float, default=90.0)
    parser.add_argument(
        "--direct",
        action="store_true",
        help="Call the FastAPI app in-process with TestClient instead of requiring a running server.",
    )
    parser.add_argument(
        "--strict-budget",
        action="store_true",
        help="Check today's TourAPI usage before running. Actual calls are still guarded per endpoint before each request.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    try:
        results = run_eval(
            input_path=args.input,
            base_url=args.base_url,
            output_path=args.output,
            timeout=args.timeout,
            direct=args.direct,
            strict_budget=args.strict_budget,
        )
    except Exception as exc:
        if exc.__class__.__name__ == "TourAPIQuotaExceeded":
            print(f"TourAPI budget check failed: {exc}")
            raise SystemExit(2) from exc
        raise
    failures = [row for row in results if row["failure_reasons"]]
    print(f"\nWrote {len(results)} rows to {args.output}")
    print(f"Failures: {len(failures)}")
    if failures:
        summary: dict[str, int] = {}
        for row in failures:
            for reason in row["failure_reasons"]:
                summary[reason] = summary.get(reason, 0) + 1
        print(f"Failure summary: {summary}")


if __name__ == "__main__":
    main()
