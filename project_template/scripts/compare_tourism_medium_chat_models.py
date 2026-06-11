from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
DEFAULT_INPUT = PROJECT_ROOT / "data" / "eval" / "tourism_context_medium_chat_eval_v4_120.jsonl"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "data" / "generated" / "tour_api" / "medium_chat_model_compare_20260518"
DEFAULT_CHAT_MODEL = "hf.co/unsloth/gemma-4-E4B-it-qat-GGUF:UD-Q4_K_XL"
GEMMA3_FAST_MODEL = "gemma3:4b-it-q4_K_M"
GEMMA4_MODEL = "gemma4:e4b"


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")


def write_markdown(path: Path, report: dict[str, Any]) -> None:
    lines = [
        "# Medium Chat Model Comparison",
        "",
        f"- input: `{Path(report['input']).name}`",
        f"- rows: {report['rows']}",
        "",
        "## Chat Card Quality",
        "",
        "| variant | passed | failed | pass_rate | mean_ms | output |",
        "|---|---:|---:|---:|---:|---|",
    ]
    for name, summary in report["chat_eval"].items():
        lines.append(
            f"| {name} | {summary['passed']} | {summary['failed']} | {summary['pass_rate']:.4f} | "
            f"{summary['mean_duration_ms']:.1f} | `{Path(summary['output']).name}` |"
        )
    lines.extend(
        [
            "",
            "## Condition Label Extraction",
            "",
            "| variant | rows | exact | micro_f1 | false_pos | false_neg |",
            "|---|---:|---:|---:|---:|---:|",
        ]
    )
    for name, summary in report["condition_eval"].items():
        lines.append(
            f"| {name} | {summary['rows']} | {summary['exact_match']:.4f} | {summary['micro_f1']:.4f} | "
            f"{summary['false_positive']} | {summary['false_negative']} |"
        )
    lines.extend(["", "## Failure Buckets", ""])
    for name, summary in report["chat_eval"].items():
        lines.append(f"### {name}")
        if not summary["failure_summary"]:
            lines.append("- no failures")
        else:
            for reason, count in sorted(summary["failure_summary"].items(), key=lambda item: (-item[1], item[0])):
                lines.append(f"- {reason}: {count}")
        lines.append("")
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def summarize_chat_output(path: Path) -> dict[str, Any]:
    rows = load_jsonl(path)
    failures: dict[str, int] = {}
    durations = []
    for row in rows:
        durations.append(float(row.get("duration_ms") or 0.0))
        for reason in row.get("failure_reasons") or []:
            failures[str(reason)] = failures.get(str(reason), 0) + 1
    passed = sum(1 for row in rows if row.get("passed"))
    failed = len(rows) - passed
    return {
        "rows": len(rows),
        "passed": passed,
        "failed": failed,
        "pass_rate": passed / len(rows) if rows else 0.0,
        "mean_duration_ms": sum(durations) / len(durations) if durations else 0.0,
        "failure_summary": failures,
        "output": str(path),
    }


def run_chat_eval(input_path: Path, output_dir: Path, variant: str, env_overrides: dict[str, str]) -> dict[str, Any]:
    output_path = output_dir / f"{variant}.jsonl"
    env = {
        **os.environ,
        "TOURISM_LIVE_LOOKUP_ENABLED": "false",
        "TOURISM_QUERY_EVENT_LOG_ENABLED": "false",
        **env_overrides,
    }
    command = [
        sys.executable,
        "scripts/eval_tourism_chat.py",
        "--direct",
        "--input",
        str(input_path),
        "--output",
        str(output_path),
    ]
    started = time.perf_counter()
    completed = subprocess.run(command, cwd=PROJECT_ROOT, env=env, text=True, capture_output=True, check=False)
    summary = summarize_chat_output(output_path) if output_path.exists() else {
        "rows": 0,
        "passed": 0,
        "failed": 0,
        "pass_rate": 0.0,
        "mean_duration_ms": 0.0,
        "failure_summary": {"runner_failed": 1},
        "output": str(output_path),
    }
    summary.update(
        {
            "returncode": completed.returncode,
            "runner_duration_ms": round((time.perf_counter() - started) * 1000, 1),
            "stdout_tail": completed.stdout.splitlines()[-20:],
            "stderr_tail": completed.stderr.splitlines()[-20:],
        }
    )
    if completed.returncode != 0:
        summary["failure_summary"]["runner_failed"] = summary["failure_summary"].get("runner_failed", 0) + 1
    return summary


def iter_condition_cases(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    cases = []
    for row in rows:
        if "turns" in row:
            for index, turn in enumerate(row["turns"], start=1):
                if "expected_conditions" in turn:
                    cases.append({"id": f"{row['id']}:turn{index}", "text": turn["message"], "expected": set(turn["expected_conditions"])})
        elif "expected_conditions" in row:
            cases.append({"id": row["id"], "text": row["message"], "expected": set(row["expected_conditions"])})
    return cases


def condition_metrics(cases: list[dict[str, Any]], predictions: dict[str, set[str]]) -> dict[str, Any]:
    exact = tp = fp = fn = 0
    samples = []
    for case in cases:
        expected = set(case["expected"])
        predicted = set(predictions.get(case["id"], set()))
        exact += int(expected == predicted)
        tp += len(expected & predicted)
        fp += len(predicted - expected)
        fn += len(expected - predicted)
        if expected != predicted and len(samples) < 25:
            samples.append({"id": case["id"], "text": case["text"], "expected": sorted(expected), "predicted": sorted(predicted)})
    precision = tp / (tp + fp) if tp + fp else 1.0
    recall = tp / (tp + fn) if tp + fn else 1.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {
        "rows": len(cases),
        "exact_match": exact / len(cases) if cases else 0.0,
        "micro_precision": precision,
        "micro_recall": recall,
        "micro_f1": f1,
        "false_positive": fp,
        "false_negative": fn,
        "sample_mismatches": samples,
    }


def run_condition_eval(rows: list[dict[str, Any]]) -> dict[str, Any]:
    from app.core.config import Settings
    from app.services.korean_external_corrector import ExternalCorrectionResult
    from app.services.tourism_condition_transformer import TourismConditionTransformer
    from app.services.tourism_query_service import CONDITION_KEYWORDS, TourismQueryService

    quickspacer_available = True

    class QuickSpacerCorrector:
        def __init__(self):
            try:
                from quickspacer import Spacer
            except ModuleNotFoundError:
                nonlocal quickspacer_available
                quickspacer_available = False
                self.spacer = None
                return

            self.spacer = Spacer()

        def correct(self, text: str, protected_terms: list[str]) -> ExternalCorrectionResult:
            if self.spacer is None:
                return ExternalCorrectionResult(
                    raw_text=text,
                    corrected_text=text,
                    accepted=False,
                    provider="quickspacer",
                    model="quickspacer",
                    reason="module_missing",
                    damaged_terms=[],
                )
            spaced = self.spacer.space([text])
            corrected = str(spaced[0]).strip() if isinstance(spaced, list) and spaced else str(text)
            return ExternalCorrectionResult(
                raw_text=text,
                corrected_text=corrected,
                accepted=True,
                provider="quickspacer",
                model="quickspacer",
                reason="candidate",
                damaged_terms=[],
            )

    cases = iter_condition_cases(rows)
    services = {
        "rule_parser": TourismQueryService(enable_external_correction=False),
        "et5_local": TourismQueryService(enable_external_correction=True),
    }
    quickspacer = QuickSpacerCorrector()
    if quickspacer_available:
        services["quickspacer"] = TourismQueryService(external_corrector=quickspacer, enable_external_correction=True)
    results = {}
    for name, service in services.items():
        predictions = {case["id"]: set(service.extract(case["text"]).get("conditions") or []) for case in cases}
        results[name] = condition_metrics(cases, predictions)

    transformer = TourismConditionTransformer(Settings(tourism_condition_transformer_enabled=True), labels=list(CONDITION_KEYWORDS))
    predictions = {}
    for case in cases:
        rule_conditions = set(services["rule_parser"].extract(case["text"]).get("conditions") or [])
        transformer_conditions = set(transformer.predict(case["text"]).get("labels") or [])
        predictions[case["id"]] = rule_conditions | transformer_conditions
    results["roberta_small_candidate"] = condition_metrics(cases, predictions)
    return results


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compare tourism medium chat model candidates.")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--skip-chat", action="store_true")
    parser.add_argument("--skip-condition", action="store_true")
    parser.add_argument(
        "--include-reasoning-assist",
        action="store_true",
        help="Also run slow full-pipeline variants with TOURISM_REASONING_ASSIST_ENABLED=true and Ollama chat models.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    rows = load_jsonl(args.input)
    variant_names = [
        "current_runtime",
        "rule_parser",
        "et5_local",
        "quickspacer",
        "roberta_small_candidate",
        "current_default_reasoning",
        "et5_roberta_default_reasoning",
        "current_gemma3_reasoning",
        "current_gemma4_reasoning",
    ]
    chat_eval = {}
    if not args.skip_chat:
        variants = {
            "current_runtime": {
                "TOURISM_KOREAN_CORRECTION_ENABLED": "true",
                "TOURISM_KOREAN_CORRECTION_PROVIDER": "hf_seq2seq",
                "TOURISM_KOREAN_CORRECTION_RISKY_ONLY": "true",
                "TOURISM_CONDITION_TRANSFORMER_ENABLED": "false",
                "TOURISM_REASONING_ASSIST_ENABLED": "false",
            },
            "rule_parser": {"TOURISM_KOREAN_CORRECTION_ENABLED": "false", "TOURISM_CONDITION_TRANSFORMER_ENABLED": "false"},
            "et5_local": {
                "TOURISM_KOREAN_CORRECTION_ENABLED": "true",
                "TOURISM_KOREAN_CORRECTION_PROVIDER": "hf_seq2seq",
                "TOURISM_KOREAN_CORRECTION_RISKY_ONLY": "true",
                "TOURISM_CONDITION_TRANSFORMER_ENABLED": "false",
            },
            "quickspacer": {
                "TOURISM_KOREAN_CORRECTION_ENABLED": "true",
                "TOURISM_KOREAN_CORRECTION_PROVIDER": "quickspacer",
                "TOURISM_KOREAN_CORRECTION_RISKY_ONLY": "false",
                "TOURISM_CONDITION_TRANSFORMER_ENABLED": "false",
            },
            "roberta_small_candidate": {
                "TOURISM_KOREAN_CORRECTION_ENABLED": "false",
                "TOURISM_CONDITION_TRANSFORMER_ENABLED": "true",
            },
        }
        if args.include_reasoning_assist:
            variants.update(
                {
                    "current_default_reasoning": {
                        "TOURISM_KOREAN_CORRECTION_ENABLED": "true",
                        "TOURISM_KOREAN_CORRECTION_PROVIDER": "hf_seq2seq",
                        "TOURISM_KOREAN_CORRECTION_RISKY_ONLY": "true",
                        "TOURISM_CONDITION_TRANSFORMER_ENABLED": "false",
                        "TOURISM_REASONING_ASSIST_ENABLED": "true",
                        "OLLAMA_CHAT_MODEL": DEFAULT_CHAT_MODEL,
                        "LLM_THINK": "false",
                    },
                    "et5_roberta_default_reasoning": {
                        "TOURISM_KOREAN_CORRECTION_ENABLED": "true",
                        "TOURISM_KOREAN_CORRECTION_PROVIDER": "hf_seq2seq",
                        "TOURISM_KOREAN_CORRECTION_RISKY_ONLY": "true",
                        "TOURISM_CONDITION_TRANSFORMER_ENABLED": "true",
                        "TOURISM_REASONING_ASSIST_ENABLED": "true",
                        "OLLAMA_CHAT_MODEL": DEFAULT_CHAT_MODEL,
                        "LLM_THINK": "false",
                    },
                    "current_gemma3_reasoning": {
                        "TOURISM_KOREAN_CORRECTION_ENABLED": "true",
                        "TOURISM_KOREAN_CORRECTION_PROVIDER": "hf_seq2seq",
                        "TOURISM_KOREAN_CORRECTION_RISKY_ONLY": "true",
                        "TOURISM_CONDITION_TRANSFORMER_ENABLED": "false",
                        "TOURISM_REASONING_ASSIST_ENABLED": "true",
                        "OLLAMA_CHAT_MODEL": GEMMA3_FAST_MODEL,
                        "LLM_THINK": "false",
                    },
                    "current_gemma4_reasoning": {
                        "TOURISM_KOREAN_CORRECTION_ENABLED": "true",
                        "TOURISM_KOREAN_CORRECTION_PROVIDER": "hf_seq2seq",
                        "TOURISM_KOREAN_CORRECTION_RISKY_ONLY": "true",
                        "TOURISM_CONDITION_TRANSFORMER_ENABLED": "false",
                        "TOURISM_REASONING_ASSIST_ENABLED": "true",
                        "OLLAMA_CHAT_MODEL": GEMMA4_MODEL,
                        "LLM_THINK": "false",
                    },
                }
            )
        for name, env in variants.items():
            print(json.dumps({"running_chat_variant": name}, ensure_ascii=False), flush=True)
            chat_eval[name] = run_chat_eval(args.input, args.output_dir, name, env)
    else:
        for name in variant_names:
            output_path = args.output_dir / f"{name}.jsonl"
            if output_path.exists():
                chat_eval[name] = summarize_chat_output(output_path)
    condition_eval = {} if args.skip_condition else run_condition_eval(rows)
    report = {
        "input": str(args.input),
        "rows": len(rows),
        "chat_eval": chat_eval,
        "condition_eval": condition_eval,
        "decision": {
            "runtime_promote": False,
            "reason": "Only promote a candidate if fresh chat-card quality improves without clear over-filtering or over-labeling regressions.",
        },
    }
    write_json(args.output_dir / "summary.json", report)
    write_markdown(args.output_dir / "summary.md", report)
    output_path = args.output_dir / "summary.json"
    try:
        output_display = str(output_path.resolve().relative_to(PROJECT_ROOT))
    except ValueError:
        output_display = str(output_path)
    print(json.dumps({"output": output_display}, ensure_ascii=False))


if __name__ == "__main__":
    main()
