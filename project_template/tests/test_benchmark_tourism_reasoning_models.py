import json

from scripts import benchmark_tourism_reasoning_models as benchmark


def test_extract_json_object_accepts_fenced_json():
    parsed = benchmark.extract_json_object(
        """```json
{"ranked_ids":["C2","C4"],"missing_or_uncertain":["혼잡도"]}
```"""
    )

    assert parsed == {"ranked_ids": ["C2", "C4"], "missing_or_uncertain": ["혼잡도"]}


def test_valid_ranked_ids_filters_unknown_ids():
    ranked_ids = benchmark.valid_ranked_ids({"ranked_ids": ["C2", "BAD", "C4", 3]})

    assert ranked_ids == ["C2", "C4"]


def test_build_row_records_reasoning_json_parse():
    data = {
        "response": json.dumps({"ranked_ids": ["C2", "C4"], "missing_or_uncertain": []}, ensure_ascii=False),
        "thinking": "후보를 비교함",
        "total_duration": 123,
        "load_duration": 4,
        "prompt_eval_count": 5,
        "eval_count": 6,
        "eval_duration": 7,
    }

    row = benchmark.build_row(
        model="sample",
        show={"details": {"parameter_size": "4B"}, "capabilities": ["completion"]},
        scenario="reasoning_json",
        run_index=1,
        think=True,
        data=data,
        error_message=None,
        elapsed_ms=10.5,
    )

    assert row["json_parse_ok"] is True
    assert row["ranked_ids"] == ["C2", "C4"]
    assert row["supports_native_thinking_observed"] is True
    assert row["thinking_chars"] > 0


def test_write_jsonl_keeps_relative_generated_output(tmp_path):
    output = tmp_path / "bench.jsonl"

    benchmark.write_jsonl(output, [{"model": "gemma4:e4b", "scenario": "reasoning_json"}])

    assert "gemma4:e4b" in output.read_text(encoding="utf-8")


def test_cosine_similarity_ranks_related_vectors():
    related = benchmark.cosine_similarity([1.0, 0.0, 0.0], [0.9, 0.1, 0.0])
    unrelated = benchmark.cosine_similarity([1.0, 0.0, 0.0], [0.0, 1.0, 0.0])

    assert related > unrelated


def test_openai_compatible_embedding_error_row_on_bad_response(monkeypatch):
    def fake_embeddings(base_url, model, texts, timeout):
        return [[0.1, 0.2]], None, 12.3

    monkeypatch.setattr(benchmark, "call_openai_compatible_embeddings", fake_embeddings)

    rows = benchmark.benchmark_embeddings("openai-compatible", "http://localhost:8000/v1", "embed-model", 10)

    assert rows == [
        {
            "provider": "openai-compatible",
            "task": "embedding",
            "model": "embed-model",
            "scenario": "batch_embedding",
            "elapsed_ms": 12.3,
            "error": "embedding_count_mismatch",
            "input_count": 9,
            "embedding_count": 1,
        }
    ]


def test_benchmark_embeddings_records_top1(monkeypatch):
    doc_embeddings = [
        [1.0, 0.0, 0.0],
        [0.0, 1.0, 0.0],
        [0.0, 0.0, 1.0],
        [0.7, 0.7, 0.0],
        [0.1, 0.1, 0.9],
    ]
    query_embeddings = [
        [0.0, 1.0, 0.0],
        [1.0, 0.0, 0.0],
        [0.7, 0.7, 0.0],
        [0.0, 0.0, 1.0],
    ]

    def fake_embeddings(base_url, model, texts, timeout):
        return doc_embeddings + query_embeddings, None, 45.6

    monkeypatch.setattr(benchmark, "call_ollama_embeddings", fake_embeddings)

    rows = benchmark.benchmark_embeddings("ollama", "http://localhost:11434", "bge-m3", 10)

    assert len(rows) == 4
    assert rows[0]["top_id"] == "D2"
    assert rows[0]["top1_ok"] is True
    assert rows[0]["embedding_dimension"] == 3
