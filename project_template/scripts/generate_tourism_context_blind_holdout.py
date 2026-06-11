from __future__ import annotations

import json
from pathlib import Path
import sys
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.services.tourism_context_classifier import CONTEXT_LABELS  # noqa: E402


DEFAULT_OUTPUT = PROJECT_ROOT / "data" / "eval" / "tourism_context_blind_holdout.jsonl"


def row(text: str, labels: list[str], category: str, rationale: str) -> dict[str, Any]:
    return {
        "text": " ".join(text.split()),
        "labels": [label for label in CONTEXT_LABELS if label in set(labels)],
        "category": category,
        "template_family": "llm_blind_manual_v1",
        "rationale": rationale,
        "source": "codex_llm_blind_holdout",
    }


def build_rows() -> list[dict[str, Any]]:
    rows = [
        row("점자블록이랑 안내견 둘 중 하나라도 빠지면 이번엔 후보에서 빼줘", ["strict_and", "specific_facility_required"], "strict_and", "Both named facilities are mandatory."),
        row("주차랑 화장실이 같이 확인된 데만 보고 싶어. 하나만 되는 곳은 말고", ["strict_and", "specific_facility_required"], "strict_and", "Parking and restroom evidence are both required."),
        row("수어 안내, 자막 안내가 한 장소 안에 같이 있는지만 먼저 걸러줘", ["strict_and", "specific_facility_required"], "strict_and", "Both sensory-access facilities are required in one place."),
        row("엘베만 있거나 경사로만 있는 곳 말고 두 조건이 같이 맞는 데로", ["strict_and", "specific_facility_required"], "strict_and", "Both elevator and ramp are required despite colloquial elevator spelling."),
        row("기저귀 갈 곳이랑 유아 의자가 둘 다 되는 식당만 남겨줘", ["strict_and", "family_context", "specific_facility_required"], "strict_and", "Family facilities are mandatory."),
        row("휠체어 접근 가능하고 장애인 화장실도 확인된 카드만 보고 싶다", ["strict_and", "mobility_context", "specific_facility_required"], "strict_and", "Mobility context plus required restroom evidence."),
        row("오디오가이드하고 촉지도 중 하나라도 없으면 패스할게", ["strict_and", "specific_facility_required"], "strict_and", "Both visual-access supports are mandatory."),
        row("전동휠체어 이동이랑 엘리베이터가 동시에 해결되는 곳으로만", ["strict_and", "mobility_context", "specific_facility_required"], "strict_and", "Mobility plus elevator are mandatory."),
        row("수어 안내나 자막 안내 중 확인되는 쪽이면 돼", ["or_condition", "specific_facility_required"], "or_condition", "Either sensory-access facility is acceptable."),
        row("주차가 확실하지 않으면 화장실 정보라도 분명한 곳으로 골라줘", ["or_condition", "specific_facility_required"], "or_condition", "Fallback from one facility to another."),
        row("안내견 동반 가능 아니면 점자 안내라도 괜찮아", ["or_condition", "specific_facility_required"], "or_condition", "Either guide dog or tactile/visual aid is acceptable."),
        row("경사로든 엘리베이터든 바퀴로 이동할 근거 하나만 있으면 돼", ["or_condition", "mobility_context", "specific_facility_required"], "or_condition", "One of two mobility facilities is enough."),
        row("아이 데리고 가는 거라 수유실 아니면 기저귀 교환대라도 있으면 좋겠어", ["or_condition", "family_context", "specific_facility_required"], "or_condition", "Family context with either facility acceptable."),
        row("수어가 베스트지만 없으면 자막 있는 곳도 후보에 넣어줘", ["or_condition", "specific_facility_required"], "or_condition", "Fallback acceptable condition."),
        row("휠체어 이용자라 경사로 또는 승강기 중 하나라도 확인되면 돼", ["or_condition", "mobility_context", "specific_facility_required"], "or_condition", "Mobility OR condition."),
        row("점자블록까지 꼭은 아니고 시각장애인 안내가 조금이라도 있으면 봐줘", ["or_condition", "specific_facility_required"], "or_condition", "Any visual-access evidence is acceptable."),
        row("시장 구경이 우선이고 화장실 정보는 있으면 참고만 할게", ["soft_and"], "soft_and", "Facility is optional and main preference is market browsing."),
        row("아이랑 편한 분위기면 충분하고 수유실은 있으면 고맙고 없으면 말고", ["soft_and", "family_context"], "soft_and", "Family context with optional nursing room."),
        row("휠체어 이동이 편한 곳 위주로 보되 카페 느낌도 괜찮으면 섞어줘", ["soft_and", "mobility_context"], "soft_and", "Mobility is main, cafe preference optional."),
        row("조용한 산책이 먼저고 경사로는 후보 적을 때만 가산점 정도로", ["soft_and"], "soft_and", "Ramp is optional ranking signal."),
        row("박물관이면 좋고 장애인 주차는 필수까진 아니야", ["soft_and"], "soft_and", "Parking is optional."),
        row("애기랑 가니 붐비지 않는 게 우선이고 유아 의자는 덤으로 봐줘", ["soft_and", "family_context"], "soft_and", "Child context with optional chair."),
        row("어르신 모시고 가서 걷기 부담 없는 곳 우선, 먹거리는 있으면 좋아", ["soft_and", "mobility_context"], "soft_and", "Mobility is core; food is optional."),
        row("전시 위주로 보되 자막 안내도 보이면 좋겠어", ["soft_and"], "soft_and", "Caption is optional."),
        row("아까 본 부산 중구 결과에서 장애인 화장실 조건도 추가해줘", ["add_condition", "specific_facility_required"], "add_condition", "Adds a required facility to existing result set."),
        row("방금 후보들 중에서 아이랑 가도 괜찮은 곳만 다시 추려줘", ["add_condition", "family_context"], "add_condition", "Adds family context to existing candidates."),
        row("그 목록에 경사로 근거 있는지까지 한 번 더 걸러줘", ["add_condition", "specific_facility_required"], "add_condition", "Adds ramp facility filter."),
        row("현재 추천에서 시장 느낌은 유지하고 수어 안내 되는지만 더 봐줘", ["add_condition", "specific_facility_required"], "add_condition", "Adds sign-language evidence while keeping previous preference."),
        row("이전 결과 안에서 휠체어 동선 짧은 곳으로 좁혀줘", ["add_condition", "mobility_context"], "add_condition", "Adds mobility filter inside prior results."),
        row("위 카드들 중 주차 문구가 확인되는 것만 남겨줘", ["add_condition", "specific_facility_required"], "add_condition", "Adds parking evidence filter."),
        row("아까 장소들에 유모차로 다니기 편한지도 같이 체크해줘", ["add_condition", "mobility_context"], "add_condition", "Adds stroller mobility context."),
        row("기존 추천에서 보조견 동반 근거가 있는 카드만 다시", ["add_condition", "specific_facility_required"], "add_condition", "Adds guide-dog evidence filter."),
        row("휠체어 조건은 잠깐 내려놓고 아이랑 편한 곳 기준으로 바꿔줘", ["replace_condition", "family_context"], "replace_condition", "Replaces previous mobility condition with family context."),
        row("수어 안내 말고 이번엔 오디오가이드 있는 곳으로 갈아타자", ["replace_condition", "specific_facility_required"], "replace_condition", "Replaces old facility with audio guide."),
        row("시장 위주였던 건 취소하고 실내 전시 쪽으로 다시 추천해줘", ["replace_condition"], "replace_condition", "Replaces preference category."),
        row("부산 중구 말고 이번엔 대구 기준으로 장애인 화장실 있는 곳", ["replace_condition", "specific_facility_required"], "replace_condition", "Region changes and facility remains required."),
        row("유모차 편의는 빼고 전동휠체어 이동 기준으로 다시 볼래", ["replace_condition", "mobility_context"], "replace_condition", "Replaces stroller/family-ish condition with mobility condition."),
        row("카페는 그만 보고 공원 산책 가능한 곳으로 바꿔줘", ["replace_condition"], "replace_condition", "Replaces place type."),
        row("자막 안내 대신 보조견 동반 가능한지로 기준 바꿔줘", ["replace_condition", "specific_facility_required"], "replace_condition", "Replaces one accessibility facility with another."),
        row("아이 조건은 빼고 어르신 걷기 편한 쪽으로 다시", ["replace_condition", "mobility_context"], "replace_condition", "Replaces family context with mobility context."),
        row("숙박 업소는 빼고 관광지 카드만 보여줘", ["exclude_condition"], "exclude_condition", "Excludes lodging type."),
        row("시장 골목 말고 조용한 곳만 보고 싶어", ["exclude_condition"], "exclude_condition", "Excludes market alleys."),
        row("카페 분위기는 제외하고 산책 위주로", ["exclude_condition"], "exclude_condition", "Excludes cafe-like places."),
        row("음식점은 빼줘. 접근성 조건은 그대로 두고", ["exclude_condition"], "exclude_condition", "Excludes restaurant while preserving existing accessibility condition."),
        row("야외는 힘들어서 실내 쪽만 남겨줘", ["exclude_condition", "mobility_context"], "exclude_condition", "Excludes outdoor due mobility burden."),
        row("계단 많은 곳은 패스하고 평지 위주로", ["exclude_condition", "mobility_context"], "exclude_condition", "Excludes stair-heavy places."),
        row("아이 데리고 가는 일정이라 술집 느낌 나는 데는 빼줘", ["exclude_condition", "family_context"], "exclude_condition", "Family context plus exclusion."),
        row("붐비는 시장은 제외하고 유모차 동선 편한 곳", ["exclude_condition", "mobility_context"], "exclude_condition", "Excludes crowded market and asks stroller mobility."),
        row("초등학생이랑 같이 보기 좋은 역사 장소 있을까", ["family_context"], "family_context", "Child/family context without facility requirement."),
        row("애기 낮잠 시간 때문에 너무 오래 걷지 않는 코스면 좋겠어", ["family_context", "mobility_context"], "family_context", "Child context plus walking burden."),
        row("부모님이랑 아이가 같이 가도 무리 없는 곳 추천해줘", ["family_context", "mobility_context"], "family_context", "Family and mobility context."),
        row("유아차 대여가 아니라 그냥 애랑 쉬기 편한 곳이면 돼", ["family_context"], "family_context", "Family context, facility negated."),
        row("어린이 눈높이에서 지루하지 않은 전시 위주로", ["family_context"], "family_context", "Family/child context only."),
        row("아기랑 같이 먹기 편한 식당 근처 관광지도 괜찮아", ["family_context"], "family_context", "Family context."),
        row("기저귀 교환대는 없어도 되니 아이가 덜 피곤한 곳", ["soft_and", "family_context", "mobility_context"], "family_context", "Optional facility with family and walking comfort."),
        row("가족 사진 찍기 좋은데 너무 계단 많지 않은 곳", ["family_context", "mobility_context"], "family_context", "Family plus mobility constraint."),
        row("무릎이 안 좋아서 오르막 적은 곳 위주로", ["mobility_context"], "mobility_context", "Mobility limitation without named facility."),
        row("전동 스쿠터로 움직여도 동선이 끊기지 않는 곳", ["mobility_context"], "mobility_context", "Mobility context."),
        row("휠체어라는 단어보다 실제 이동 동선이 편한지가 중요해", ["mobility_context"], "mobility_context", "Mobility context, not literal facility requirement."),
        row("오래 서 있지 않아도 되는 관람지 있을까", ["mobility_context"], "mobility_context", "Mobility/endurance context."),
        row("계단 피해 다닐 수 있으면 좋겠어", ["mobility_context"], "mobility_context", "Mobility/stair avoidance."),
        row("어르신이 중간에 쉬기 쉬운 코스면 좋겠다", ["mobility_context"], "mobility_context", "Elder mobility context."),
        row("유모차로 사람 많은 데 비집고 다니긴 싫어", ["mobility_context"], "mobility_context", "Stroller mobility context."),
        row("발목 다친 사람이랑 가니 이동이 짧은 곳", ["mobility_context"], "mobility_context", "Temporary mobility limitation."),
        row("수어라는 단어가 들어간 이름 말고 실제 수어 안내 근거를 봐줘", ["specific_facility_required"], "specific_facility_required", "Requires actual sign-language evidence."),
        row("화장실 좋다는 후기 말고 장애인 화장실 표기가 있어야 해", ["specific_facility_required"], "specific_facility_required", "Requires explicit accessible-restroom evidence."),
        row("점자 느낌의 전시가 아니라 점자블록 편의정보가 필요해", ["specific_facility_required"], "specific_facility_required", "Requires literal tactile block evidence."),
        row("엘베 있으면 좋다가 아니라 엘리베이터 확인된 카드만", ["specific_facility_required"], "specific_facility_required", "Requires elevator evidence."),
        row("보조견 동반 가능 여부가 안 보이면 추천하지 마", ["specific_facility_required"], "specific_facility_required", "Requires guide-dog evidence."),
        row("수유실 문구가 있는지 원문 기준으로만 판단해줘", ["specific_facility_required"], "specific_facility_required", "Requires nursing-room text evidence."),
        row("주차 편하다는 말 말고 장애인 주차 가능 여부만", ["specific_facility_required"], "specific_facility_required", "Requires accessible parking evidence."),
        row("자막 지원이 확인되지 않으면 청각장애 동행자에게는 어려워", ["specific_facility_required"], "specific_facility_required", "Requires caption evidence."),
        row("수어지교 같은 이름의 장소 말고 사진 찍기 좋은 곳", [], "negative_near_miss", "Facility-looking word is not a facility request."),
        row("화장실 얘기하려는 게 아니라 물가 풍경이 좋은 곳", [], "negative_near_miss", "Facility word is explicitly negated."),
        row("주차 말고 주제가 독특한 박물관 추천해줘", [], "negative_near_miss", "Negated facility word should not become requirement."),
        row("점자라는 단어가 작품명에 있어도 접근성 조건은 아니야", [], "negative_near_miss", "Facility-like word is not requested."),
        row("아이돌 굿즈 파는 시장 말하는 거지 아이 동반 조건은 아냐", [], "negative_near_miss", "Child-looking token is not family context."),
        row("엘리베이터 피치가 높은 음악 얘기 아니고 조용한 전시", [], "negative_near_miss", "Facility-looking word is irrelevant."),
        row("보조견이라는 전시 제목이면 접근성으로 세지 말아줘", [], "negative_near_miss", "Facility term in title is not requirement."),
        row("가족이라는 이름의 식당 말고 그냥 관광지만", [], "negative_near_miss", "Family-like word not context."),
    ]
    for index, item in enumerate(rows, start=1):
        item["id"] = f"CTXBLIND{index:04d}"
    return rows


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        for item in rows:
            file.write(json.dumps(item, ensure_ascii=False, sort_keys=True) + "\n")


def main() -> None:
    rows = build_rows()
    write_jsonl(DEFAULT_OUTPUT, rows)
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
                "output": str(DEFAULT_OUTPUT.relative_to(PROJECT_ROOT)),
                "rows": len(rows),
                "label_counts": dict(sorted(label_counts.items())),
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
