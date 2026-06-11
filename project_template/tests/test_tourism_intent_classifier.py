import json

from app.services.tourism_intent_classifier import TourismIntentClassifier, train_intent_model
from scripts.build_tourism_intent_training_set import build_rows
from scripts.generate_tourism_intent_utterances import generate_rows


def test_tourism_intent_classifier_predicts_followup_intents(tmp_path):
    rows = [
        {"text": "더 보기", "intent": "show_more"},
        {"text": "더 보여줘", "intent": "show_more"},
        {"text": "출처 알려줘", "intent": "ask_source"},
        {"text": "근거도 보여줘", "intent": "ask_source"},
        {"text": "서울에서 휠체어 관광지 추천", "intent": "recommend_places"},
        {"text": "부산에서 유모차 관광지 추천", "intent": "recommend_places"},
    ]
    model_path = tmp_path / "intent.json"
    model_path.write_text(json.dumps(train_intent_model(rows), ensure_ascii=False), encoding="utf-8")
    classifier = TourismIntentClassifier(model_path)

    assert classifier.predict("더 많이 보여줘").intent == "show_more"
    assert classifier.predict("출처도 같이 알려줘").intent == "ask_source"
    assert classifier.predict("서울 관광지 추천").intent == "recommend_places"


def test_tourism_intent_classifier_rule_overrides_common_short_intents():
    classifier = TourismIntentClassifier.__new__(TourismIntentClassifier)
    classifier.model_path = None
    classifier.model = None

    assert classifier.predict("서울 말고 부산으로").intent == "change_region"
    assert classifier.predict("동구에서 휠체어 가능한 곳").intent == "clarify_region"
    assert classifier.predict("제주시 휠체어 가능한 관광지").intent == "recommend_places"
    assert classifier.predict("지금 영업 중인 곳만").intent == "unsupported_request"
    assert classifier.predict("예약 가능한 객실 가격 알려줘").intent == "unsupported_request"
    assert classifier.predict("여기서 버스로 갈 수 있나요").intent == "unsupported_request"
    assert classifier.predict("아까 유모차 검색했는데, 휠체어로 바꿔주세요").intent == "replace_condition"
    assert classifier.predict("중구 여행 정보 찾아줘").intent == "clarify_region"
    assert classifier.predict("부산 중구 쪽으로만 찾아줄래요").intent == "narrow_region"
    assert classifier.predict("지역을 다시 선택할게요").intent == "change_region"
    assert classifier.predict("서울 여행 정보 알려줘").intent == "recommend_places"
    assert classifier.predict("방금 후보에 수유실까지 봐줘").intent == "add_condition"
    assert classifier.predict("방금 카드 자료 기준 확인하고 싶어").intent == "ask_source"
    assert classifier.predict("현재 카드 다음 5곳도 추가 후보 보여줘").intent == "show_more"
    assert classifier.predict("지금 가지고 있는 것 말고 새로 조회해줘").intent == "live_topup"
    assert classifier.predict("버스 소요시간 확인되는 곳만 보여줘").intent == "unsupported_request"
    assert classifier.predict("오늘 환율 알려줘").intent == "unsupported_request"
    assert classifier.predict("아까 지역 중 부산 중구 위주로").intent == "narrow_region"
    assert classifier.predict("고성군 휠체어 가능한 관광지").intent == "clarify_region"
    assert classifier.predict("광주 남구 휠체어 가능한 관광지").intent == "recommend_places"
    assert classifier.predict("경남 고성군 여행 정보").intent == "recommend_places"
    assert classifier.predict("중구만 말하면 어디 지역인지 애매하지 않아").intent == "clarify_region"
    assert classifier.predict("강서구는 서울인지 부산인지").intent == "clarify_region"
    assert classifier.predict("중구라면 어디 중구 말하는 거야").intent == "clarify_region"
    assert classifier.predict("중구 중에서도 서울 중구만").intent == "narrow_region"


def test_build_tourism_intent_training_set_includes_turns_and_seed_rows(tmp_path):
    eval_path = tmp_path / "eval.jsonl"
    seed_path = tmp_path / "seed.jsonl"
    eval_path.write_text(
        json.dumps(
            {
                "id": "TCV001",
                "turns": [
                    {"message": "서울에서 휠체어 관광지 추천"},
                    {"message": "더 보기"},
                ],
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    seed_path.write_text(
        json.dumps({"text": "출처 알려줘", "intent": "ask_source"}, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    rows = build_rows([eval_path, seed_path])

    assert {"text": "서울에서 휠체어 관광지 추천", "intent": "recommend_places", "source": "eval.jsonl", "item_id": "TCV001"} in rows
    assert {"text": "더 보기", "intent": "show_more", "source": "eval.jsonl", "item_id": "TCV001"} in rows
    assert {"text": "출처 알려줘", "intent": "ask_source", "source": "seed.jsonl", "item_id": ""} in rows


def test_generate_tourism_intent_utterances_has_all_labels():
    rows = generate_rows(rows_per_intent=30)
    counts = {}
    for row in rows:
        counts[row["intent"]] = counts.get(row["intent"], 0) + 1

    assert set(counts) == {
        "add_condition",
        "ask_source",
        "change_region",
        "clarify_region",
        "exclude_preference",
        "live_topup",
        "narrow_region",
        "recommend_places",
        "replace_condition",
        "show_more",
        "unsupported_request",
    }
    assert all(count >= 30 for count in counts.values())
