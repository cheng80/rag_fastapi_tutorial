import json

import pytest

from scripts import eval_tourism_chat
from scripts.eval_tourism_chat import (
    classify_eval_failure_details,
    classify_eval_failures,
    load_eval_items,
    normalize_term_groups,
    run_eval,
    write_jsonl,
)


def test_load_eval_items_requires_id_and_message(tmp_path):
    eval_file = tmp_path / "eval.jsonl"
    eval_file.write_text(json.dumps({"id": "TQ001"}, ensure_ascii=False), encoding="utf-8")

    with pytest.raises(ValueError):
        load_eval_items(eval_file)


def test_write_jsonl_keeps_korean_text(tmp_path):
    output = tmp_path / "nested" / "result.jsonl"
    write_jsonl(output, [{"id": "TQ001", "message": "서울 휠체어 관광지 추천"}])

    saved = output.read_text(encoding="utf-8")
    assert "서울 휠체어 관광지 추천" in saved


def test_normalize_term_groups_treats_list_of_strings_as_one_any_group():
    assert normalize_term_groups(["수유실", "기저귀"]) == [["수유실", "기저귀", "유아용 의자"]]
    assert normalize_term_groups([["수유실", "기저귀"], ["휠체어"]]) == [["수유실", "기저귀", "유아용 의자"], ["휠체어"]]


def test_run_eval_direct_uses_in_process_client(monkeypatch, tmp_path):
    eval_file = tmp_path / "eval.jsonl"
    output = tmp_path / "result.jsonl"
    eval_file.write_text(
        json.dumps(
            {
                "id": "TQ001",
                "message": "서울 휠체어 관광지 추천",
                "category": "smoke",
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    def fake_post_tourism_chat_direct(message: str, session_id: str):
        assert message == "서울 휠체어 관광지 추천"
        assert session_id == "eval-TQ001"
        return 200, {"answer": "ok", "cards": [{"title": "sample"}], "lookup_mode": "sample"}

    monkeypatch.setattr(eval_tourism_chat, "post_tourism_chat_direct", fake_post_tourism_chat_direct)

    rows = run_eval(eval_file, "http://unused.test", output, timeout=1.0, direct=True)

    assert rows[0]["status_code"] == 200
    assert rows[0]["card_count"] == 1
    assert rows[0]["lookup_mode"] == "sample"
    assert rows[0]["passed"] is True
    assert "서울 휠체어 관광지 추천" in output.read_text(encoding="utf-8")


def test_classify_eval_failures_detects_wrong_region_and_missing_terms():
    item = {
        "must_not_include_regions": ["울산광역시 중구"],
        "must_contain_answer_terms": ["출처"],
        "min_cards": 1,
    }
    response = {
        "answer": "부산 중구 기준 추천입니다.",
        "cards": [{"title": "울산중구어린이역사과학체험관", "address": "울산광역시 중구"}],
    }

    failures = classify_eval_failures(item, 200, response, None)

    assert "wrong_region_card" in failures
    assert "answer_missing_term" in failures


def test_classify_eval_failures_checks_card_terms_and_first_card():
    item = {
        "must_include_any_card_terms": [["점자블록", "오디오가이드"]],
        "first_card_must_include_any_terms": ["박물관", "전시관"],
        "must_not_include_card_terms": [["호텔", "숙박"]],
        "must_include_answer_any_terms": ["확인했습니다", "추천합니다"],
        "min_suggestions": 1,
    }
    response = {
        "answer": "조건에 맞는 곳을 추천합니다.",
        "cards": [
            {"title": "서울 전시관", "raw_fields": {"시각장애 편의": "점자블록 있음"}},
            {"title": "서울 호텔", "raw_fields": {"숙박": "객실 있음"}},
        ],
        "suggested_messages": [],
    }

    failures = classify_eval_failures(item, 200, response, None)

    assert "card_contains_forbidden_terms" in failures
    assert "suggestion_count_low" in failures
    assert "card_missing_required_terms" not in failures
    assert "first_card_missing_required_terms" not in failures
    assert "answer_missing_any_term" not in failures


def test_classify_eval_failures_checks_forbidden_answer_and_suggestions():
    item = {
        "must_not_contain_answer_terms": ["유모차"],
        "must_not_include_suggestion_terms": ["서울"],
    }
    response = {
        "answer": "휠체어 기준으로 추천하지만 유모차 조건은 제외했습니다.",
        "cards": [],
        "suggested_messages": ["서울에서 더 보기"],
    }

    failures = classify_eval_failures(item, 200, response, None)

    assert "answer_contains_forbidden_term" in failures
    assert "suggestion_contains_forbidden_term" in failures


def test_classify_eval_failure_details_separates_no_card_and_evidence_mismatch():
    item = {"min_cards": 1, "must_include_any_card_terms": [["수어", "수화"]]}

    no_card = classify_eval_failure_details(item, {"cards": []})
    mismatch = classify_eval_failure_details(item, {"cards": [{"title": "나폴레옹갤러리", "raw_fields": {"자막/영상안내": "자막 제공"}}]})

    assert no_card["classes"] == ["no_card_output", "strict_evidence_unverifiable_no_card"]
    assert mismatch["classes"] == ["strict_evidence_mismatch"]
    assert mismatch["card_output_state"] == "has_cards"


def test_run_eval_records_failure_reasons(monkeypatch, tmp_path):
    eval_file = tmp_path / "eval.jsonl"
    output = tmp_path / "result.jsonl"
    eval_file.write_text(
        json.dumps(
            {
                "id": "TQ001",
                "message": "서울 휠체어 관광지 추천",
                "min_cards": 2,
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    def fake_post_tourism_chat_direct(message: str, session_id: str):
        return 200, {"answer": "ok", "cards": [{"title": "sample"}], "lookup_mode": "sample"}

    monkeypatch.setattr(eval_tourism_chat, "post_tourism_chat_direct", fake_post_tourism_chat_direct)

    rows = run_eval(eval_file, "http://unused.test", output, timeout=1.0, direct=True)

    assert rows[0]["passed"] is False
    assert rows[0]["failure_reasons"] == ["card_count_low"]
    assert rows[0]["failure_classes"] == ["low_card_count"]


def test_run_eval_supports_conversation_turns(monkeypatch, tmp_path):
    eval_file = tmp_path / "eval.jsonl"
    output = tmp_path / "result.jsonl"
    eval_file.write_text(
        json.dumps(
            {
                "id": "TCV001",
                "category": "conversation",
                "turns": [
                    {"message": "서울에서 휠체어 관광지 추천", "min_cards": 1},
                    {"message": "더 보기", "min_cards": 2},
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    calls = []

    def fake_post_tourism_chat_direct(message: str, session_id: str):
        calls.append((message, session_id))
        cards = [{"title": "sample"}] if message != "더 보기" else [{"title": "sample"}, {"title": "sample2"}]
        return 200, {"answer": "ok", "cards": cards, "lookup_mode": "sample"}

    monkeypatch.setattr(eval_tourism_chat, "post_tourism_chat_direct", fake_post_tourism_chat_direct)

    rows = run_eval(eval_file, "http://unused.test", output, timeout=1.0, direct=True)

    assert rows[0]["passed"] is True
    assert [call[0] for call in calls] == ["서울에서 휠체어 관광지 추천", "더 보기"]
    assert calls[0][1] == calls[1][1] == "eval-TCV001"
    assert len(rows[0]["turn_results"]) == 2
