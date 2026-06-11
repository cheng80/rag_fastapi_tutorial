import json

from app.services.tourism_context_classifier import TourismContextClassifier, train_context_model
from scripts.generate_tourism_context_interpretation_data import generate_hard_holdout_rows, generate_rows, split_train_holdout


def test_tourism_context_classifier_rule_labels_strict_or_and_soft():
    assert "strict_and" in TourismContextClassifier.rule_labels("휠체어랑 유모차 둘 다 되는 곳만")
    assert "or_condition" in TourismContextClassifier.rule_labels("수어 안내나 자막 안내 중 하나라도 있는 곳")
    assert "strict_and" not in TourismContextClassifier.rule_labels("수어 안내나 자막 안내 중 하나라도 있는 곳")
    assert "soft_and" in TourismContextClassifier.rule_labels("유모차 위주면 좋고 산책도 참고만 해줘")


def test_tourism_context_classifier_rule_labels_followup_context():
    assert "replace_condition" in TourismContextClassifier.rule_labels("시장 말고 공원 위주로 바꿔줘")
    assert "exclude_condition" in TourismContextClassifier.rule_labels("카페는 제외하고 보여줘")
    assert "add_condition" in TourismContextClassifier.rule_labels("장애인 주차도 되는 곳")
    assert "family_context" in TourismContextClassifier.rule_labels("아이랑 가기 좋은 곳")
    assert "mobility_context" in TourismContextClassifier.rule_labels("어르신이 걷기 편한 곳")
    assert "specific_facility_required" in TourismContextClassifier.rule_labels("기저귀 교환대 있는 곳")


def test_tourism_context_classifier_rule_labels_hard_boundaries():
    assert "or_condition" in TourismContextClassifier.rule_labels("점자블록이 없으면 오디오가이드라도 있으면 돼")
    assert "strict_and" in TourismContextClassifier.rule_labels("점자블록만 있고 안내견이 없으면 안 돼")
    assert "add_condition" not in TourismContextClassifier.rule_labels("수유실 여부를 추측하지 말고 있는 곳")
    assert "exclude_condition" not in TourismContextClassifier.rule_labels("수유실 여부를 추측하지 말고 있는 곳")
    assert "add_condition" not in TourismContextClassifier.rule_labels("아까 추천에서 아이 때문에 수유나 기저귀도 확인되면 좋아")
    assert "add_condition" in TourismContextClassifier.rule_labels("아까 추천에서 그중 수유실까지 확인되는 곳만 찾아줘")


def test_tourism_context_classifier_predicts_normalized_noisy_input():
    classifier = TourismContextClassifier()

    prediction = classifier.predict("수어안내나자막자료중하나만있음됨")

    assert "or_condition" in prediction.labels
    assert "specific_facility_required" in prediction.labels
    assert any(source.endswith(":normalized") or source == "model" for source in prediction.source_by_label.values())


def test_tourism_context_classifier_training_predicts_multilabel(tmp_path):
    rows = [
        {"text": "휠체어랑 유모차 둘 다 되는 곳만", "labels": ["strict_and", "specific_facility_required"]},
        {"text": "점자블록 또는 오디오가이드 있는 곳", "labels": ["or_condition", "specific_facility_required"]},
        {"text": "시장 말고 공원 위주로", "labels": ["replace_condition"]},
        {"text": "아이랑 가기 좋은 곳", "labels": ["family_context"]},
        {"text": "계단 적고 이동 편한 곳", "labels": ["mobility_context"]},
    ]
    model_path = tmp_path / "context.json"
    model_path.write_text(json.dumps(train_context_model(rows), ensure_ascii=False), encoding="utf-8")
    classifier = TourismContextClassifier(model_path, threshold=0.5)

    prediction = classifier.predict("점자블록이나 오디오가이드 확인되는 곳")

    assert "or_condition" in prediction.labels
    assert "specific_facility_required" in prediction.labels


def test_generate_tourism_context_interpretation_data_has_holdout_scale():
    rows = generate_rows(per_category=100)
    train, holdout = split_train_holdout(rows)
    hard_holdout = generate_hard_holdout_rows(per_category=80)
    labels = {label for row in rows for label in row["labels"]}

    assert len(holdout) >= 500
    assert len(hard_holdout) >= 500
    assert {
        "strict_and",
        "soft_and",
        "or_condition",
        "add_condition",
        "replace_condition",
        "exclude_condition",
        "family_context",
        "mobility_context",
        "specific_facility_required",
    } <= labels
    assert all("required_terms" in row and "optional_terms" in row and "excluded_terms" in row for row in rows)
