from __future__ import annotations

import argparse
import json
import math
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import requests


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "data" / "generated" / "tour_api" / "model_benchmarks"
DEFAULT_MODELS = [
    "hf.co/unsloth/gemma-4-E4B-it-qat-GGUF:UD-Q4_K_XL",
    "hf.co/mradermacher/supergemma4-e4b-abliterated-i1-GGUF:Q4_K_M",
    "gemma3:4b-it-q4_K_M",
    "qwen3:4b",
    "gemma4:e4b",
    "huihui_ai/gemma-4-abliterated:e4b",
]

SAMPLE_CARDS = [
    {
        "card_id": "C1",
        "title": "서울어린이대공원",
        "region": "서울 광진구",
        "accessibility": ["휠체어 대여", "장애인 화장실", "장애인 주차"],
        "family": ["유모차 대여", "수유실"],
        "summary": "넓은 산책로와 실내외 관람 시설이 함께 있어 가족 동반 방문에 적합합니다.",
    },
    {
        "card_id": "C2",
        "title": "서울역사박물관",
        "region": "서울 종로구",
        "accessibility": ["장애인 화장실", "엘리베이터", "장애인 주차"],
        "family": ["유모차 접근 가능"],
        "summary": "실내 관람 중심이라 비 오는 날과 장시간 보행이 어려운 동행자에게 비교적 안정적입니다.",
    },
    {
        "card_id": "C3",
        "title": "남산골한옥마을",
        "region": "서울 중구",
        "accessibility": ["장애인 화장실"],
        "family": ["전통문화 체험"],
        "summary": "야외 이동 구간이 있고 일부 바닥 상태는 현장 확인이 필요합니다.",
    },
    {
        "card_id": "C4",
        "title": "서울식물원",
        "region": "서울 강서구",
        "accessibility": ["휠체어 대여", "장애인 화장실", "엘리베이터"],
        "family": ["유모차 접근 가능", "실내 온실"],
        "summary": "실내 온실과 넓은 동선이 있어 날씨 영향을 줄이면서 가족이 함께 보기 좋습니다.",
    },
]

EMBEDDING_DOCUMENTS = [
    {
        "id": "D1",
        "text": "서울어린이대공원은 휠체어 대여, 장애인 화장실, 장애인 주차, 유모차 대여와 수유실 정보가 있는 가족 동반 관광지다.",
    },
    {
        "id": "D2",
        "text": "서울역사박물관은 실내 관람 중심이며 엘리베이터와 장애인 화장실, 장애인 주차 정보가 확인된다.",
    },
    {
        "id": "D3",
        "text": "남산골한옥마을은 전통문화 체험 장소이며 일부 야외 이동 구간과 바닥 상태는 현장 확인이 필요하다.",
    },
    {
        "id": "D4",
        "text": "서울식물원은 실내 온실, 휠체어 대여, 엘리베이터, 장애인 화장실, 유모차 접근 가능 정보가 있는 관광지다.",
    },
    {
        "id": "D5",
        "text": "부산 영화의전당은 공연장과 영화 상영 시설 중심이며 휠체어 관람석과 장애인 화장실 확인이 필요하다.",
    },
]

EMBEDDING_QUERIES = [
    {
        "query": "비 오는 날 휠체어 이용자와 아이가 함께 갈 서울 실내 관광지",
        "expected": "D2",
        "acceptable": ["D2", "D4"],
    },
    {
        "query": "수유실과 유모차 대여가 있는 가족 관광지",
        "expected": "D1",
        "acceptable": ["D1"],
    },
    {
        "query": "실내 온실이 있고 엘리베이터가 있는 곳",
        "expected": "D4",
        "acceptable": ["D4"],
    },
    {
        "query": "전통문화 체험이 가능한 한옥 관광지",
        "expected": "D3",
        "acceptable": ["D3"],
    },
]


def reasoning_prompt() -> str:
    return (
        "너는 무장애 관광 상담 보조 모델이다. 아래 후보 카드만 사용해서 사용자의 복합 조건에 맞는 순서를 골라라.\n"
        "없는 장소, 없는 편의시설, 확인되지 않은 사실을 만들지 마라.\n"
        "판단은 짧게 끝내고 최종 출력은 JSON만 남겨라.\n"
        '반드시 JSON만 출력한다. 형식: {"ranked_ids":["C2","C4"],"missing_or_uncertain":["..."]}\n\n'
        "사용자 질문: 비가 와도 괜찮고, 휠체어 타시는 아버지와 초등학생 아이가 같이 가기 좋은 서울 관광지를 추천해줘.\n"
        f"후보 카드:\n{json.dumps(SAMPLE_CARDS, ensure_ascii=False, indent=2)}"
    )


def final_answer_prompt() -> str:
    return (
        "너는 무장애 관광 상담 챗봇이다. 아래 카드만 근거로 한국어 답변을 짧게 작성하라.\n"
        "접근성 정보가 없으면 추측하지 말고 확인 필요라고 말하라.\n\n"
        "판단은 짧게 끝내고 사용자에게 보여줄 최종 답변만 작성하라.\n\n"
        "사용자 질문: 비가 와도 괜찮고, 휠체어 타시는 아버지와 초등학생 아이가 같이 가기 좋은 서울 관광지를 추천해줘.\n"
        f"추천 카드:\n{json.dumps(SAMPLE_CARDS[:3], ensure_ascii=False, indent=2)}"
    )


def extract_json_object(text: str) -> dict[str, Any] | None:
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = re.sub(r"^```(?:json)?\s*", "", stripped, flags=re.IGNORECASE)
        stripped = re.sub(r"\s*```$", "", stripped)
    try:
        parsed = json.loads(stripped)
        return parsed if isinstance(parsed, dict) else None
    except json.JSONDecodeError:
        pass

    start = stripped.find("{")
    end = stripped.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None
    try:
        parsed = json.loads(stripped[start : end + 1])
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


def valid_ranked_ids(parsed: dict[str, Any] | None) -> list[str]:
    if not parsed:
        return []
    ranked_ids = parsed.get("ranked_ids")
    if not isinstance(ranked_ids, list):
        return []
    known_ids = {card["card_id"] for card in SAMPLE_CARDS}
    return [card_id for card_id in ranked_ids if isinstance(card_id, str) and card_id in known_ids]


def call_ollama_generate(
    base_url: str,
    model: str,
    prompt: str,
    think: bool | None,
    timeout: float,
    num_predict: int,
) -> tuple[dict[str, Any] | None, str | None, float]:
    payload: dict[str, Any] = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "keep_alive": "10m",
        "options": {
            "temperature": 0.1,
            "num_predict": num_predict,
        },
    }
    if think is not None:
        payload["think"] = think

    started = time.perf_counter()
    try:
        response = requests.post(f"{base_url.rstrip('/')}/api/generate", json=payload, timeout=timeout)
        elapsed_ms = round((time.perf_counter() - started) * 1000, 1)
        response.raise_for_status()
        return response.json(), None, elapsed_ms
    except requests.RequestException as exc:
        elapsed_ms = round((time.perf_counter() - started) * 1000, 1)
        return None, str(exc), elapsed_ms


def call_openai_compatible_chat(
    base_url: str,
    model: str,
    prompt: str,
    timeout: float,
    num_predict: int,
) -> tuple[dict[str, Any] | None, str | None, float]:
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.1,
        "max_tokens": num_predict,
        "stream": False,
    }
    started = time.perf_counter()
    try:
        response = requests.post(f"{base_url.rstrip('/')}/chat/completions", json=payload, timeout=timeout)
        elapsed_ms = round((time.perf_counter() - started) * 1000, 1)
        response.raise_for_status()
        data = response.json()
    except requests.RequestException as exc:
        elapsed_ms = round((time.perf_counter() - started) * 1000, 1)
        return None, str(exc), elapsed_ms

    choices = data.get("choices")
    message = choices[0].get("message") if isinstance(choices, list) and choices else {}
    content = message.get("content") if isinstance(message, dict) else ""
    if not isinstance(content, str):
        content = ""
    return {"response": content, "raw": data, "usage": data.get("usage")}, None, elapsed_ms


def model_show(base_url: str, model: str, timeout: float) -> dict[str, Any]:
    try:
        response = requests.post(f"{base_url.rstrip('/')}/api/show", json={"model": model}, timeout=timeout)
        response.raise_for_status()
        data = response.json()
    except requests.RequestException as exc:
        return {"error": str(exc)}
    return {
        "details": data.get("details", {}),
        "model_info": data.get("model_info", {}),
        "capabilities": data.get("capabilities", []),
    }


def openai_compatible_model_show(base_url: str, timeout: float) -> dict[str, Any]:
    try:
        response = requests.get(f"{base_url.rstrip('/')}/models", timeout=timeout)
        response.raise_for_status()
        return {"models": response.json().get("data", [])}
    except requests.RequestException as exc:
        return {"error": str(exc)}


def benchmark_model(
    provider: str,
    base_url: str,
    model: str,
    runs: int,
    timeout: float,
    include_thinking: bool,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    show = model_show(base_url, model, timeout) if provider == "ollama" else openai_compatible_model_show(base_url, timeout)
    scenarios = [
        ("reasoning_json", reasoning_prompt(), 160),
        ("final_answer_ko", final_answer_prompt(), 220),
    ]

    for scenario, prompt, num_predict in scenarios:
        for run_index in range(1, runs + 1):
            if provider == "ollama":
                data, error_message, elapsed_ms = call_ollama_generate(
                    base_url=base_url,
                    model=model,
                    prompt=prompt,
                    think=False,
                    timeout=timeout,
                    num_predict=num_predict,
                )
            else:
                data, error_message, elapsed_ms = call_openai_compatible_chat(
                    base_url=base_url,
                    model=model,
                    prompt=prompt,
                    timeout=timeout,
                    num_predict=num_predict,
                )
            rows.append(build_row(model, show, scenario, run_index, False, data, error_message, elapsed_ms, provider))

            if include_thinking and provider == "ollama":
                thinking_num_predict = max(num_predict * 10, 1536)
                data, error_message, elapsed_ms = call_ollama_generate(
                    base_url=base_url,
                    model=model,
                    prompt=prompt,
                    think=True,
                    timeout=timeout,
                    num_predict=thinking_num_predict,
                )
                rows.append(build_row(model, show, scenario, run_index, True, data, error_message, elapsed_ms, provider))
    return rows


def build_row(
    model: str,
    show: dict[str, Any],
    scenario: str,
    run_index: int,
    think: bool,
    data: dict[str, Any] | None,
    error_message: str | None,
    elapsed_ms: float,
    provider: str = "ollama",
) -> dict[str, Any]:
    response_text = ""
    thinking_text = ""
    if data:
        response_text = data.get("response") if isinstance(data.get("response"), str) else ""
        thinking_text = data.get("thinking") if isinstance(data.get("thinking"), str) else ""

    parsed = extract_json_object(response_text) if scenario == "reasoning_json" else None
    ranked_ids = valid_ranked_ids(parsed)
    return {
        "model": model,
        "provider": provider,
        "task": "generation",
        "scenario": scenario,
        "run_index": run_index,
        "think": think,
        "elapsed_ms": elapsed_ms,
        "error": error_message,
        "supports_native_thinking_observed": bool(thinking_text),
        "thinking_chars": len(thinking_text),
        "response_chars": len(response_text),
        "json_parse_ok": parsed is not None if scenario == "reasoning_json" else None,
        "ranked_ids": ranked_ids,
        "ranked_id_count": len(ranked_ids),
        "response_excerpt": response_text[:500],
        "thinking_excerpt": thinking_text[:500],
        "total_duration_ns": data.get("total_duration") if data else None,
        "load_duration_ns": data.get("load_duration") if data else None,
        "prompt_eval_count": data.get("prompt_eval_count") if data else None,
        "eval_count": data.get("eval_count") if data else None,
        "eval_duration_ns": data.get("eval_duration") if data else None,
        "model_details": show.get("details", {}),
        "model_capabilities": show.get("capabilities", []),
        "model_list": show.get("models", []),
        "show_error": show.get("error"),
    }


def call_ollama_embeddings(
    base_url: str,
    model: str,
    texts: list[str],
    timeout: float,
) -> tuple[list[list[float]] | None, str | None, float]:
    started = time.perf_counter()
    try:
        response = requests.post(
            f"{base_url.rstrip('/')}/api/embed",
            json={"model": model, "input": texts},
            timeout=timeout,
        )
        elapsed_ms = round((time.perf_counter() - started) * 1000, 1)
        response.raise_for_status()
        data = response.json()
    except requests.RequestException as exc:
        elapsed_ms = round((time.perf_counter() - started) * 1000, 1)
        return None, str(exc), elapsed_ms
    embeddings = data.get("embeddings")
    return embeddings if isinstance(embeddings, list) else None, None, elapsed_ms


def call_openai_compatible_embeddings(
    base_url: str,
    model: str,
    texts: list[str],
    timeout: float,
) -> tuple[list[list[float]] | None, str | None, float]:
    started = time.perf_counter()
    try:
        response = requests.post(
            f"{base_url.rstrip('/')}/embeddings",
            json={"model": model, "input": texts},
            timeout=timeout,
        )
        elapsed_ms = round((time.perf_counter() - started) * 1000, 1)
        response.raise_for_status()
        data = response.json()
    except requests.RequestException as exc:
        elapsed_ms = round((time.perf_counter() - started) * 1000, 1)
        return None, str(exc), elapsed_ms
    items = data.get("data")
    if not isinstance(items, list):
        return None, "embedding response missing data list", elapsed_ms
    embeddings = [item.get("embedding") for item in items if isinstance(item, dict)]
    return embeddings if embeddings else None, None, elapsed_ms


def cosine_similarity(left: list[float], right: list[float]) -> float:
    numerator = sum(a * b for a, b in zip(left, right, strict=False))
    left_norm = math.sqrt(sum(a * a for a in left))
    right_norm = math.sqrt(sum(b * b for b in right))
    if not left_norm or not right_norm:
        return 0.0
    return numerator / (left_norm * right_norm)


def benchmark_embeddings(
    provider: str,
    base_url: str,
    model: str,
    timeout: float,
) -> list[dict[str, Any]]:
    texts = [doc["text"] for doc in EMBEDDING_DOCUMENTS] + [item["query"] for item in EMBEDDING_QUERIES]
    if provider == "ollama":
        embeddings, error_message, elapsed_ms = call_ollama_embeddings(base_url, model, texts, timeout)
    else:
        embeddings, error_message, elapsed_ms = call_openai_compatible_embeddings(base_url, model, texts, timeout)

    rows: list[dict[str, Any]] = []
    if error_message or not embeddings or len(embeddings) != len(texts):
        return [
            {
                "provider": provider,
                "task": "embedding",
                "model": model,
                "scenario": "batch_embedding",
                "elapsed_ms": elapsed_ms,
                "error": error_message or "embedding_count_mismatch",
                "input_count": len(texts),
                "embedding_count": len(embeddings or []),
            }
        ]

    doc_embeddings = embeddings[: len(EMBEDDING_DOCUMENTS)]
    query_embeddings = embeddings[len(EMBEDDING_DOCUMENTS) :]
    for query_case, query_embedding in zip(EMBEDDING_QUERIES, query_embeddings, strict=True):
        scores = [
            (doc["id"], cosine_similarity(query_embedding, doc_embedding))
            for doc, doc_embedding in zip(EMBEDDING_DOCUMENTS, doc_embeddings, strict=True)
        ]
        ranked = sorted(scores, key=lambda item: item[1], reverse=True)
        top_id = ranked[0][0] if ranked else ""
        rows.append(
            {
                "provider": provider,
                "task": "embedding",
                "model": model,
                "scenario": "tourism_retrieval_probe",
                "elapsed_ms": elapsed_ms,
                "error": None,
                "query": query_case["query"],
                "expected": query_case["expected"],
                "acceptable": query_case["acceptable"],
                "top_id": top_id,
                "top1_ok": top_id in query_case["acceptable"],
                "ranked_ids": [item[0] for item in ranked],
                "ranked_scores": [round(item[1], 6) for item in ranked],
                "embedding_dimension": len(query_embedding),
                "input_count": len(texts),
            }
        )
    return rows


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        for row in rows:
            file.write(json.dumps(row, ensure_ascii=False) + "\n")


def default_output_path() -> Path:
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    return DEFAULT_OUTPUT_DIR / f"tourism_model_benchmark_{timestamp}.jsonl"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Benchmark local AI providers for tourism RAG migration decisions.")
    parser.add_argument("--provider", choices=["ollama", "openai-compatible"], default=os.environ.get("LOCAL_AI_PROVIDER", "ollama"))
    parser.add_argument("--base-url", default=None)
    parser.add_argument("--models", nargs="+", default=None)
    parser.add_argument("--embedding-model", default=None)
    parser.add_argument("--runs", type=int, default=1)
    parser.add_argument("--timeout", type=float, default=240.0)
    parser.add_argument("--output", type=Path, default=default_output_path())
    parser.add_argument("--skip-generation", action="store_true")
    parser.add_argument("--skip-embeddings", action="store_true")
    parser.add_argument(
        "--no-thinking",
        action="store_true",
        help="Skip think=true measurements. By default, think=true is attempted and unsupported models are recorded as errors.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    base_url = args.base_url
    if base_url is None:
        base_url = (
            os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
            if args.provider == "ollama"
            else os.environ.get("OPENAI_COMPATIBLE_BASE_URL", "http://localhost:8000/v1")
        )
    models = args.models or DEFAULT_MODELS
    embedding_model = args.embedding_model or (
        os.environ.get("OLLAMA_EMBED_MODEL", "bge-m3")
        if args.provider == "ollama"
        else os.environ.get("OPENAI_COMPATIBLE_EMBED_MODEL", "bge-m3")
    )
    rows: list[dict[str, Any]] = []
    if not args.skip_generation:
        for model in models:
            print(f"\n== {args.provider} generation: {model} ==", flush=True)
            model_rows = benchmark_model(
                provider=args.provider,
                base_url=base_url,
                model=model,
                runs=args.runs,
                timeout=args.timeout,
                include_thinking=not args.no_thinking,
            )
            rows.extend(model_rows)
            for row in model_rows:
                status = "error" if row["error"] else "ok"
                print(
                    f"{row['scenario']} think={row['think']} {status} "
                    f"{row['elapsed_ms']}ms json={row['json_parse_ok']} "
                    f"native_think={row['supports_native_thinking_observed']}",
                    flush=True,
                )
    if not args.skip_embeddings:
        print(f"\n== {args.provider} embeddings: {embedding_model} ==", flush=True)
        embedding_rows = benchmark_embeddings(args.provider, base_url, embedding_model, args.timeout)
        rows.extend(embedding_rows)
        for row in embedding_rows:
            status = "error" if row["error"] else "ok"
            if row.get("scenario") == "tourism_retrieval_probe":
                print(
                    f"embedding {status} {row['elapsed_ms']}ms top={row['top_id']} "
                    f"ok={row['top1_ok']} dim={row['embedding_dimension']}",
                    flush=True,
                )
            else:
                print(f"embedding {status} {row['elapsed_ms']}ms error={row['error']}", flush=True)
    write_jsonl(args.output, rows)
    print(f"\nWrote {len(rows)} rows to {args.output}")


if __name__ == "__main__":
    main()
