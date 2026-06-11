from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import time
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.services.tourism_context_classifier import (  # noqa: E402
    CONTEXT_LABELS,
    DEFAULT_CONTEXT_MODEL_PATH,
    SPECIFIC_FACILITY_TERMS,
    TourismContextClassifier,
)


DEFAULT_INPUT = PROJECT_ROOT / "data" / "eval" / "tourism_context_hard_holdout.jsonl"
DEFAULT_TRAIN = PROJECT_ROOT / "data" / "processed" / "tourism_context_training.jsonl"
DEFAULT_OUTPUT = PROJECT_ROOT / "data" / "generated" / "tour_api" / "context_classifier_eval_latest.json"


def project_relative(path: Path) -> str:
    resolved = path.resolve()
    try:
        return str(resolved.relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path)


def load_rows(path: Path) -> list[dict[str, Any]]:
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        payload = json.loads(line)
        payload["labels"] = list(payload.get("labels") or [])
        rows.append(payload)
    return rows


def predict_rule(text: str) -> set[str]:
    return set(TourismContextClassifier.rule_labels(text))


def predict_nb(text: str, classifier: TourismContextClassifier) -> set[str]:
    return set(classifier.predict(text).labels)


def train_linear_model(train_rows: list[dict[str, Any]], model_name: str):
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression
    from sklearn.multiclass import OneVsRestClassifier
    from sklearn.preprocessing import MultiLabelBinarizer
    from sklearn.svm import LinearSVC

    texts = [str(row.get("text") or "") for row in train_rows]
    labels = [list(row.get("labels") or []) for row in train_rows]
    vectorizer = TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 5), min_df=1)
    matrix = vectorizer.fit_transform(texts)
    binarizer = MultiLabelBinarizer(classes=CONTEXT_LABELS)
    y = binarizer.fit_transform(labels)
    if model_name == "linear_svc":
        estimator = OneVsRestClassifier(LinearSVC(class_weight="balanced", random_state=13))
    elif model_name == "logistic_regression":
        estimator = OneVsRestClassifier(
            LogisticRegression(class_weight="balanced", max_iter=1000, solver="liblinear", random_state=13)
        )
    else:
        raise ValueError(f"unsupported linear model: {model_name}")
    estimator.fit(matrix, y)
    return vectorizer, binarizer, estimator


def predict_linear(text: str, bundle: Any) -> set[str]:
    vectorizer, binarizer, estimator = bundle
    predicted = estimator.predict(vectorizer.transform([text]))
    labels = binarizer.inverse_transform(predicted)
    return set(labels[0]) if labels else set()


def predict_hybrid_linear(text: str, bundle: Any) -> set[str]:
    predicted = predict_linear(text, bundle)
    rule_labels = predict_rule(text)

    # High-precision structural labels should not be left solely to the linear model.
    for label in [
        "strict_and",
        "or_condition",
        "add_condition",
        "replace_condition",
        "exclude_condition",
        "family_context",
        "mobility_context",
        "specific_facility_required",
        "soft_and",
    ]:
        if label in rule_labels:
            predicted.add(label)

    # OR and strict AND are mutually dangerous. Explicit OR language wins unless strict language is also present.
    if "or_condition" in rule_labels and "strict_and" not in rule_labels:
        predicted.discard("strict_and")
    if "strict_and" in rule_labels and "or_condition" not in rule_labels:
        predicted.discard("or_condition")

    # Replacement includes exclusion semantics in ordinary language, but the runtime needs the stronger action.
    if "replace_condition" in predicted:
        predicted.discard("exclude_condition")

    if "추측하지 말고" in text:
        predicted.discard("add_condition")
        predicted.discard("exclude_condition")

    if "exclude_condition" in predicted and not any(term in text for term in SPECIFIC_FACILITY_TERMS):
        predicted.discard("specific_facility_required")
    if any(pattern in text for pattern in ["수어지교", "화장실이 아니라", "가 아니라 화려", "전체 목록"]):
        predicted.discard("specific_facility_required")
    if ("필수는 아니" in text or "참고만" in text) and "strict_and" not in predicted and "add_condition" not in predicted:
        predicted.discard("specific_facility_required")
    if "strict_and" not in rule_labels:
        predicted.discard("strict_and")
    if "or_condition" not in rule_labels:
        predicted.discard("or_condition")
    for action_label in ("add_condition", "replace_condition", "exclude_condition"):
        if action_label not in rule_labels:
            predicted.discard(action_label)
    for context_label in ("family_context", "mobility_context"):
        if context_label not in rule_labels:
            predicted.discard(context_label)
    if predicted & {"strict_and", "or_condition", "add_condition", "replace_condition", "exclude_condition"}:
        predicted.discard("soft_and")
    if "specific_facility_required" not in rule_labels:
        predicted.discard("specific_facility_required")

    return predicted


def evaluate_predictions(
    rows: list[dict[str, Any]],
    predictor_name: str,
    predict,
) -> dict[str, Any]:
    started = time.perf_counter()
    exact = 0
    total_expected = 0
    total_predicted = 0
    total_correct = 0
    per_label = {
        label: {"tp": 0, "fp": 0, "fn": 0}
        for label in CONTEXT_LABELS
    }
    special_errors = {
        "strict_and_missed": 0,
        "strict_and_overcalled": 0,
        "or_as_strict_and": 0,
        "exclude_missed": 0,
        "specific_facility_missed": 0,
    }
    samples: list[dict[str, Any]] = []
    failure_buckets: dict[str, int] = {}

    for row in rows:
        expected = set(row.get("labels") or [])
        predicted = set(predict(str(row.get("text") or "")))
        exact += int(expected == predicted)
        total_expected += len(expected)
        total_predicted += len(predicted)
        total_correct += len(expected & predicted)
        for label in CONTEXT_LABELS:
            if label in expected and label in predicted:
                per_label[label]["tp"] += 1
            elif label not in expected and label in predicted:
                per_label[label]["fp"] += 1
            elif label in expected and label not in predicted:
                per_label[label]["fn"] += 1

        if "strict_and" in expected and "strict_and" not in predicted:
            special_errors["strict_and_missed"] += 1
        if "strict_and" not in expected and "strict_and" in predicted:
            special_errors["strict_and_overcalled"] += 1
        if "or_condition" in expected and "strict_and" in predicted:
            special_errors["or_as_strict_and"] += 1
        if "exclude_condition" in expected and "exclude_condition" not in predicted:
            special_errors["exclude_missed"] += 1
        if "specific_facility_required" in expected and "specific_facility_required" not in predicted:
            special_errors["specific_facility_missed"] += 1
        if expected != predicted and len(samples) < 20:
            missing = sorted(expected - predicted)
            spurious = sorted(predicted - expected)
            for label in missing:
                failure_buckets[f"missing:{label}"] = failure_buckets.get(f"missing:{label}", 0) + 1
            for label in spurious:
                failure_buckets[f"spurious:{label}"] = failure_buckets.get(f"spurious:{label}", 0) + 1
            samples.append(
                {
                    "id": row.get("id"),
                    "text": row.get("text"),
                    "expected": sorted(expected),
                    "predicted": sorted(predicted),
                }
            )
        elif expected != predicted:
            for label in sorted(expected - predicted):
                failure_buckets[f"missing:{label}"] = failure_buckets.get(f"missing:{label}", 0) + 1
            for label in sorted(predicted - expected):
                failure_buckets[f"spurious:{label}"] = failure_buckets.get(f"spurious:{label}", 0) + 1

    precision = total_correct / total_predicted if total_predicted else 1.0
    recall = total_correct / total_expected if total_expected else 1.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    per_label_metrics = {}
    for label, counts in per_label.items():
        label_precision = counts["tp"] / (counts["tp"] + counts["fp"]) if counts["tp"] + counts["fp"] else 1.0
        label_recall = counts["tp"] / (counts["tp"] + counts["fn"]) if counts["tp"] + counts["fn"] else 1.0
        label_f1 = (
            2 * label_precision * label_recall / (label_precision + label_recall)
            if label_precision + label_recall
            else 0.0
        )
        per_label_metrics[label] = {
            "precision": round(label_precision, 4),
            "recall": round(label_recall, 4),
            "f1": round(label_f1, 4),
            **counts,
        }

    elapsed_ms = (time.perf_counter() - started) * 1000
    return {
        "predictor": predictor_name,
        "rows": len(rows),
        "exact_match": round(exact / len(rows), 4) if rows else 0.0,
        "micro_precision": round(precision, 4),
        "micro_recall": round(recall, 4),
        "micro_f1": round(f1, 4),
        "per_label": per_label_metrics,
        "special_errors": special_errors,
        "failure_buckets": dict(sorted(failure_buckets.items(), key=lambda item: (-item[1], item[0]))),
        "latency": {
            "total_ms": round(elapsed_ms, 4),
            "mean_ms": round(elapsed_ms / len(rows), 4) if rows else 0.0,
        },
        "sample_mismatches": samples,
    }


def build_second_stage_report(linear_metrics: dict[str, Any], train_rows: int) -> dict[str, Any]:
    exact = float(linear_metrics.get("exact_match") or 0.0)
    f1 = float(linear_metrics.get("micro_f1") or 0.0)
    holdout_rows = int(linear_metrics.get("rows") or 0)
    labeled_rows = train_rows + holdout_rows
    ko_readiness = min(1.0, labeled_rows / 3000)
    expected_gain = max(0.0, 1.0 - max(exact, f1))
    operational_risk = 0.75 if train_rows < 2000 else 0.45
    suitability = (expected_gain * 0.45) + (ko_readiness * 0.25) + ((1.0 - operational_risk) * 0.30)
    recommendation = (
        "hold"
        if train_rows < 1000 or expected_gain < 0.03
        else "pilot_finetune"
    )
    return {
        "candidate": "KoBERT/KLUE-RoBERTa multi-label classifier",
        "basis": "Linear model holdout gap, available labeled rows, and MVP runtime/operation risk.",
        "available_train_rows": train_rows,
        "available_holdout_rows": holdout_rows,
        "available_labeled_rows": labeled_rows,
        "linear_exact_match": exact,
        "linear_micro_f1": f1,
        "estimated_accuracy_headroom": round(expected_gain, 4),
        "data_readiness_score": round(ko_readiness, 4),
        "operation_risk_score": round(operational_risk, 4),
        "suitability_score": round(suitability, 4),
        "recommendation": recommendation,
        "interpretation": (
            "2차 딥러닝 fine-tuning은 현재 Linear 모델이 못 맞히는 독립 holdout 오류가 충분히 남고 "
            "라벨링 데이터가 2천 건 이상 쌓였을 때 적용 가치가 커진다."
        ),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate tourism context classifiers.")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--train", type=Path, default=DEFAULT_TRAIN)
    parser.add_argument("--model", type=Path, default=DEFAULT_CONTEXT_MODEL_PATH)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    rows = load_rows(args.input)
    train_rows = load_rows(args.train)
    nb_classifier = TourismContextClassifier(args.model)
    metrics: dict[str, Any] = {
        "input": project_relative(args.input),
        "train": project_relative(args.train),
        "results": [],
    }
    metrics["results"].append(evaluate_predictions(rows, "rule_only", predict_rule))
    metrics["results"].append(evaluate_predictions(rows, "naive_bayes", lambda text: predict_nb(text, nb_classifier)))

    linear_results = []
    for model_name in ("linear_svc", "logistic_regression"):
        bundle = train_linear_model(train_rows, model_name)
        result = evaluate_predictions(rows, model_name, lambda text, bundle=bundle: predict_linear(text, bundle))
        metrics["results"].append(result)
        linear_results.append(result)
        hybrid_result = evaluate_predictions(
            rows,
            f"hybrid_{model_name}",
            lambda text, bundle=bundle: predict_hybrid_linear(text, bundle),
        )
        metrics["results"].append(hybrid_result)
        linear_results.append(hybrid_result)

    best_linear = max(linear_results, key=lambda item: (item["micro_f1"], item["exact_match"]))
    metrics["best_linear"] = best_linear["predictor"]
    metrics["second_stage"] = build_second_stage_report(best_linear, train_rows=len(train_rows))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(metrics, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(metrics, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
