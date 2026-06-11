from __future__ import annotations

import argparse
import json
from pathlib import Path
from statistics import mean, median
import sys
from time import perf_counter
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.api.deps import get_retriever  # noqa: E402
from app.core.config import Settings  # noqa: E402
from app.services.embedding_service import EmbeddingService  # noqa: E402
from app.services.korean_external_corrector import ExternalKoreanCorrector  # noqa: E402
from app.services.retriever import Retriever  # noqa: E402
from app.services.tour_api_service import TourAPIService  # noqa: E402
from app.services.tourism_condition_transformer import TourismConditionTransformer  # noqa: E402
from app.services.tourism_chat_service import TourismChatService  # noqa: E402
from app.services.tourism_intent_classifier import TourismIntentClassifier  # noqa: E402
from app.services.tourism_query_service import CONDITION_KEYWORDS  # noqa: E402
from app.services.tourism_query_service import TourismQueryService  # noqa: E402
from app.services.vector_store import VectorStore  # noqa: E402


DEFAULT_OUTPUT = PROJECT_ROOT / "data" / "generated" / "tour_api" / "latency_benchmark_latest.json"
DEFAULT_MESSAGES = [
    "서울에서 휠체어 관광지 추천해줘",
    "부산 중구에서 휠체어 관광지 추천해줘",
    "제주시에서 유모차로 갈만한 곳 추천해줘",
    "서귀포시에서 실내 박물관이나 전시관으로 무장애 관광지 골라줘",
    "중구에서 휠체어 가능한 관광지 추천해줘",
    "입장료가 제일 싼 곳 알려줘",
    "응급실은 말고 관광지만 계속",
    "서울 말고 부산으로 다시",
]
DEFAULT_COMPONENT_MESSAGES = [
    "서울에서 휠체어 관광지 추천해줘",
    "서울강남구근처휄체여관광지추천",
    "부산 중구 영상에 글자 안내있는 실내 관광지",
    "전주에서 주차장서 많이 안 걷는 곳",
    "서울에서 휠체어 관광지 추천해줘. 식당이나 카페 말고 관광지 위주로",
    "강릉에서화장실편한제외하고엘레베터기준",
]


def percentile(values: list[float], ratio: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, int(round((len(ordered) - 1) * ratio))))
    return ordered[index]


def summarize(values: list[float]) -> dict[str, float]:
    return {
        "count": len(values),
        "mean_ms": round(mean(values), 4) if values else 0.0,
        "p50_ms": round(median(values), 4) if values else 0.0,
        "p95_ms": round(percentile(values, 0.95), 4),
        "max_ms": round(max(values), 4) if values else 0.0,
    }


def measure_warm_calls(messages: list[str], iterations: int, warmup: int, func) -> dict[str, Any]:
    for index in range(warmup):
        func(messages[index % len(messages)])
    latencies = []
    per_message: dict[str, list[float]] = {message: [] for message in messages}
    for index in range(iterations):
        message = messages[index % len(messages)]
        started = perf_counter()
        func(message)
        elapsed = (perf_counter() - started) * 1000
        latencies.append(elapsed)
        per_message[message].append(elapsed)
    return {
        "overall": summarize(latencies),
        "by_message": {message: summarize(values) for message, values in per_message.items()},
    }


def benchmark_classifier(iterations: int) -> dict[str, Any]:
    start = perf_counter()
    classifier = TourismIntentClassifier()
    load_ms = (perf_counter() - start) * 1000
    latencies = []
    for index in range(iterations):
        text = DEFAULT_MESSAGES[index % len(DEFAULT_MESSAGES)]
        started = perf_counter()
        classifier.predict(text)
        latencies.append((perf_counter() - started) * 1000)
    return {"load_ms": round(load_ms, 4), **summarize(latencies)}


def benchmark_korean_corrector(iterations: int, warmup: int) -> dict[str, Any]:
    settings = Settings()
    started = perf_counter()
    corrector = ExternalKoreanCorrector(settings)
    first_result = corrector.correct("서울강남구근처휄체여관광지추천")
    load_and_first_call_ms = (perf_counter() - started) * 1000
    messages = [
        "서울강남구근처휄체여관광지추천",
        "부산엘베있는실내관광지",
        "성남시장애 화장실관광지추천",
        "강릉에서화장실편한제외하고엘레베터기준",
    ]
    payload = measure_warm_calls(messages, iterations, warmup, lambda message: corrector.correct(message))
    return {
        "load_and_first_call_ms": round(load_and_first_call_ms, 4),
        "first_result_reason": first_result.reason,
        **payload,
    }


def benchmark_condition_transformer(iterations: int, warmup: int) -> dict[str, Any]:
    settings = Settings(tourism_condition_transformer_enabled=True)
    started = perf_counter()
    transformer = TourismConditionTransformer(settings, labels=list(CONDITION_KEYWORDS))
    first_result = transformer.predict("서울에서 소리 없이 안내를 볼 수 있는 곳")
    load_and_first_call_ms = (perf_counter() - started) * 1000
    messages = [
        "서울에서 소리 없이 안내를 볼 수 있는 곳",
        "전주에서 주차장서 많이 안 걷는 곳",
        "부산 중구 영상에 글자 안내있는 실내 관광지",
        "강릉에서화장실편한제외하고엘레베터기준",
    ]
    payload = measure_warm_calls(messages, iterations, warmup, lambda message: transformer.predict(message))
    return {
        "load_and_first_call_ms": round(load_and_first_call_ms, 4),
        "first_result_reason": first_result.get("reason"),
        **payload,
    }


def benchmark_query_extract(iterations: int, warmup: int) -> dict[str, Any]:
    query_service = TourismQueryService()
    return measure_warm_calls(DEFAULT_COMPONENT_MESSAGES, iterations, warmup, query_service.extract)


def benchmark_retriever_top_k(iterations: int, warmup: int, top_k_values: list[int]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for top_k in top_k_values:
        settings = Settings(top_k=top_k, tourism_live_lookup_enabled=False)
        embedding_service = EmbeddingService(settings)
        vector_store = VectorStore(settings)
        retriever = Retriever(settings, embedding_service, vector_store)
        query_embedding = embedding_service.embed_query(DEFAULT_COMPONENT_MESSAGES[0])
        for index in range(warmup):
            vector_store.search(query_embedding=query_embedding, top_k=top_k)

        search_latencies = []
        for _ in range(iterations):
            started = perf_counter()
            vector_store.search(query_embedding=query_embedding, top_k=top_k)
            search_latencies.append((perf_counter() - started) * 1000)

        retrieve_payload = measure_warm_calls(DEFAULT_COMPONENT_MESSAGES, iterations, warmup, retriever.retrieve)
        result[str(top_k)] = {
            "vector_search_only": summarize(search_latencies),
            "embed_plus_vector_retrieve": retrieve_payload["overall"],
            "embed_plus_vector_by_message": retrieve_payload["by_message"],
        }
    return result


def benchmark_components(iterations: int, warmup: int, top_k_values: list[int]) -> dict[str, Any]:
    return {
        "korean_corrector": benchmark_korean_corrector(iterations, warmup),
        "condition_transformer": benchmark_condition_transformer(iterations, warmup),
        "query_extract": benchmark_query_extract(iterations, warmup),
        "retriever_top_k": benchmark_retriever_top_k(iterations, warmup, top_k_values),
    }


def benchmark_chat(iterations: int, warmup: int) -> dict[str, Any]:
    settings = Settings(tourism_live_lookup_enabled=False)
    service = TourismChatService(
        settings=settings,
        retriever=get_retriever(),
        query_service=TourismQueryService(),
        tour_api_service=TourAPIService(settings),
    )
    for index in range(warmup):
        service.answer(DEFAULT_MESSAGES[index % len(DEFAULT_MESSAGES)], session_id=f"latency-warmup-{index}")
    latencies = []
    per_message: dict[str, list[float]] = {message: [] for message in DEFAULT_MESSAGES}
    for index in range(iterations):
        message = DEFAULT_MESSAGES[index % len(DEFAULT_MESSAGES)]
        started = perf_counter()
        service.answer(message, session_id=f"latency-{index}")
        elapsed = (perf_counter() - started) * 1000
        latencies.append(elapsed)
        per_message[message].append(elapsed)
    return {
        "overall": summarize(latencies),
        "by_message": {message: summarize(values) for message, values in per_message.items()},
    }


def load_eval_run_latencies(paths: list[Path]) -> dict[str, Any]:
    result = {}
    for path in paths:
        values = []
        if not path.exists():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            value = row.get("duration_ms")
            if isinstance(value, int | float):
                values.append(float(value))
        result[path.name] = summarize(values)
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Benchmark tourism classifier and chat latency.")
    parser.add_argument("--classifier-iterations", type=int, default=12000)
    parser.add_argument("--chat-iterations", type=int, default=80)
    parser.add_argument("--component-iterations", type=int, default=40)
    parser.add_argument("--warmup-iterations", type=int, default=6)
    parser.add_argument("--top-k-values", type=int, nargs="+", default=[5, 40])
    parser.add_argument(
        "--skip-components",
        action="store_true",
        help="Only run the legacy classifier/chat benchmark.",
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output = args.output if args.output.is_absolute() else PROJECT_ROOT / args.output
    eval_paths = [
        PROJECT_ROOT / "data" / "generated" / "tour_api" / "eval_runs" / "tourism_100_latest.jsonl",
        PROJECT_ROOT / "data" / "generated" / "tour_api" / "eval_runs" / "tourism_challenge_latest.jsonl",
        PROJECT_ROOT / "data" / "generated" / "tour_api" / "eval_runs" / "tourism_conversation_latest.jsonl",
        PROJECT_ROOT / "data" / "generated" / "tour_api" / "eval_runs" / "tourism_expanded_questions_latest.jsonl",
        PROJECT_ROOT / "data" / "generated" / "tour_api" / "eval_runs" / "tourism_expanded_conversation_latest.jsonl",
        PROJECT_ROOT / "data" / "generated" / "tour_api" / "eval_runs" / "tourism_100_live_latest.jsonl",
        PROJECT_ROOT / "data" / "generated" / "tour_api" / "eval_runs" / "tourism_challenge_live_latest.jsonl",
        PROJECT_ROOT / "data" / "generated" / "tour_api" / "eval_runs" / "tourism_conversation_live_latest.jsonl",
        PROJECT_ROOT / "data" / "generated" / "tour_api" / "eval_runs" / "tourism_expanded_questions_live_latest.jsonl",
        PROJECT_ROOT / "data" / "generated" / "tour_api" / "eval_runs" / "tourism_expanded_conversation_live_latest.jsonl",
    ]
    payload = {
        "classifier": benchmark_classifier(args.classifier_iterations),
        "chat_direct_fallback": benchmark_chat(args.chat_iterations, args.warmup_iterations),
        "eval_run_durations": load_eval_run_latencies(eval_paths),
    }
    if not args.skip_components:
        payload["components_warm"] = benchmark_components(
            args.component_iterations,
            args.warmup_iterations,
            args.top_k_values,
        )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
