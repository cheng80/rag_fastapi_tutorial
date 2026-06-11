from __future__ import annotations

import argparse
from itertools import product
import json
from pathlib import Path
import subprocess
import sys
import time
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_ROOT = PROJECT_ROOT / "data" / "generated" / "tour_api" / "context_transformer_grid"
DEFAULT_SUMMARY = PROJECT_ROOT / "data" / "generated" / "tour_api" / "context_transformer_grid_latest.json"
DEFAULT_BASELINE_METRICS = PROJECT_ROOT / "data" / "generated" / "tour_api" / "context_classifier_eval_augmented_latest.json"


def parse_csv_int(value: str) -> list[int]:
    return [int(part.strip()) for part in value.split(",") if part.strip()]


def parse_csv_float(value: str) -> list[float]:
    return [float(part.strip()) for part in value.split(",") if part.strip()]


def run_one(args: argparse.Namespace, epoch: int, batch_size: int, learning_rate: float) -> dict[str, Any]:
    run_name = f"e{epoch}_b{batch_size}_lr{learning_rate:g}".replace(".", "p")
    output_dir = args.output_root / run_name
    output_dir.mkdir(parents=True, exist_ok=True)
    command = [
        sys.executable,
        "scripts/train_tourism_context_transformer.py",
        "--epochs",
        str(epoch),
        "--batch-size",
        str(batch_size),
        "--learning-rate",
        str(learning_rate),
        "--model-name",
        args.model_name,
        "--baseline-metrics",
        str(args.baseline_metrics),
        "--output-dir",
        str(output_dir),
    ]
    started = time.perf_counter()
    process = subprocess.run(
        command,
        cwd=PROJECT_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    elapsed_ms = (time.perf_counter() - started) * 1000
    metrics_path = output_dir / "metrics.json"
    metrics: dict[str, Any] = {}
    if metrics_path.exists():
        metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
    result = {
        "run_name": run_name,
        "epochs": epoch,
        "batch_size": batch_size,
        "learning_rate": learning_rate,
        "returncode": process.returncode,
        "elapsed_ms": round(elapsed_ms, 4),
        "output_dir": str(output_dir.relative_to(PROJECT_ROOT)),
        "stdout_tail": process.stdout.splitlines()[-20:],
    }
    if metrics:
        validation = dict(metrics.get("validation") or {})
        test = dict(metrics.get("test") or {})
        hybrid_test = dict(metrics.get("hybrid_test") or {})
        baseline = dict(metrics.get("baseline") or {})
        result.update(
            {
                "baseline_exact": baseline.get("exact_match"),
                "baseline_micro_f1": baseline.get("micro_f1"),
                "validation_exact": validation.get("exact_match"),
                "validation_micro_f1": validation.get("micro_f1"),
                "test_exact": test.get("exact_match"),
                "test_micro_f1": test.get("micro_f1"),
                "hybrid_test_exact": hybrid_test.get("exact_match"),
                "hybrid_test_micro_f1": hybrid_test.get("micro_f1"),
                "hybrid_test_latency_mean_ms": dict(hybrid_test.get("latency") or {}).get("mean_ms"),
                "overfit_warning": (
                    float(validation.get("micro_f1") or 0.0) - float(test.get("micro_f1") or 0.0)
                )
                >= 0.05,
                "adoption_gain_micro_f1": round(
                    float(hybrid_test.get("micro_f1") or 0.0) - float(baseline.get("micro_f1") or 0.0),
                    4,
                ),
                "adoption_gain_exact": round(
                    float(hybrid_test.get("exact_match") or 0.0) - float(baseline.get("exact_match") or 0.0),
                    4,
                ),
            }
        )
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a small transformer hyperparameter grid for tourism context classification.")
    parser.add_argument("--model-name", default="klue/roberta-small")
    parser.add_argument("--epochs", default="3,5")
    parser.add_argument("--batch-sizes", default="16,32")
    parser.add_argument("--learning-rates", default="1e-5,2e-5")
    parser.add_argument("--max-runs", type=int, default=0, help="0 means run the full grid.")
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--summary", type=Path, default=DEFAULT_SUMMARY)
    parser.add_argument("--baseline-metrics", type=Path, default=DEFAULT_BASELINE_METRICS)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    epochs = parse_csv_int(args.epochs)
    batch_sizes = parse_csv_int(args.batch_sizes)
    learning_rates = parse_csv_float(args.learning_rates)
    combos = list(product(epochs, batch_sizes, learning_rates))
    if args.max_runs > 0:
        combos = combos[: args.max_runs]
    results = []
    for epoch, batch_size, learning_rate in combos:
        result = run_one(args, epoch=epoch, batch_size=batch_size, learning_rate=learning_rate)
        results.append(result)
        print(json.dumps(result, ensure_ascii=False, sort_keys=True), flush=True)

    successful = [result for result in results if result.get("returncode") == 0 and "hybrid_test_micro_f1" in result]
    best = None
    if successful:
        best = max(
            successful,
            key=lambda item: (
                float(item.get("hybrid_test_micro_f1") or 0.0),
                float(item.get("hybrid_test_exact") or 0.0),
                -float(item.get("hybrid_test_latency_mean_ms") or 9999.0),
            ),
        )
    summary = {
        "model_name": args.model_name,
        "runs": results,
        "best_run": best,
        "selection_policy": "Choose only if hybrid_test_micro_f1 >= baseline + 0.02, exact improves, and overfit_warning is false.",
    }
    args.summary.parent.mkdir(parents=True, exist_ok=True)
    args.summary.write_text(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps({"summary": str(args.summary.relative_to(PROJECT_ROOT)), "best_run": best}, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
