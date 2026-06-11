from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
from datetime import datetime
import hashlib
import json
import math
from pathlib import Path
import sys
import time
from typing import Callable
import urllib.request

import numpy as np
from rank_bm25 import BM25Okapi

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.build_autorag_tourism_dataset import (  # noqa: E402
    DEFAULT_CORPUS_INPUTS,
    DEFAULT_EVAL_INPUTS,
    build_corpus,
    build_qa_rows,
)


DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "data" / "generated" / "tour_api" / "autorag_bm25_tokenizers"
DEFAULT_TOKENIZERS = ["space", "ko_kiwi", "ko_okt", "ko_kkma"]
DEFAULT_TOP_KS = [5, 10, 20, 40]


@dataclass
class TokenizerResult:
    tokenizer: str
    corpus_docs: int
    qa_rows: int
    top_k: int
    hit_rate: float
    recall: float
    precision: float
    mrr: float
    ndcg: float
    corpus_tokenize_ms: float
    search_ms: float
    total_ms: float
    avg_doc_tokens: float
    avg_query_tokens: float


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Benchmark Korean BM25 tokenizers on the tourism AutoRAG retrieval dataset.",
    )
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--corpus-input", action="append", type=Path, dest="corpus_inputs")
    parser.add_argument("--eval-input", action="append", type=Path, dest="eval_inputs")
    parser.add_argument("--max-eval-rows", type=int, default=220)
    parser.add_argument("--min-ground-truth", type=int, default=1)
    parser.add_argument("--top-k", action="append", type=int, dest="top_ks")
    parser.add_argument("--tokenizer", action="append", choices=DEFAULT_TOKENIZERS, dest="tokenizers")
    parser.add_argument("--include-ollama-vector", action="store_true")
    parser.add_argument("--ollama-base-url", default="http://localhost:11434")
    parser.add_argument("--embedding-model", default="bge-m3")
    parser.add_argument("--embedding-batch-size", type=int, default=32)
    return parser.parse_args()


def space_tokenize(text: str) -> list[str]:
    return [token for token in text.split() if token]


def build_tokenizer(name: str) -> Callable[[str], list[str]]:
    if name == "space":
        return space_tokenize
    if name == "ko_kiwi":
        from kiwipiepy import Kiwi

        kiwi = Kiwi()
        return lambda text: [token.form for token in kiwi.tokenize(text) if token.form.strip()]
    if name == "ko_okt":
        from konlpy.tag import Okt

        okt = Okt()
        return lambda text: [token for token in okt.morphs(text) if token.strip()]
    if name == "ko_kkma":
        from konlpy.tag import Kkma

        kkma = Kkma()
        return lambda text: [token for token in kkma.morphs(text) if token.strip()]
    raise ValueError(f"Unsupported tokenizer: {name}")


def flatten_ground_truth(row: dict[str, object]) -> set[str]:
    gt = row.get("retrieval_gt") or []
    if gt and isinstance(gt, list) and isinstance(gt[0], list):
        return {str(item) for item in gt[0]}
    if isinstance(gt, list):
        return {str(item) for item in gt}
    return set()


def reciprocal_rank(ranked_ids: list[str], gt_ids: set[str]) -> float:
    for index, doc_id in enumerate(ranked_ids, start=1):
        if doc_id in gt_ids:
            return 1.0 / index
    return 0.0


def ndcg_at_k(ranked_ids: list[str], gt_ids: set[str], top_k: int) -> float:
    if not gt_ids:
        return 0.0
    dcg = 0.0
    for index, doc_id in enumerate(ranked_ids[:top_k], start=1):
        if doc_id in gt_ids:
            dcg += 1.0 / math.log2(index + 1)
    ideal_hits = min(len(gt_ids), top_k)
    idcg = sum(1.0 / math.log2(index + 1) for index in range(1, ideal_hits + 1))
    return dcg / idcg if idcg else 0.0


def evaluate_tokenizer(
    name: str,
    tokenize: Callable[[str], list[str]],
    doc_ids: list[str],
    doc_texts: list[str],
    qa_rows: list[dict[str, object]],
    top_ks: list[int],
) -> list[TokenizerResult]:
    total_start = time.perf_counter()
    corpus_start = time.perf_counter()
    tokenized_docs = [tokenize(text) for text in doc_texts]
    corpus_tokenize_ms = (time.perf_counter() - corpus_start) * 1000
    bm25 = BM25Okapi(tokenized_docs)

    rows_by_k = {
        top_k: {
            "hits": 0,
            "recall": 0.0,
            "precision": 0.0,
            "mrr": 0.0,
            "ndcg": 0.0,
        }
        for top_k in top_ks
    }
    query_token_count = 0
    search_start = time.perf_counter()
    for qa_row in qa_rows:
        gt_ids = flatten_ground_truth(qa_row)
        query_tokens = tokenize(str(qa_row["query"]))
        query_token_count += len(query_tokens)
        scores = bm25.get_scores(query_tokens)
        ranked_indexes = sorted(range(len(scores)), key=lambda index: scores[index], reverse=True)
        ranked_ids = [doc_ids[index] for index in ranked_indexes]
        for top_k in top_ks:
            top_ids = ranked_ids[:top_k]
            found = len(gt_ids.intersection(top_ids))
            rows_by_k[top_k]["hits"] += 1 if found else 0
            rows_by_k[top_k]["recall"] += found / len(gt_ids) if gt_ids else 0.0
            rows_by_k[top_k]["precision"] += found / top_k
            rows_by_k[top_k]["mrr"] += reciprocal_rank(top_ids, gt_ids)
            rows_by_k[top_k]["ndcg"] += ndcg_at_k(top_ids, gt_ids, top_k)
    search_ms = (time.perf_counter() - search_start) * 1000
    total_ms = (time.perf_counter() - total_start) * 1000

    qa_count = len(qa_rows)
    doc_count = len(doc_texts)
    avg_doc_tokens = sum(len(tokens) for tokens in tokenized_docs) / doc_count if doc_count else 0.0
    avg_query_tokens = query_token_count / qa_count if qa_count else 0.0
    results = []
    for top_k in top_ks:
        values = rows_by_k[top_k]
        results.append(
            TokenizerResult(
                tokenizer=name,
                corpus_docs=doc_count,
                qa_rows=qa_count,
                top_k=top_k,
                hit_rate=values["hits"] / qa_count if qa_count else 0.0,
                recall=values["recall"] / qa_count if qa_count else 0.0,
                precision=values["precision"] / qa_count if qa_count else 0.0,
                mrr=values["mrr"] / qa_count if qa_count else 0.0,
                ndcg=values["ndcg"] / qa_count if qa_count else 0.0,
                corpus_tokenize_ms=corpus_tokenize_ms,
                search_ms=search_ms,
                total_ms=total_ms,
                avg_doc_tokens=avg_doc_tokens,
                avg_query_tokens=avg_query_tokens,
            )
        )
    return results


def embedding_cache_key(model: str, text: str) -> str:
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    return f"{model}:{digest}"


def load_embedding_cache(path: Path) -> dict[str, list[float]]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def save_embedding_cache(path: Path, cache: dict[str, list[float]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")


def ollama_embed_batch(base_url: str, model: str, texts: list[str]) -> list[list[float]]:
    payload = json.dumps({"model": model, "input": texts}).encode("utf-8")
    request = urllib.request.Request(
        f"{base_url.rstrip('/')}/api/embed",
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=300) as response:
        body = json.load(response)
    embeddings = body.get("embeddings")
    if not isinstance(embeddings, list) or len(embeddings) != len(texts):
        raise RuntimeError("Ollama /api/embed returned an unexpected payload.")
    return embeddings


def embed_texts(
    texts: list[str],
    *,
    base_url: str,
    model: str,
    batch_size: int,
    cache_path: Path,
) -> list[list[float]]:
    cache = load_embedding_cache(cache_path)
    results: list[list[float] | None] = [None] * len(texts)
    missing: list[tuple[int, str, str]] = []
    for index, text in enumerate(texts):
        key = embedding_cache_key(model, text)
        value = cache.get(key)
        if value is None:
            missing.append((index, key, text))
        else:
            results[index] = value
    for offset in range(0, len(missing), batch_size):
        batch = missing[offset : offset + batch_size]
        embeddings = ollama_embed_batch(base_url, model, [item[2] for item in batch])
        for (index, key, _), embedding in zip(batch, embeddings, strict=True):
            cache[key] = embedding
            results[index] = embedding
        save_embedding_cache(cache_path, cache)
    return [embedding for embedding in results if embedding is not None]


def normalize_matrix(vectors: list[list[float]]) -> np.ndarray:
    matrix = np.asarray(vectors, dtype=np.float32)
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    norms[norms == 0.0] = 1.0
    return matrix / norms


def evaluate_vector_retrieval(
    method_name: str,
    doc_ids: list[str],
    doc_texts: list[str],
    qa_rows: list[dict[str, object]],
    top_ks: list[int],
    *,
    base_url: str,
    model: str,
    batch_size: int,
    cache_path: Path,
) -> list[TokenizerResult]:
    total_start = time.perf_counter()
    doc_embed_start = time.perf_counter()
    doc_embeddings = normalize_matrix(
        embed_texts(doc_texts, base_url=base_url, model=model, batch_size=batch_size, cache_path=cache_path)
    )
    corpus_tokenize_ms = (time.perf_counter() - doc_embed_start) * 1000
    query_texts = [str(row["query"]) for row in qa_rows]
    search_start = time.perf_counter()
    query_embeddings = normalize_matrix(
        embed_texts(query_texts, base_url=base_url, model=model, batch_size=batch_size, cache_path=cache_path)
    )
    scores_matrix = query_embeddings @ doc_embeddings.T

    rows_by_k = {
        top_k: {
            "hits": 0,
            "recall": 0.0,
            "precision": 0.0,
            "mrr": 0.0,
            "ndcg": 0.0,
        }
        for top_k in top_ks
    }
    max_k = max(top_ks)
    for qa_row, scores in zip(qa_rows, scores_matrix, strict=True):
        gt_ids = flatten_ground_truth(qa_row)
        ranked_indexes = np.argsort(-scores)[:max_k]
        ranked_ids = [doc_ids[int(index)] for index in ranked_indexes]
        for top_k in top_ks:
            top_ids = ranked_ids[:top_k]
            found = len(gt_ids.intersection(top_ids))
            rows_by_k[top_k]["hits"] += 1 if found else 0
            rows_by_k[top_k]["recall"] += found / len(gt_ids) if gt_ids else 0.0
            rows_by_k[top_k]["precision"] += found / top_k
            rows_by_k[top_k]["mrr"] += reciprocal_rank(top_ids, gt_ids)
            rows_by_k[top_k]["ndcg"] += ndcg_at_k(top_ids, gt_ids, top_k)
    search_ms = (time.perf_counter() - search_start) * 1000
    total_ms = (time.perf_counter() - total_start) * 1000

    qa_count = len(qa_rows)
    doc_count = len(doc_texts)
    return [
        TokenizerResult(
            tokenizer=method_name,
            corpus_docs=doc_count,
            qa_rows=qa_count,
            top_k=top_k,
            hit_rate=values["hits"] / qa_count if qa_count else 0.0,
            recall=values["recall"] / qa_count if qa_count else 0.0,
            precision=values["precision"] / qa_count if qa_count else 0.0,
            mrr=values["mrr"] / qa_count if qa_count else 0.0,
            ndcg=values["ndcg"] / qa_count if qa_count else 0.0,
            corpus_tokenize_ms=corpus_tokenize_ms,
            search_ms=search_ms,
            total_ms=total_ms,
            avg_doc_tokens=0.0,
            avg_query_tokens=0.0,
        )
        for top_k, values in rows_by_k.items()
    ]


def write_report(output_dir: Path, results: list[TokenizerResult], summary: dict[str, object]) -> None:
    rows = sorted(results, key=lambda item: (item.top_k, -item.recall, -item.mrr, item.total_ms))
    lines = [
        "# Tourism BM25 Tokenizer Benchmark",
        "",
        "AutoRAG blog tokenizer candidates were replayed against this project's tourism corpus and heuristic QA mapping.",
        "Use this as retrieval-screening evidence, not as final `/tourism/chat` quality evidence.",
        "",
        f"- Created at: {summary['created_at']}",
        f"- Corpus docs: {summary['corpus_docs']}",
        f"- QA rows: {summary['qa_rows']}",
        f"- Tokenizers: {', '.join(str(item) for item in summary['tokenizers'])}",
        f"- Vector method: {summary.get('vector_method') or 'not run'}",
        "",
        "| top_k | tokenizer | hit_rate | recall | precision | mrr | ndcg | corpus_tokenize_ms | search_ms | avg_doc_tokens |",
        "|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in rows:
        lines.append(
            "| "
            f"{row.top_k} | {row.tokenizer} | {row.hit_rate:.4f} | {row.recall:.4f} | "
            f"{row.precision:.4f} | {row.mrr:.4f} | {row.ndcg:.4f} | "
            f"{row.corpus_tokenize_ms:.1f} | {row.search_ms:.1f} | {row.avg_doc_tokens:.1f} |"
        )
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    args = parse_args()
    output_dir = args.output_dir
    if not output_dir.is_absolute():
        output_dir = PROJECT_ROOT / output_dir
    top_ks = sorted(set(args.top_ks or DEFAULT_TOP_KS))
    tokenizers = args.tokenizers or DEFAULT_TOKENIZERS
    corpus_inputs = args.corpus_inputs or DEFAULT_CORPUS_INPUTS
    eval_inputs = args.eval_inputs or DEFAULT_EVAL_INPUTS

    corpus_rows = build_corpus(corpus_inputs)
    if not corpus_rows:
        raise SystemExit("No tourism markdown corpus rows found.")
    qa_rows = build_qa_rows(eval_inputs, corpus_rows, args.max_eval_rows, args.min_ground_truth)
    if not qa_rows:
        raise SystemExit("No QA rows matched corpus docs.")

    doc_ids = [row.doc_id for row in corpus_rows]
    doc_texts = [row.contents for row in corpus_rows]
    all_results: list[TokenizerResult] = []
    for tokenizer_name in tokenizers:
        print(f"benchmarking {tokenizer_name} ...", flush=True)
        tokenize = build_tokenizer(tokenizer_name)
        all_results.extend(evaluate_tokenizer(tokenizer_name, tokenize, doc_ids, doc_texts, qa_rows, top_ks))
    vector_method = None
    if args.include_ollama_vector:
        vector_method = f"vector_{args.embedding_model}"
        print(f"benchmarking {vector_method} ...", flush=True)
        all_results.extend(
            evaluate_vector_retrieval(
                vector_method,
                doc_ids,
                doc_texts,
                qa_rows,
                top_ks,
                base_url=args.ollama_base_url,
                model=args.embedding_model,
                batch_size=args.embedding_batch_size,
                cache_path=output_dir / "embedding_cache.json",
            )
        )

    summary = {
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "corpus_docs": len(corpus_rows),
        "qa_rows": len(qa_rows),
        "tokenizers": tokenizers,
        "vector_method": vector_method,
        "top_ks": top_ks,
        "notes": [
            "Ground truth is generated by scripts/build_autorag_tourism_dataset.py heuristics.",
            "BM25 tokenizer results should be combined with vector/hybrid AutoRAG runs before runtime adoption.",
        ],
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "summary.json").write_text(
        json.dumps(
            {
                **summary,
                "results": [asdict(result) for result in all_results],
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    write_report(output_dir, all_results, summary)
    print(f"wrote {output_dir.relative_to(PROJECT_ROOT) / 'summary.md'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
