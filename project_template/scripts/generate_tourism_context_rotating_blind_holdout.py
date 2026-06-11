from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.services.tourism_context_classifier import CONTEXT_LABELS  # noqa: E402


DEFAULT_OUTPUT = PROJECT_ROOT / "data" / "eval" / "tourism_context_rotating_blind_holdout_20260517.jsonl"
DEFAULT_OUTPUT_V2 = PROJECT_ROOT / "data" / "eval" / "tourism_context_rotating_blind_holdout_20260517_v2.jsonl"
DEFAULT_OUTPUT_V3 = PROJECT_ROOT / "data" / "eval" / "tourism_context_rotating_blind_holdout_20260517_v3.jsonl"
DEFAULT_OUTPUT_V4 = PROJECT_ROOT / "data" / "eval" / "tourism_context_rotating_blind_holdout_20260517_v4.jsonl"
DEFAULT_OUTPUT_V5 = PROJECT_ROOT / "data" / "eval" / "tourism_context_rotating_blind_holdout_20260517_v5.jsonl"
OVERLAP_INPUTS = [
    PROJECT_ROOT / "data" / "processed" / "context_finetune" / "train.jsonl",
    PROJECT_ROOT / "data" / "eval" / "tourism_context_blind_holdout.jsonl",
    PROJECT_ROOT / "data" / "eval" / "tourism_context_rotating_blind_holdout_20260517.jsonl",
    PROJECT_ROOT / "data" / "eval" / "tourism_context_rotating_blind_holdout_20260517_v2.jsonl",
    PROJECT_ROOT / "data" / "eval" / "tourism_context_rotating_blind_holdout_20260517_v3.jsonl",
    PROJECT_ROOT / "data" / "eval" / "tourism_context_rotating_blind_holdout_20260517_v4.jsonl",
]


def normalize(text: str) -> str:
    return " ".join(text.split()).casefold()


def load_seen_texts(paths: list[Path]) -> set[str]:
    seen: set[str] = set()
    for path in paths:
        if not path.exists():
            continue
        with path.open("r", encoding="utf-8") as file:
            for line in file:
                if not line.strip():
                    continue
                item = json.loads(line)
                seen.add(normalize(str(item.get("text") or "")))
    return seen


def row(text: str, labels: list[str], category: str, variant: str = "v1") -> dict[str, Any]:
    label_set = set(labels)
    return {
        "text": normalize(text),
        "labels": [label for label in CONTEXT_LABELS if label in label_set],
        "category": category,
        "template_family": f"rotating_blind_codex_20260517_{variant}",
        "source": "codex_rotating_blind_holdout",
    }


def build_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    rows.extend(
        [
            row("주차 가능하고 장애인 화장실 표기가 둘 다 있는 곳 아니면 이번엔 빼자", ["strict_and", "specific_facility_required"], "strict_and"),
            row("경사로랑 승강기 둘 중 하나만 확인된 곳은 부족해 둘 다 잡힌 곳으로", ["strict_and", "mobility_context", "specific_facility_required"], "strict_and"),
            row("수어 안내와 자막 안내가 같은 장소에 같이 적힌 카드만 남겨", ["strict_and", "specific_facility_required"], "strict_and"),
            row("아이 데리고 가니까 기저귀 교환대와 유아 의자 둘 다 확인된 식당형 장소만", ["strict_and", "family_context", "specific_facility_required"], "strict_and"),
            row("휠체어 동선과 장애인 주차가 동시에 해결되는 후보만 골라줘", ["strict_and", "mobility_context", "specific_facility_required"], "strict_and"),
            row("촉지도만 있거나 점자블록만 있는 곳 말고 둘이 함께 있는 곳", ["strict_and", "specific_facility_required"], "strict_and"),
            row("보조견 동반하고 실내 이동 편의가 둘 다 맞아야 해", ["strict_and", "mobility_context", "specific_facility_required"], "strict_and"),
            row("오디오가이드와 엘리베이터가 모두 확인되는 박물관 쪽으로만", ["strict_and", "specific_facility_required"], "strict_and"),
            row("수유실이 제일 좋고 없으면 기저귀 갈 곳이라도 있는 데", ["or_condition", "family_context", "specific_facility_required"], "or_condition"),
            row("장애인 주차가 안 보이면 장애인 화장실 근거라도 확실한 후보", ["or_condition", "specific_facility_required"], "or_condition"),
            row("승강기든 완만한 경사로든 바퀴 이동 근거 하나만 있으면 괜찮아", ["or_condition", "mobility_context", "specific_facility_required"], "or_condition"),
            row("수어 안내가 없을 때는 자막 지원이라도 명확하면 후보에 넣어", ["or_condition", "specific_facility_required"], "or_condition"),
            row("점자블록 또는 촉지도 중 하나라도 편의정보에 있으면 보여줘", ["or_condition", "specific_facility_required"], "or_condition"),
            row("유모차로 편하거나 아이 휴식 공간이 있거나 둘 중 하나면 충분해", ["or_condition", "family_context", "mobility_context"], "or_condition"),
            row("안내견 동반이 최선이고 안 되면 시각장애 안내 자료라도", ["or_condition", "specific_facility_required"], "or_condition"),
            row("계단 회피가 어렵다면 실내 좌석 많은 곳이라도 우선 봐줘", ["or_condition", "mobility_context"], "or_condition"),
            row("전시 분위기가 우선이고 자막 지원은 보이면 가점 정도야", ["soft_and"], "soft_and"),
            row("아이랑 쉬기 좋은 게 핵심이고 유아 의자는 있으면 참고", ["soft_and", "family_context"], "soft_and"),
            row("어르신 이동 부담이 적은 곳 먼저 보고 주차는 있으면 좋고", ["soft_and", "mobility_context"], "soft_and"),
            row("시장 구경 위주로 보되 장애인 화장실은 후보 많을 때만 고려해", ["soft_and"], "soft_and"),
            row("산책하기 조용한 곳이면 되고 경사로까지 필수로 묶진 마", ["soft_and"], "soft_and"),
            row("박물관 중심으로 추천하고 오디오가이드는 덤으로만 봐줘", ["soft_and"], "soft_and"),
            row("아기랑 가서 덜 붐비는 게 먼저고 수유실은 없으면 넘어가도 돼", ["soft_and", "family_context"], "soft_and"),
            row("휠체어 이동이 편하면 좋지만 카페형 장소 여부는 참고만", ["soft_and", "mobility_context"], "soft_and"),
            row("방금 결과에서 장애인 주차 확인된 후보로만 좁혀줘", ["add_condition", "specific_facility_required"], "add_condition"),
            row("위 목록은 유지하고 기저귀 교환대 있는지만 추가로 봐줘", ["add_condition", "family_context", "specific_facility_required"], "add_condition"),
            row("이전 추천 안에서 계단 적은 곳만 다시 추려줘", ["add_condition", "mobility_context"], "add_condition"),
            row("아까 카드 중 수어 안내 근거 붙은 곳만 남겨", ["add_condition", "specific_facility_required"], "add_condition"),
            row("그 후보들에 유모차 이동 편한지도 조건으로 얹어줘", ["add_condition", "mobility_context"], "add_condition"),
            row("현재 결과에서 시장 느낌은 그대로 두고 화장실 표기만 더 확인", ["add_condition", "specific_facility_required"], "add_condition"),
            row("전 추천에서 아이 동반 괜찮은 장소만 한 번 더 걸러줘", ["add_condition", "family_context"], "add_condition"),
            row("같은 지역 후보에서 보조견 동반 가능 여부까지 같이 체크해", ["add_condition", "specific_facility_required"], "add_condition"),
            row("수유실 기준은 빼고 이번에는 조용한 전시 기준으로 바꿔줘", ["replace_condition"], "replace_condition"),
            row("시장 말고 실내 박물관 쪽으로 기준을 갈아탈게", ["replace_condition"], "replace_condition"),
            row("아이 편의는 잠깐 내려놓고 어르신 걷기 편한 쪽으로", ["replace_condition", "mobility_context"], "replace_condition"),
            row("자막 안내 대신 수어 안내 확인되는 곳으로 바꿔줘", ["replace_condition", "specific_facility_required"], "replace_condition"),
            row("부산 조건 말고 대구에서 장애인 화장실 있는 곳", ["replace_condition", "specific_facility_required"], "replace_condition"),
            row("휠체어 이동 조건은 유지 말고 유모차 동선 기준으로 다시", ["replace_condition", "mobility_context"], "replace_condition"),
            row("먹거리 위주는 취소하고 자연 산책 위주로 추천해", ["replace_condition"], "replace_condition"),
            row("점자블록 말고 오디오가이드 확인되는 쪽으로 바꿀래", ["replace_condition", "specific_facility_required"], "replace_condition"),
            row("음식점형 장소는 제외하고 관광지 중심으로만", ["exclude_condition"], "exclude_condition"),
            row("붐비는 시장 골목은 빼고 한적한 산책 코스", ["exclude_condition"], "exclude_condition"),
            row("숙박 느낌 나는 후보는 뒤로 보내줘", ["exclude_condition"], "exclude_condition"),
            row("카페는 빼되 실내에서 쉬운 동선이면 좋아", ["exclude_condition", "mobility_context"], "exclude_condition"),
            row("계단 많은 전망대는 패스하고 평지 위주로", ["exclude_condition", "mobility_context"], "exclude_condition"),
            row("아이와 가는 일정이라 술집 분위기는 제외", ["exclude_condition", "family_context"], "exclude_condition"),
            row("야외 오래 걷는 곳은 빼고 실내 관람 위주로", ["exclude_condition", "mobility_context"], "exclude_condition"),
            row("쇼핑몰 성격은 제외하고 지역 문화 볼거리만", ["exclude_condition"], "exclude_condition"),
            row("초등 아이가 지루해하지 않을 체험형 장소", ["family_context"], "family_context"),
            row("아기 낮잠 시간 사이에 짧게 다녀올 만한 곳", ["family_context", "mobility_context"], "family_context"),
            row("부모님과 아이가 같이 가도 부담 적은 코스", ["family_context", "mobility_context"], "family_context"),
            row("유아차 대여 조건 말고 아이가 쉬기 좋은 분위기", ["family_context"], "family_context"),
            row("어린이 눈높이에 맞는 역사 전시가 있을까", ["family_context"], "family_context"),
            row("가족끼리 사진 찍기 좋고 너무 힘들지 않은 곳", ["family_context", "mobility_context"], "family_context"),
            row("기저귀 시설은 없어도 아이가 덜 피곤한 일정", ["soft_and", "family_context", "mobility_context"], "family_context"),
            row("아이와 함께 먹기 편한 주변 동선의 관광지", ["family_context", "mobility_context"], "family_context"),
            row("무릎이 불편해서 오르막이 적은 곳", ["mobility_context"], "mobility_context"),
            row("발목 다친 동행자가 있어서 이동 거리가 짧아야 해", ["mobility_context"], "mobility_context"),
            row("오래 서서 기다리지 않아도 볼 수 있는 곳", ["mobility_context"], "mobility_context"),
            row("전동 스쿠터로 동선이 끊기지 않는 관광지", ["mobility_context"], "mobility_context"),
            row("계단을 최대한 피해서 움직일 수 있으면 좋겠어", ["mobility_context"], "mobility_context"),
            row("어르신이 중간중간 쉬기 쉬운 코스", ["mobility_context"], "mobility_context"),
            row("유모차로 사람 많은 골목을 헤치지 않아도 되는 곳", ["mobility_context"], "mobility_context"),
            row("걷는 시간이 짧고 앉아 쉴 곳이 있는 장소", ["mobility_context"], "mobility_context"),
            row("수어라는 이름 말고 실제 수어 안내 여부가 필요해", ["specific_facility_required"], "specific_facility_required"),
            row("장애인 화장실 표기가 없으면 후보로 세지 마", ["specific_facility_required"], "specific_facility_required"),
            row("점자 느낌 전시가 아니라 점자블록 편의정보를 확인해", ["specific_facility_required"], "specific_facility_required"),
            row("엘베가 있다는 근거가 카드에 있어야 해", ["specific_facility_required"], "specific_facility_required"),
            row("보조견 동반 가능 여부가 명시된 곳만", ["specific_facility_required"], "specific_facility_required"),
            row("수유실 문구는 원문 근거가 있을 때만 인정해", ["specific_facility_required"], "specific_facility_required"),
            row("장애인 주차 가능 여부만 정확히 봐줘", ["specific_facility_required"], "specific_facility_required"),
            row("청각장애 동행자라 자막 지원 확인이 중요해", ["specific_facility_required"], "specific_facility_required"),
            row("수어지교라는 이름의 장소를 찾는 게 아니야", [], "negative_near_miss"),
            row("화장실 이야기가 아니라 바다 풍경이 좋은 곳", [], "negative_near_miss"),
            row("주차 말고 주제가 독특한 전시를 원해", [], "negative_near_miss"),
            row("점자라는 작품명이 있어도 접근성 조건은 아냐", [], "negative_near_miss"),
            row("아이돌 굿즈 시장이지 아이 동반 얘기는 아니야", [], "negative_near_miss"),
            row("엘리베이터 음악 얘기 말고 조용한 관람지", [], "negative_near_miss"),
            row("보조견이라는 전시 제목이면 편의정보로 보지 마", [], "negative_near_miss"),
            row("가족이라는 상호명 말고 실제 관광지를 봐줘", [], "negative_near_miss"),
        ]
    )
    for index, item in enumerate(rows, start=1):
        item["id"] = f"CTXROT20260517{index:04d}"
    return rows


def build_rows_v2() -> list[dict[str, Any]]:
    cases = [
        ("장애인 주차랑 화장실이 한 카드에 같이 확인되는 데만 추려줘", ["strict_and", "specific_facility_required"], "strict_and"),
        ("경사로만 있거나 엘리베이터만 있는 건 말고 두 근거가 같이 있어야 해", ["strict_and", "mobility_context", "specific_facility_required"], "strict_and"),
        ("아이 식사 의자와 기저귀 갈 곳이 둘 다 적힌 곳만 남겨줘", ["strict_and", "family_context", "specific_facility_required"], "strict_and"),
        ("수어랑 자막 중 하나만 있는 곳은 빼고 둘 다 표기된 곳", ["strict_and", "specific_facility_required"], "strict_and"),
        ("보조견 동반과 휠체어 이동이 동시에 무리 없는 후보", ["strict_and", "mobility_context", "specific_facility_required"], "strict_and"),
        ("점자블록에 오디오 안내까지 같이 확인되는 실내 전시만", ["strict_and", "specific_facility_required"], "strict_and"),
        ("수유실하고 유아 휴식 공간이 둘 다 있는 가족 코스", ["strict_and", "family_context", "specific_facility_required"], "strict_and"),
        ("장애인 화장실과 승강기 둘 중 하나라도 빠지면 제외해줘", ["strict_and", "mobility_context", "specific_facility_required"], "strict_and"),
        ("수유실이 안 보이면 기저귀 교환대라도 확인되는 곳", ["or_condition", "family_context", "specific_facility_required"], "or_condition"),
        ("엘리베이터가 없으면 경사로라도 확실하면 괜찮아", ["or_condition", "mobility_context", "specific_facility_required"], "or_condition"),
        ("수어가 안 되면 자막 안내라도 있으면 후보에 넣어줘", ["or_condition", "specific_facility_required"], "or_condition"),
        ("보조견 동반이나 시각장애 안내 자료 중 하나만 확실해도 돼", ["or_condition", "specific_facility_required"], "or_condition"),
        ("유모차 동선이 좋거나 아이가 앉아 쉴 곳이 있으면 충분해", ["or_condition", "family_context", "mobility_context"], "or_condition"),
        ("장애인 주차가 없으면 가까운 하차 동선이라도 확인되는 곳", ["or_condition", "mobility_context", "specific_facility_required"], "or_condition"),
        ("점자블록이든 촉지도든 시각장애 안내 근거 하나만 있으면 돼", ["or_condition", "specific_facility_required"], "or_condition"),
        ("계단을 피하기 어렵다면 오래 앉아 쉴 수 있는 장소라도 봐줘", ["or_condition", "mobility_context"], "or_condition"),
        ("풍경이 우선이고 장애인 주차는 있으면 가점 정도로만", ["soft_and"], "soft_and"),
        ("가족이 쉬기 좋은 게 먼저고 수유실은 보이면 참고해", ["soft_and", "family_context"], "soft_and"),
        ("어르신이 덜 걷는 코스가 핵심이고 화장실 표기는 부가 조건이야", ["soft_and", "mobility_context"], "soft_and"),
        ("시장 분위기가 중요하고 엘리베이터는 필수로 묶지 말아줘", ["soft_and"], "soft_and"),
        ("박물관이면 충분하고 오디오가이드는 덤으로 봐도 돼", ["soft_and"], "soft_and"),
        ("아이 체험 위주로 보고 유아 의자는 없으면 넘어가자", ["soft_and", "family_context"], "soft_and"),
        ("휠체어로 편하면 좋지만 카페 여부는 선택 조건이야", ["soft_and", "mobility_context"], "soft_and"),
        ("조용한 전시를 우선하고 자막 지원은 후보가 많을 때만 보자", ["soft_and"], "soft_and"),
        ("방금 본 후보에서 점자블록 근거 있는 곳만 다시 남겨", ["add_condition", "specific_facility_required"], "add_condition"),
        ("현재 결과는 유지하고 수유실 표기만 더 확인해줘", ["add_condition", "specific_facility_required"], "add_condition"),
        ("이전 목록 안에서 유모차 이동 편한 곳으로만 좁혀줘", ["add_condition", "mobility_context"], "add_condition"),
        ("아까 추천 중 아이랑 가기 좋은 후보만 다시 걸러줘", ["add_condition", "family_context"], "add_condition"),
        ("그 카드들에 장애인 화장실 근거도 같이 체크해줘", ["add_condition", "specific_facility_required"], "add_condition"),
        ("같은 지역 결과에서 계단 적은 곳만 추려줘", ["add_condition", "mobility_context"], "add_condition"),
        ("위 후보 중 보조견 동반 문구가 있는지만 봐줘", ["add_condition", "specific_facility_required"], "add_condition"),
        ("이 결과에 가족 휴식 가능성도 조건으로 얹어줘", ["add_condition", "family_context"], "add_condition"),
        ("시장 기준은 접고 이번엔 한적한 산책 코스로 바꿔줘", ["replace_condition"], "replace_condition"),
        ("아이 편의 대신 휠체어 이동 편한 기준으로 다시 볼게", ["replace_condition", "mobility_context"], "replace_condition"),
        ("수어 말고 자막 지원 쪽으로 기준을 바꿔줘", ["replace_condition", "specific_facility_required"], "replace_condition"),
        ("부산 말고 대전에서 장애인 주차 표기 있는 곳", ["replace_condition", "specific_facility_required"], "replace_condition"),
        ("숙박 느낌은 그만 보고 지역 문화 전시 중심으로", ["replace_condition"], "replace_condition"),
        ("오디오가이드 조건은 내려놓고 점자블록 기준으로 다시", ["replace_condition", "specific_facility_required"], "replace_condition"),
        ("유모차 동선은 유지하지 말고 어르신 보행 기준으로 바꿔", ["replace_condition", "mobility_context"], "replace_condition"),
        ("먹거리 말고 실내 관람 코스로 방향 바꿀래", ["replace_condition"], "replace_condition"),
        ("카페형 장소는 빼고 실제 관광지만 보여줘", ["exclude_condition"], "exclude_condition"),
        ("붐비는 골목은 제외하고 넓게 볼 수 있는 곳", ["exclude_condition", "mobility_context"], "exclude_condition"),
        ("야외 계단 많은 데는 빼고 평지 느낌으로", ["exclude_condition", "mobility_context"], "exclude_condition"),
        ("아이랑 가니까 술집 거리 분위기는 제외해줘", ["exclude_condition", "family_context"], "exclude_condition"),
        ("쇼핑 위주 후보는 뒤로 보내고 전시 위주로", ["exclude_condition"], "exclude_condition"),
        ("식당은 빼되 유모차로 이동 쉬운 주변 관광지는 좋아", ["exclude_condition", "mobility_context"], "exclude_condition"),
        ("숙박업소 느낌 나는 건 패스하고 낮에 볼거리만", ["exclude_condition"], "exclude_condition"),
        ("소음 많은 축제형 장소는 제외하고 조용한 곳", ["exclude_condition"], "exclude_condition"),
        ("초등학생이 직접 체험할 수 있는 관광지", ["family_context"], "family_context"),
        ("아기와 부모가 중간에 쉬기 좋은 짧은 코스", ["family_context", "mobility_context"], "family_context"),
        ("가족 사진 찍기 좋고 이동이 버겁지 않은 곳", ["family_context", "mobility_context"], "family_context"),
        ("유아용 시설이 없어도 아이가 지루하지 않을 장소", ["soft_and", "family_context"], "family_context"),
        ("아이 손잡고 걷기 부담이 적은 산책형 장소", ["family_context", "mobility_context"], "family_context"),
        ("부모님과 아이가 같이 둘러보기 쉬운 동선", ["family_context", "mobility_context"], "family_context"),
        ("수유실보다는 아이가 쉬어갈 수 있는 분위기가 중요해", ["soft_and", "family_context"], "family_context"),
        ("어린이 전시가 있는지 중심으로 추천해줘", ["family_context"], "family_context"),
        ("허리가 불편해서 오래 걷지 않아도 되는 곳", ["mobility_context"], "mobility_context"),
        ("오르내림이 적고 쉬어갈 의자가 있으면 좋겠어", ["mobility_context"], "mobility_context"),
        ("전동휠체어로 길이 끊기지 않는 코스", ["mobility_context"], "mobility_context"),
        ("줄 서는 시간이 길지 않은 실내 관광지", ["mobility_context"], "mobility_context"),
        ("발이 아픈 동행이 있어서 이동 반경이 작아야 해", ["mobility_context"], "mobility_context"),
        ("유모차로 좁은 골목을 피할 수 있는 곳", ["mobility_context"], "mobility_context"),
        ("계단보다 완만한 길 위주로 보고 싶어", ["mobility_context"], "mobility_context"),
        ("걷다가 앉아 쉴 수 있는 포인트가 있는 곳", ["mobility_context"], "mobility_context"),
        ("작품 제목의 점자가 아니라 실제 점자블록 여부가 필요해", ["specific_facility_required"], "specific_facility_required"),
        ("보조견 테마 전시 말고 보조견 동반 가능 표기를 봐줘", ["specific_facility_required"], "specific_facility_required"),
        ("수어라는 상호가 아니라 수어 안내 편의정보가 있는 곳", ["specific_facility_required"], "specific_facility_required"),
        ("장애인 주차 문구가 원문에 있어야 인정해", ["specific_facility_required"], "specific_facility_required"),
        ("자막 지원 여부가 명시되지 않으면 후보로 보지 마", ["specific_facility_required"], "specific_facility_required"),
        ("기저귀 교환대 편의정보가 확인되는 카드만", ["specific_facility_required"], "specific_facility_required"),
        ("엘리베이터 설치 여부가 명확한 곳만 골라줘", ["specific_facility_required"], "specific_facility_required"),
        ("촉지도 근거가 실제 편의정보에 있어야 해", ["specific_facility_required"], "specific_facility_required"),
        ("수어지교라는 식당 이름을 말한 거야 접근성은 아냐", [], "negative_near_miss"),
        ("점자 무늬 작품 이야기가 아니라 조용한 전시를 원해", [], "negative_near_miss"),
        ("가족이라는 브랜드명 말고 여행지 자체를 봐줘", [], "negative_near_miss"),
        ("엘리베이터라는 노래 제목은 빼고 전망 좋은 곳", [], "negative_near_miss"),
        ("주차장이라는 상호명일 뿐 주차 조건은 아니야", [], "negative_near_miss"),
        ("아이돌 행사 말고 일반 관광지 추천해줘", [], "negative_near_miss"),
        ("보조견 캐릭터 전시 제목이면 편의조건으로 보지 마", [], "negative_near_miss"),
        ("화장실 벽화가 유명한 곳이지 장애인 화장실 조건은 아냐", [], "negative_near_miss"),
    ]
    rows = [row(text, labels, category, variant="v2") for text, labels, category in cases]
    for index, item in enumerate(rows, start=1):
        item["id"] = f"CTXROT20260517V2{index:04d}"
    return rows


def build_rows_v3() -> list[dict[str, Any]]:
    cases = [
        ("장애인 주차장 표기랑 장애인 화장실 안내가 한 장소에 같이 없으면 후보에서 빼", ["strict_and", "specific_facility_required"], "strict_and"),
        ("경사로와 승강기 중 하나만 있으면 부족하고 둘 다 확인된 코스", ["strict_and", "mobility_context", "specific_facility_required"], "strict_and"),
        ("기저귀 갈 곳과 아이용 의자가 같은 카드에 적힌 곳만", ["strict_and", "family_context", "specific_facility_required"], "strict_and"),
        ("수어 통역과 자막 안내가 동시에 잡힌 전시만 보고 싶어", ["strict_and", "specific_facility_required"], "strict_and"),
        ("휠체어 이동 동선에 보조견 동반 가능까지 함께 맞아야 해", ["strict_and", "mobility_context", "specific_facility_required"], "strict_and"),
        ("점자블록과 촉지도 둘 중 하나 빠지면 이번 후보는 제외", ["strict_and", "specific_facility_required"], "strict_and"),
        ("수유실도 있고 유모차 대여도 되는 가족 방문지만", ["strict_and", "family_context", "specific_facility_required"], "strict_and"),
        ("엘리베이터랑 장애인 화장실이 모두 명시된 실내 장소", ["strict_and", "specific_facility_required"], "strict_and"),
        ("수유 공간이 없으면 기저귀 교환대라도 확인되면 좋아", ["or_condition", "family_context", "specific_facility_required"], "or_condition"),
        ("승강기가 안 보이면 완만한 경사로라도 있는 곳", ["or_condition", "mobility_context", "specific_facility_required"], "or_condition"),
        ("자막 안내나 수어 안내 둘 중 하나라도 분명하면 괜찮아", ["or_condition", "specific_facility_required"], "or_condition"),
        ("안내견 동반이 없으면 시각장애 안내 자료라도 후보로", ["or_condition", "specific_facility_required"], "or_condition"),
        ("유아차로 편하거나 아이가 쉬는 공간이 있거나 하면 충분", ["or_condition", "family_context", "mobility_context"], "or_condition"),
        ("장애인 주차가 없더라도 바로 내릴 수 있는 동선이면 봐줘", ["or_condition", "mobility_context", "specific_facility_required"], "or_condition"),
        ("점자블록 아니면 오디오 안내라도 실제 근거가 있으면 돼", ["or_condition", "specific_facility_required"], "or_condition"),
        ("계단 없는 곳이 최선이고 없으면 앉아 쉴 수 있는 곳이라도", ["or_condition", "mobility_context"], "or_condition"),
        ("실내 전시 분위기가 우선이고 자막은 있으면 좋은 정도", ["soft_and"], "soft_and"),
        ("아이랑 쉬기 좋은 곳이 먼저고 기저귀 시설은 참고 수준", ["soft_and", "family_context"], "soft_and"),
        ("부모님이 덜 걷는 게 중요하고 주차 표기는 보조 조건", ["soft_and", "mobility_context"], "soft_and"),
        ("시장 구경이 목적이고 엘리베이터까지 필수로 보진 말자", ["soft_and"], "soft_and"),
        ("박물관이면 충분하고 촉지도는 후보가 여럿일 때만 보자", ["soft_and"], "soft_and"),
        ("아이 체험이 핵심이고 유아용 의자 없으면 그냥 넘어가도 돼", ["soft_and", "family_context"], "soft_and"),
        ("휠체어 이동은 좋으면 좋고 음식점 여부는 필수 아님", ["soft_and", "mobility_context"], "soft_and"),
        ("조용한 산책이 먼저고 장애인 화장실은 가산점으로만", ["soft_and"], "soft_and"),
        ("지금 나온 카드 중 오디오가이드 근거 있는 곳만 남겨", ["add_condition", "specific_facility_required"], "add_condition"),
        ("방금 결과에 아이 동반 편의가 보이는 후보만 더 걸러줘", ["add_condition", "family_context"], "add_condition"),
        ("그 목록 안에서 계단 부담 적은 장소만 다시 추려", ["add_condition", "mobility_context"], "add_condition"),
        ("현재 후보는 그대로 두고 장애인 주차 문구만 추가 확인", ["add_condition", "specific_facility_required"], "add_condition"),
        ("위 카드들 중 수유실 있는 곳으로 좁혀줘", ["add_condition", "specific_facility_required"], "add_condition"),
        ("같은 결과에서 전동휠체어 동선이 괜찮은지만 봐줘", ["add_condition", "mobility_context"], "add_condition"),
        ("이전 추천 중 가족이 오래 머물기 편한 곳만 남겨줘", ["add_condition", "family_context"], "add_condition"),
        ("아까 후보에 수어 안내 여부도 같이 체크해", ["add_condition", "specific_facility_required"], "add_condition"),
        ("먹거리 중심은 접고 이번엔 조용한 전시 위주로 바꿔", ["replace_condition"], "replace_condition"),
        ("아이 기준 말고 어르신 이동 편한 기준으로 다시 볼래", ["replace_condition", "mobility_context"], "replace_condition"),
        ("자막 안내 대신 수어 통역 표기된 곳으로 바꿔줘", ["replace_condition", "specific_facility_required"], "replace_condition"),
        ("서울 말고 인천에서 장애인 화장실 표기 있는 곳", ["replace_condition", "specific_facility_required"], "replace_condition"),
        ("숙박 후보는 내려놓고 낮에 관람할 전시 중심으로", ["replace_condition"], "replace_condition"),
        ("점자블록 조건은 빼고 오디오가이드 기준으로 다시", ["replace_condition", "specific_facility_required"], "replace_condition"),
        ("유모차 편의 말고 휠체어 동선 쪽으로 기준 바꿔", ["replace_condition", "mobility_context"], "replace_condition"),
        ("카페 느낌은 그만 보고 자연 산책 코스로 갈래", ["replace_condition"], "replace_condition"),
        ("식당형 후보는 제외하고 관광지로 볼 수 있는 곳만", ["exclude_condition"], "exclude_condition"),
        ("복잡한 시장 안쪽은 빼고 넓게 움직이는 코스", ["exclude_condition", "mobility_context"], "exclude_condition"),
        ("계단 많은 야외 전망지는 패스하고 완만한 곳", ["exclude_condition", "mobility_context"], "exclude_condition"),
        ("아이랑 가서 밤거리 분위기는 제외해줘", ["exclude_condition", "family_context"], "exclude_condition"),
        ("쇼핑몰 위주 결과는 뒤로 미루고 지역 볼거리만", ["exclude_condition"], "exclude_condition"),
        ("음식점은 빼되 유아차 이동이 쉬운 주변 관광지는 괜찮아", ["exclude_condition", "mobility_context"], "exclude_condition"),
        ("숙소처럼 보이는 곳은 빼고 낮에 방문할 장소", ["exclude_condition"], "exclude_condition"),
        ("시끄러운 축제장은 제외하고 차분한 관람지", ["exclude_condition"], "exclude_condition"),
        ("초등학생이 직접 만져보고 배울 만한 체험 공간", ["family_context"], "family_context"),
        ("아기랑 부모가 잠깐 쉬어갈 수 있는 짧은 나들이", ["family_context", "mobility_context"], "family_context"),
        ("아이와 부모님이 같이 둘러봐도 힘들지 않은 코스", ["family_context", "mobility_context"], "family_context"),
        ("유아 시설은 없어도 아이가 흥미를 느낄 만한 곳", ["soft_and", "family_context"], "family_context"),
        ("아이 손잡고 걷기 편한 실내외 동선", ["family_context", "mobility_context"], "family_context"),
        ("가족이 사진 찍고 오래 걷지 않아도 되는 장소", ["family_context", "mobility_context"], "family_context"),
        ("기저귀 교환대보다 아이가 편히 쉴 분위기가 중요", ["soft_and", "family_context"], "family_context"),
        ("어린이가 보기 쉬운 설명이나 체험이 있는 전시", ["family_context"], "family_context"),
        ("무릎이 안 좋아서 오르막이 적어야 해", ["mobility_context"], "mobility_context"),
        ("발목 보호대를 한 동행자가 있어 동선이 짧았으면 해", ["mobility_context"], "mobility_context"),
        ("오래 줄 서지 않고 바로 둘러볼 수 있는 곳", ["mobility_context"], "mobility_context"),
        ("전동 스쿠터가 다니기 애매하지 않은 길", ["mobility_context"], "mobility_context"),
        ("계단을 피하고 완만하게 이동 가능한 장소", ["mobility_context"], "mobility_context"),
        ("어르신이 앉아서 쉬는 지점이 중간중간 있는 코스", ["mobility_context"], "mobility_context"),
        ("유아차가 좁은 통로에서 막히지 않는 곳", ["mobility_context"], "mobility_context"),
        ("걷는 거리가 짧고 쉬어갈 벤치가 있으면 좋겠어", ["mobility_context"], "mobility_context"),
        ("점자라는 작품 설명 말고 점자블록 편의 여부가 필요해", ["specific_facility_required"], "specific_facility_required"),
        ("보조견 캐릭터가 아니라 보조견 동반 가능 안내를 봐줘", ["specific_facility_required"], "specific_facility_required"),
        ("수어라는 상호 말고 실제 수어 안내가 있는 곳", ["specific_facility_required"], "specific_facility_required"),
        ("장애인 주차 가능 문구가 원문에 있어야 후보야", ["specific_facility_required"], "specific_facility_required"),
        ("자막 지원 표기가 없으면 청각장애 조건은 충족 못 해", ["specific_facility_required"], "specific_facility_required"),
        ("기저귀 교환대가 편의정보에 확인되는 장소만", ["specific_facility_required"], "specific_facility_required"),
        ("엘베라는 별명 말고 엘리베이터 설치 여부가 필요해", ["specific_facility_required"], "specific_facility_required"),
        ("촉지도나 점자 안내 근거가 명시된 곳", ["or_condition", "specific_facility_required"], "specific_facility_required"),
        ("수어지교라는 가게 이름을 말한 거라 수어 안내 조건은 아니야", [], "negative_near_miss"),
        ("점자 패턴 디자인이 예쁜 전시지 접근성 얘기는 아냐", [], "negative_near_miss"),
        ("가족사진관이라는 상호명 말고 관광지를 찾는 거야", [], "negative_near_miss"),
        ("엘리베이터라는 노래가 흐르는 카페 말고 조용한 곳", ["exclude_condition"], "negative_near_miss"),
        ("주차장 벽화가 유명한 곳이지 주차 조건을 묻는 건 아니야", [], "negative_near_miss"),
        ("아이돌 공연장은 빼고 일반 관광지를 보고 싶어", ["exclude_condition"], "negative_near_miss"),
        ("보조견 캐릭터 상품 전시라면 편의정보로 세지 마", [], "negative_near_miss"),
        ("화장실 타일 전시가 유명한 곳이지 장애인 화장실 조건 아님", [], "negative_near_miss"),
    ]
    rows = [row(text, labels, category, variant="v3") for text, labels, category in cases]
    for index, item in enumerate(rows, start=1):
        item["id"] = f"CTXROT20260517V3{index:04d}"
    return rows


def build_rows_v4() -> list[dict[str, Any]]:
    cases = [
        ("방금처럼 휠체어 접근만 있는 곳 말고 장애인 화장실까지 같은 카드에서 확인되는 곳", ["strict_and", "specific_facility_required"], "strict_and"),
        ("주차 가능 문구와 출입구 경사로 설명이 둘 다 안 보이면 이번엔 넘겨", ["strict_and", "mobility_context", "specific_facility_required"], "strict_and"),
        ("수유실과 기저귀 교환대가 한 장소에 같이 확인된 가족 후보만", ["strict_and", "family_context", "specific_facility_required"], "strict_and"),
        ("점자블록도 있고 음성 안내도 있는 식으로 두 근거가 같이 있어야 해", ["strict_and", "specific_facility_required"], "strict_and"),
        ("수어 안내와 자막 안내가 한 장소에 같이 적힌 문화시설만", ["strict_and", "specific_facility_required"], "strict_and"),
        ("보조견 동반 가능하고 실내 동선도 끊기지 않는 곳이어야 해", ["strict_and", "mobility_context", "specific_facility_required"], "strict_and"),
        ("유모차 대여와 아이 쉬는 공간 둘 중 하나만 있으면 부족해 둘 다 봐줘", ["strict_and", "family_context", "specific_facility_required"], "strict_and"),
        ("장애인 주차와 승강기 표기가 동시에 확인되는 카드로만", ["strict_and", "mobility_context", "specific_facility_required"], "strict_and"),
        ("장애인 화장실이 없으면 주차 근거라도 분명한 곳으로", ["or_condition", "specific_facility_required"], "or_condition"),
        ("수어 안내가 없으면 자막 영상 안내라도 있으면 돼", ["or_condition", "specific_facility_required"], "or_condition"),
        ("점자블록 아니면 촉지도 중 하나라도 실제 편의정보에 있으면 보여줘", ["or_condition", "specific_facility_required"], "or_condition"),
        ("승강기든 완만한 진입로든 바퀴 이동 근거 하나만 있으면 괜찮아", ["or_condition", "mobility_context", "specific_facility_required"], "or_condition"),
        ("수유실이 최선이고 안 보이면 기저귀 갈 수 있는 곳이라도", ["or_condition", "family_context", "specific_facility_required"], "or_condition"),
        ("보조견이 안 되면 시각장애 안내 자료라도 명확한 곳", ["or_condition", "specific_facility_required"], "or_condition"),
        ("계단을 못 피하면 중간에 오래 앉아 쉴 수 있는 곳이라도 봐줘", ["or_condition", "mobility_context"], "or_condition"),
        ("유아차 이동이 편하거나 아이 체험이 좋거나 둘 중 하나면 충분해", ["or_condition", "family_context", "mobility_context"], "or_condition"),
        ("조용한 전시가 핵심이고 장애인 주차는 후보가 많을 때만 참고해", ["soft_and"], "soft_and"),
        ("아이랑 쉬기 좋은 분위기가 먼저고 수유실은 있으면 고마운 정도", ["soft_and", "family_context"], "soft_and"),
        ("부모님이 덜 걷는 코스가 우선이고 화장실은 보조 조건으로만", ["soft_and", "mobility_context"], "soft_and"),
        ("시장 구경이 목적이고 경사로까지 필수로 묶지는 말아줘", ["soft_and"], "soft_and"),
        ("박물관이면 충분하고 오디오가이드는 덤으로만 보자", ["soft_and"], "soft_and"),
        ("유아 의자보다 아이가 지루하지 않은지가 더 중요해", ["soft_and", "family_context"], "soft_and"),
        ("휠체어로 편하면 좋지만 카페인지 여부는 참고만", ["soft_and", "mobility_context"], "soft_and"),
        ("산책 분위기가 우선이고 점자 안내는 있으면 가산점 정도야", ["soft_and"], "soft_and"),
        ("위 후보에서 장애인 화장실 원문 근거 있는 것만 남겨줘", ["add_condition", "specific_facility_required"], "add_condition"),
        ("방금 카드들에 수어 안내 여부도 추가로 확인해", ["add_condition", "specific_facility_required"], "add_condition"),
        ("그 결과 안에서 아이랑 오래 머물기 편한 곳만 다시 걸러줘", ["add_condition", "family_context"], "add_condition"),
        ("현재 추천은 유지하고 전동휠체어 동선이 괜찮은지만 봐줘", ["add_condition", "mobility_context"], "add_condition"),
        ("아까 후보 중 주차장 문구가 있는 곳으로 좁혀줘", ["add_condition", "specific_facility_required"], "add_condition"),
        ("같은 목록에서 수유실 표기 있는 곳만 다시 추려", ["add_condition", "family_context", "specific_facility_required"], "add_condition"),
        ("방금 결과에 점자블록 근거가 있는지도 조건으로 얹어줘", ["add_condition", "specific_facility_required"], "add_condition"),
        ("그 카드들 중 계단 부담 적은 곳만 남겨줘", ["add_condition", "mobility_context"], "add_condition"),
        ("시장 위주는 취소하고 조용한 전시 공간으로 다시", ["replace_condition"], "replace_condition"),
        ("유모차 기준 말고 휠체어 동선 기준으로 바꿔줘", ["replace_condition", "mobility_context"], "replace_condition"),
        ("수어 안내 대신 자막 안내 확인되는 곳으로 기준 변경", ["replace_condition", "specific_facility_required"], "replace_condition"),
        ("서울 말고 대구에서 장애인 주차 되는 곳으로 다시", ["replace_condition", "specific_facility_required"], "replace_condition"),
        ("가족 체험은 내려놓고 어르신 이동 부담 적은 곳으로", ["replace_condition", "mobility_context"], "replace_condition"),
        ("오디오가이드 조건은 빼고 촉지도 기준으로 볼게", ["replace_condition", "specific_facility_required"], "replace_condition"),
        ("먹거리 말고 자연 산책 위주 관광지로 바꿀래", ["replace_condition"], "replace_condition"),
        ("보조견 조건은 유지 말고 점자 안내 기준으로 다시 찾아줘", ["replace_condition", "specific_facility_required"], "replace_condition"),
        ("식당이나 카페 느낌은 빼고 관광지 성격만 보고 싶어", ["exclude_condition"], "exclude_condition"),
        ("시장 안쪽 골목은 제외하고 넓은 동선 위주로", ["exclude_condition", "mobility_context"], "exclude_condition"),
        ("숙박업소처럼 보이는 후보는 패스하고 낮에 볼거리만", ["exclude_condition"], "exclude_condition"),
        ("아이랑 가니까 술집 거리 분위기는 빼줘", ["exclude_condition", "family_context"], "exclude_condition"),
        ("계단 많은 전망대는 제외하고 평탄한 쪽으로", ["exclude_condition", "mobility_context"], "exclude_condition"),
        ("쇼핑몰 위주는 뒤로 빼고 지역 문화 공간만", ["exclude_condition"], "exclude_condition"),
        ("시끄러운 공연장은 빼고 차분히 볼 수 있는 곳", ["exclude_condition"], "exclude_condition"),
        ("호텔 카페는 빼되 유모차 이동 쉬운 관광지는 괜찮아", ["exclude_condition", "mobility_context"], "exclude_condition"),
        ("초등 아이가 직접 만져보거나 배울 수 있는 곳", ["family_context"], "family_context"),
        ("아기 낮잠 전후로 짧게 다녀올 가족 나들이", ["family_context", "mobility_context"], "family_context"),
        ("부모님과 아이가 같이 둘러봐도 덜 지치는 코스", ["family_context", "mobility_context"], "family_context"),
        ("기저귀 시설은 없어도 아이가 편히 쉬는 분위기면 돼", ["soft_and", "family_context"], "family_context"),
        ("어린이 설명이 잘 되어 있는 역사 전시", ["family_context"], "family_context"),
        ("아이 손잡고 좁은 통로를 피할 수 있는 곳", ["family_context", "mobility_context"], "family_context"),
        ("가족 사진 찍고 오래 걷지 않아도 되는 장소", ["family_context", "mobility_context"], "family_context"),
        ("수유실보다 아이가 지루하지 않은 동선이 중요해", ["soft_and", "family_context", "mobility_context"], "family_context"),
        ("허리가 불편해서 오래 서 있지 않아도 되는 장소", ["mobility_context"], "mobility_context"),
        ("발목 다친 사람이 있어 이동 반경이 짧아야 해", ["mobility_context"], "mobility_context"),
        ("전동 스쿠터로 입구에서 전시장까지 끊기지 않는 코스", ["mobility_context"], "mobility_context"),
        ("오르막보다 평지가 많고 앉아 쉴 곳이 있으면 좋겠어", ["mobility_context"], "mobility_context"),
        ("계단을 최대한 피하고 완만하게 움직일 수 있는 곳", ["mobility_context"], "mobility_context"),
        ("유아차가 사람 많은 좁은 길을 지나지 않아도 되는 곳", ["mobility_context"], "mobility_context"),
        ("줄 오래 안 서고 바로 둘러볼 수 있는 실내 장소", ["mobility_context"], "mobility_context"),
        ("무릎이 불편한 동행이 중간중간 쉬어갈 수 있는 코스", ["mobility_context"], "mobility_context"),
        ("수어라는 상호가 아니라 실제 수어 안내 제공 여부", ["specific_facility_required"], "specific_facility_required"),
        ("점자 테마 전시가 아니라 점자블록 편의정보를 확인해", ["specific_facility_required"], "specific_facility_required"),
        ("엘리베이터라는 노래 제목 말고 승강기 설치 여부가 필요해", ["specific_facility_required"], "specific_facility_required"),
        ("보조견 캐릭터 상품이 아니라 보조견 동반 가능 안내를 봐줘", ["specific_facility_required"], "specific_facility_required"),
        ("장애인 주차 가능 문구가 원문에 있어야 인정", ["specific_facility_required"], "specific_facility_required"),
        ("자막 지원 표기가 카드에 없으면 청각장애 조건은 미충족", ["specific_facility_required"], "specific_facility_required"),
        ("유아용 의자가 실제 편의정보에 있는지 확인된 곳만", ["specific_facility_required"], "specific_facility_required"),
        ("촉지도 안내 여부가 명시된 곳으로만 봐줘", ["specific_facility_required"], "specific_facility_required"),
        ("수어지교라는 가게 이름 때문에 찾는 거지 수어 안내 조건은 아냐", [], "negative_near_miss"),
        ("점자 무늬 디자인이 유명한 전시라 접근성 조건은 아니야", [], "negative_near_miss"),
        ("가족사진관 상호명 말고 실제 가족 동반 관광지를 봐줘", [], "negative_near_miss"),
        ("주차장 벽화가 주제인 곳이지 주차 가능 여부는 묻는 게 아냐", [], "negative_near_miss"),
        ("엘리베이터 음악이 나오는 카페 얘기라 승강기 조건 아님", [], "negative_near_miss"),
        ("아이돌 공연은 빼고 어린이 체험 관광지를 찾는 거야", ["exclude_condition", "family_context"], "negative_near_miss"),
        ("화장실 타일 작품이 유명한 곳이지 장애인 화장실 조건은 아냐", [], "negative_near_miss"),
        ("보조견이라는 캐릭터 전시 제목이면 편의정보로 세지 마", [], "negative_near_miss"),
    ]
    rows = [row(text, labels, category, variant="v4") for text, labels, category in cases]
    for index, item in enumerate(rows, start=1):
        item["id"] = f"CTXROT20260517V4{index:04d}"
    return rows


def build_rows_v5() -> list[dict[str, Any]]:
    cases = [
        ("경사로 아니면 엘리베이터 둘 중 하나만 확인돼도 휠체어 이동은 가능할 것 같아", ["or_condition", "mobility_context", "specific_facility_required"], "or_mobility_facility"),
        ("수유실이 없으면 기저귀 교환대라도 있는 가족 코스면 돼", ["or_condition", "family_context", "specific_facility_required"], "or_family_facility"),
        ("수어 안내나 자막 자료 중 하나만 있어도 청각장애 동행자는 괜찮아", ["or_condition", "specific_facility_required"], "or_accessibility"),
        ("장애인 주차가 없으면 바로 내릴 수 있는 짧은 동선이라도 봐줘", ["or_condition", "mobility_context", "specific_facility_required"], "or_mobility_facility"),
        ("점자블록 또는 촉지도 둘 중 하나라도 실제 편의정보에 있으면 후보로", ["or_condition", "specific_facility_required"], "or_accessibility"),
        ("유모차 이동이 편하거나 아이가 쉴 공간이 있거나 하나면 충분해", ["or_condition", "family_context", "mobility_context"], "or_family_mobility"),
        ("오디오가이드가 없으면 음성안내라도 명확한 곳", ["or_condition", "specific_facility_required"], "or_accessibility"),
        ("계단이 적거나 중간에 앉아 쉴 곳이 있으면 어르신에게 괜찮아", ["or_condition", "mobility_context"], "or_mobility"),
        ("가족이 쉬기 좋은 게 우선이고 수유실은 확인되면 좋아", ["soft_and", "family_context"], "soft_family"),
        ("아이랑 갈 거라 덜 붐비는 곳이 먼저고 기저귀 교환대는 있으면 참고", ["soft_and", "family_context"], "soft_family"),
        ("어르신이 오래 걷지 않는 게 핵심이고 장애인 주차는 보이면 가점", ["soft_and", "mobility_context"], "soft_mobility"),
        ("휠체어 이동이 편한 쪽을 먼저 보고 엘리베이터 표기는 후보 많을 때만 보자", ["soft_and", "mobility_context"], "soft_mobility"),
        ("조용한 실내 전시가 목적이고 자막 지원은 덤으로만 봐줘", ["soft_and"], "soft_optional_facility"),
        ("시장 구경이 목적이라 화장실 표기는 필수로 묶지 말아줘", ["soft_and"], "soft_optional_facility"),
        ("산책 코스가 우선이고 경사로는 없으면 넘어가도 돼", ["soft_and"], "soft_optional_facility"),
        ("아기 낮잠 시간 때문에 짧은 코스가 먼저고 수유실은 가능하면 좋겠어", ["soft_and", "family_context", "mobility_context"], "soft_family_mobility"),
        ("방금 결과에서 장애인 화장실 표기 있는 곳만 다시 걸러줘", ["add_condition", "specific_facility_required"], "add_facility"),
        ("위 후보는 유지하고 엘리베이터 확인되는 카드만 남겨줘", ["add_condition", "specific_facility_required"], "add_facility"),
        ("그 목록 안에서 유모차 이동 편한 곳으로만 좁혀줘", ["add_condition", "mobility_context"], "add_mobility"),
        ("아까 추천 중 아이랑 가기 좋은 후보만 한 번 더 추려줘", ["add_condition", "family_context"], "add_family"),
        ("같은 지역 결과에서 보조견 동반 가능 문구까지 같이 체크해줘", ["add_condition", "specific_facility_required"], "add_facility"),
        ("현재 카드들 중 계단 적은 곳만 다시 보여줘", ["add_condition", "mobility_context"], "add_mobility"),
        ("이전 추천에 수어 안내 조건을 하나 더 얹어줘", ["add_condition", "specific_facility_required"], "add_facility"),
        ("전 후보에서 가족 휴식하기 좋은 곳만 남겨줘", ["add_condition", "family_context"], "add_family"),
        ("수유실 기준은 내려놓고 조용한 전시 중심으로 바꿔줘", ["replace_condition"], "replace"),
        ("시장 말고 공원 산책 코스 기준으로 다시 볼래", ["replace_condition"], "replace"),
        ("아이 편의 대신 어르신 보행 편한 기준으로 바꿔줘", ["replace_condition", "mobility_context"], "replace_mobility"),
        ("점자블록 말고 오디오가이드 확인되는 쪽으로 바꿀게", ["replace_condition", "specific_facility_required"], "replace_facility"),
        ("부산 말고 대전에서 장애인 주차 있는 곳으로", ["replace_condition", "specific_facility_required"], "replace_region_facility"),
        ("휠체어 조건은 빼고 유모차 동선 위주로 다시", ["replace_condition", "mobility_context"], "replace_mobility"),
        ("먹거리 위주는 취소하고 실내 관람 쪽으로 갈아타자", ["replace_condition"], "replace"),
        ("자막 안내 대신 수어 안내 확인되는 곳으로", ["replace_condition", "specific_facility_required"], "replace_facility"),
        ("카페형 장소는 제외하고 관광지만 보여줘", ["exclude_condition"], "exclude"),
        ("붐비는 시장 골목은 빼고 한적한 곳 위주로", ["exclude_condition"], "exclude"),
        ("야외 오래 걷는 곳은 제외하고 실내 쉬운 동선으로", ["exclude_condition", "mobility_context"], "exclude_mobility"),
        ("아이와 가니까 술집 거리 분위기는 빼줘", ["exclude_condition", "family_context"], "exclude_family"),
        ("숙박업소 느낌 나는 후보는 뒤로 보내줘", ["exclude_condition"], "exclude"),
        ("계단 많은 전망대는 패스하고 평지 위주로", ["exclude_condition", "mobility_context"], "exclude_mobility"),
        ("쇼핑몰 성격은 제외하고 지역 문화 볼거리만", ["exclude_condition"], "exclude"),
        ("음식점은 빼되 유모차로 이동 쉬운 주변 관광지는 좋아", ["exclude_condition", "mobility_context"], "exclude_mobility"),
        ("아이 손잡고 걷기 부담 적은 체험 장소", ["family_context", "mobility_context"], "family_mobility"),
        ("초등학생이 직접 볼 만한 역사 전시", ["family_context"], "family"),
        ("아기와 부모가 짧게 둘러보기 좋은 코스", ["family_context", "mobility_context"], "family_mobility"),
        ("가족사진 찍기 좋고 너무 오래 걷지 않는 곳", ["family_context", "mobility_context"], "family_mobility"),
        ("수유실은 없어도 아이가 쉬기 좋은 곳이면 돼", ["soft_and", "family_context"], "family_soft"),
        ("어린이 눈높이에 맞는 체험형 관광지", ["family_context"], "family"),
        ("부모님과 아이가 같이 움직이기 쉬운 동선", ["family_context", "mobility_context"], "family_mobility"),
        ("아이용 의자보다 아이가 지루하지 않은 구성이 중요해", ["soft_and", "family_context"], "family_soft"),
        ("무릎이 불편해서 오르막 적은 코스", ["mobility_context"], "mobility"),
        ("발목 다친 동행이 있어서 이동 거리가 짧아야 해", ["mobility_context"], "mobility"),
        ("전동휠체어로 동선이 끊기지 않는 곳", ["mobility_context"], "mobility"),
        ("오래 줄 서지 않아도 볼 수 있는 관광지", ["mobility_context"], "mobility"),
        ("걷다가 앉아 쉴 수 있는 포인트가 있는 곳", ["mobility_context"], "mobility"),
        ("계단을 최대한 피해서 움직일 수 있는 실내 장소", ["mobility_context"], "mobility"),
        ("유모차로 좁은 골목을 헤치지 않아도 되는 곳", ["mobility_context"], "mobility"),
        ("어르신이 중간중간 쉬기 쉬운 코스", ["mobility_context"], "mobility"),
        ("수어라는 상호가 아니라 실제 수어 안내 여부를 봐줘", ["specific_facility_required"], "facility"),
        ("장애인 화장실 표기가 없으면 후보로 세지 마", ["specific_facility_required"], "facility"),
        ("점자 느낌 전시가 아니라 점자블록 편의정보가 필요해", ["specific_facility_required"], "facility"),
        ("엘베가 있다는 근거가 카드에 있어야 해", ["specific_facility_required"], "facility"),
        ("보조견 동반 가능 여부가 명시된 곳만", ["specific_facility_required"], "facility"),
        ("기저귀 교환대 문구는 원문 근거가 있을 때만 인정해", ["specific_facility_required"], "facility"),
        ("자막 지원 여부가 명확하지 않으면 추천하지 마", ["specific_facility_required"], "facility"),
        ("장애인 주차 가능 여부만 정확히 봐줘", ["specific_facility_required"], "facility"),
        ("수어지교라는 이름의 장소를 찾는 게 아니야", [], "negative"),
        ("화장실 이야기가 아니라 바다 풍경이 좋은 곳", [], "negative"),
        ("점자라는 작품명이 있어도 접근성 조건은 아니야", [], "negative"),
        ("아이돌 굿즈 시장이지 아이 동반 얘기는 아니야", [], "negative"),
        ("엘리베이터 음악 얘기 말고 조용한 관람지", [], "negative"),
        ("보조견이라는 전시 제목이면 편의조건으로 보지 마", [], "negative"),
        ("가족이라는 상호명 말고 실제 관광지를 봐줘", [], "negative"),
        ("주차장 벽화가 유명한 곳이지 주차 가능 조건은 아냐", [], "negative"),
    ]
    rows = [row(text, labels, category, variant="v5") for text, labels, category in cases]
    for index, item in enumerate(rows, start=1):
        item["id"] = f"CTXROT20260517V5{index:04d}"
    return rows


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        for item in rows:
            file.write(json.dumps(item, ensure_ascii=False, sort_keys=True) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--variant", choices=["v1", "v2", "v3", "v4", "v5"], default="v1")
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    output = args.output
    if output is None:
        if args.variant == "v5":
            output = DEFAULT_OUTPUT_V5
        elif args.variant == "v4":
            output = DEFAULT_OUTPUT_V4
        elif args.variant == "v3":
            output = DEFAULT_OUTPUT_V3
        elif args.variant == "v2":
            output = DEFAULT_OUTPUT_V2
        else:
            output = DEFAULT_OUTPUT
    seen = load_seen_texts(OVERLAP_INPUTS)
    if args.variant == "v5":
        source_rows = build_rows_v5()
    elif args.variant == "v4":
        source_rows = build_rows_v4()
    elif args.variant == "v3":
        source_rows = build_rows_v3()
    elif args.variant == "v2":
        source_rows = build_rows_v2()
    else:
        source_rows = build_rows()
    rows = []
    dropped = 0
    for item in source_rows:
        if normalize(str(item["text"])) in seen:
            dropped += 1
            continue
        rows.append(item)

    write_jsonl(output, rows)
    label_counts: dict[str, int] = {"<none>": 0}
    for item in rows:
        labels = item["labels"]
        if not labels:
            label_counts["<none>"] += 1
        for label in labels:
            label_counts[label] = label_counts.get(label, 0) + 1
    print(
        json.dumps(
            {
                "output": str(output.relative_to(PROJECT_ROOT)),
                "variant": args.variant,
                "rows": len(rows),
                "dropped_exact_overlaps": dropped,
                "label_counts": dict(sorted(label_counts.items())),
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
