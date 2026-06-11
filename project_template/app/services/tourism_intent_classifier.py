from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
import json
import math
from pathlib import Path
import re
from typing import Any

from app.core.config import PROJECT_ROOT


DEFAULT_INTENT_MODEL_PATH = PROJECT_ROOT / "data" / "processed" / "tourism_intent_classifier.json"


@dataclass(frozen=True)
class TourismIntentPrediction:
    intent: str | None
    confidence: float
    scores: dict[str, float]


class TourismIntentClassifier:
    def __init__(self, model_path: Path | None = None):
        self.model_path = model_path or DEFAULT_INTENT_MODEL_PATH
        self.model: dict[str, Any] | None = self._load_model(self.model_path)

    def predict(self, text: str) -> TourismIntentPrediction:
        rule_prediction = self._rule_prediction(text)
        if rule_prediction:
            return rule_prediction
        if not self.model:
            return TourismIntentPrediction(intent=None, confidence=0.0, scores={})

        labels: list[str] = list(self.model.get("labels") or [])
        priors: dict[str, float] = dict(self.model.get("priors") or {})
        token_log_probs: dict[str, dict[str, float]] = dict(self.model.get("token_log_probs") or {})
        unknown_log_probs: dict[str, float] = dict(self.model.get("unknown_log_probs") or {})
        tokens = self._tokens(text)
        if not labels or not tokens:
            return TourismIntentPrediction(intent=None, confidence=0.0, scores={})

        log_scores = {}
        for label in labels:
            value = float(priors.get(label, -100.0))
            label_probs = token_log_probs.get(label, {})
            unknown = float(unknown_log_probs.get(label, -20.0))
            for token in tokens:
                value += float(label_probs.get(token, unknown))
            log_scores[label] = value

        probabilities = self._softmax(log_scores)
        intent, confidence = max(probabilities.items(), key=lambda item: item[1])
        return TourismIntentPrediction(intent=intent, confidence=round(confidence, 4), scores=probabilities)

    @staticmethod
    def _load_model(path: Path) -> dict[str, Any] | None:
        if not path.exists():
            return None
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        return payload if isinstance(payload, dict) else None

    @staticmethod
    def _rule_prediction(text: str) -> TourismIntentPrediction | None:
        normalized = " ".join(text.strip().split())
        if not normalized:
            return None
        if TourismIntentClassifier._looks_like_source_request(normalized):
            return TourismIntentPrediction(intent="ask_source", confidence=0.99, scores={"ask_source": 0.99})
        if TourismIntentClassifier._looks_like_region_change(normalized):
            return TourismIntentPrediction(intent="change_region", confidence=0.99, scores={"change_region": 0.99})
        if TourismIntentClassifier._looks_like_ambiguous_region_request(normalized):
            return TourismIntentPrediction(intent="clarify_region", confidence=0.98, scores={"clarify_region": 0.98})
        if TourismIntentClassifier._looks_like_show_more(normalized):
            return TourismIntentPrediction(intent="show_more", confidence=0.99, scores={"show_more": 0.99})
        if TourismIntentClassifier._looks_like_live_topup(normalized):
            return TourismIntentPrediction(intent="live_topup", confidence=0.99, scores={"live_topup": 0.99})
        if TourismIntentClassifier._looks_like_condition_replacement(normalized):
            return TourismIntentPrediction(intent="replace_condition", confidence=0.99, scores={"replace_condition": 0.99})
        if TourismIntentClassifier._looks_like_exclude_preference(normalized):
            return TourismIntentPrediction(intent="exclude_preference", confidence=0.98, scores={"exclude_preference": 0.98})
        if TourismIntentClassifier._looks_like_add_condition(normalized):
            return TourismIntentPrediction(intent="add_condition", confidence=0.98, scores={"add_condition": 0.98})
        if TourismIntentClassifier._looks_like_unsupported_request(normalized):
            return TourismIntentPrediction(intent="unsupported_request", confidence=0.99, scores={"unsupported_request": 0.99})
        if TourismIntentClassifier._looks_like_narrow_region(normalized):
            return TourismIntentPrediction(intent="narrow_region", confidence=0.98, scores={"narrow_region": 0.98})
        if TourismIntentClassifier._looks_like_recommend_request(normalized):
            return TourismIntentPrediction(intent="recommend_places", confidence=0.96, scores={"recommend_places": 0.96})
        rules = [
            (
                "show_more",
                ["더 보기", "더보기", "더 보여", "더 많이", "나머지", "전체", "전부", "20곳", "계속 보여", "목록 더"],
            ),
            (
                "live_topup",
                ["최신", "새로 검색", "최근 기준", "현재 기준", "업데이트", "다시 조회", "추가로 찾아"],
            ),
            (
                "ask_source",
                [
                    "출처",
                    "근거",
                    "원자료",
                    "어떤 자료",
                    "어디 자료",
                    "어디서 보고",
                    "어디서 나온",
                    "어떤 기준",
                    "몇 년도 데이터",
                    "원본 링크",
                    "참고한 사이트",
                    "참고한 문서",
                    "어떤 기관",
                    "확인할 수 있는 곳",
                    "사실인지 확인",
                ],
            ),
            (
                "unsupported_request",
                [
                    "실시간",
                    "혼잡",
                    "대기시간",
                    "응급실",
                    "병원",
                    "약국",
                    "가격",
                    "요금",
                    "입장료",
                    "재고",
                    "영업 중",
                    "빈자리",
                    "택시비",
                    "날씨",
                    "예약",
                    "취소",
                    "환불",
                    "환율",
                    "환전",
                    "결제",
                    "체크인",
                    "체크아웃",
                    "객실",
                    "침구",
                    "입실",
                    "퇴실",
                    "룸",
                    "전화번호",
                    "번호 안내",
                    "렌터카",
                    "버스요금",
                    "버스 요금",
                    "버스 예약",
                    "가는 버스",
                    "버스로 갈",
                    "버스로 가",
                    "몇 번 버스",
                    "버스 타면",
                    "갈아타",
                    "노선",
                    "얼마나 걸리",
                    "가는 방법",
                    "할인",
                ],
            ),
        ]
        for intent, keywords in rules:
            if any(keyword in normalized for keyword in keywords):
                return TourismIntentPrediction(intent=intent, confidence=1.0, scores={intent: 1.0})
        if any(keyword in normalized for keyword in ["말고", "빼고", "제외", "아니고", "대신", "됐고", "패스"]):
            return TourismIntentPrediction(intent="exclude_preference", confidence=0.98, scores={"exclude_preference": 0.98})
        if TourismIntentClassifier._looks_like_recommend_request(normalized):
            return TourismIntentPrediction(intent="recommend_places", confidence=0.96, scores={"recommend_places": 0.96})
        if any(keyword in normalized for keyword in ["있는 곳", "있는 곳만", "가능한 곳", "확인되는 곳", "위주로", "접근 가능한", "걷기 편한"]):
            return TourismIntentPrediction(intent="add_condition", confidence=0.95, scores={"add_condition": 0.95})
        return None

    @staticmethod
    def _looks_like_region_switch(text: str) -> bool:
        matched_spans: list[tuple[int, int]] = []
        for region in sorted(TourismIntentClassifier._region_terms(), key=len, reverse=True):
            for match in re.finditer(re.escape(region), text):
                span = match.span()
                if any(not (span[1] <= existing[0] or span[0] >= existing[1]) for existing in matched_spans):
                    continue
                matched_spans.append(span)
                break
        return len(matched_spans) >= 2

    @staticmethod
    def _region_terms() -> list[str]:
        return [
            "서울",
            "부산",
            "대구",
            "인천",
            "광주",
            "대전",
            "울산",
            "세종",
            "제주",
            "제주도",
            "제주시",
            "서귀포",
            "서귀포시",
            "경기",
            "경기도",
            "강원",
            "강원도",
            "충북",
            "충청북도",
            "충남",
            "충청남도",
            "충청도",
            "전북",
            "전라북도",
            "전남",
            "전라남도",
            "전라도",
            "경북",
            "경상북도",
            "경남",
            "경상남도",
            "경상도",
            "강릉",
            "속초",
            "전주",
            "군산",
            "경주",
            "순천",
            "목포",
            "여수",
            "포항",
            "고성군",
            "강서구",
            "중구",
            "동구",
            "서구",
            "남구",
            "북구",
            "강남구",
            "해운대구",
            "유성구",
            "수성구",
            "종로구",
            "용산구",
            "영등포구",
            "기장군",
            "수성구",
            "수원",
            "춘천",
            "안동",
            "통영",
            "남해",
            "양양",
            "여주",
            "정선",
            "청주",
        ]

    @staticmethod
    def _condition_terms() -> list[str]:
        return [
            "휠체어",
            "전동 스쿠터",
            "유모차",
            "유아차",
            "아이",
            "어르신",
            "노약자",
            "고령층",
            "주차",
            "화장실",
            "엘리베이터",
            "승강기",
            "경사로",
            "점자",
            "수어",
            "수화",
            "자막",
            "보조견",
            "안내견",
            "수유실",
            "기저귀",
            "시각장애",
            "청각장애",
            "대중교통",
            "자가용",
            "렌터카",
            "택시",
            "기차",
            "실내",
            "야외",
            "산책",
            "박물관",
            "미술관",
            "시장",
            "쇼핑몰",
            "숙소",
            "호텔",
            "객실",
            "펜션",
            "게스트하우스",
            "식당",
            "카페",
            "한식",
            "양식",
            "해변",
            "계곡",
            "야경",
            "낮",
            "주간",
            "야간",
            "휴식",
            "액티비티",
            "체험",
            "관광지",
            "공원",
            "자연",
            "경관",
            "역사",
            "유적지",
            "투어",
            "가이드",
            "자유 여행",
            "도보",
            "오전",
            "오후",
            "무료",
            "유료",
            "입장",
            "유아용",
            "카시트",
            "아기 의자",
            "조용",
            "활기",
        ]

    @staticmethod
    def _looks_like_source_request(text: str) -> bool:
        source_terms = ["출처", "근거", "원자료", "어떤 자료", "어디 자료", "자료 기준", "확인 자료", "자료명"]
        if not any(term in text for term in source_terms):
            return False
        if any(term in text for term in ["최신 자료", "최근 자료", "현재 자료", "새 자료"]):
            return False
        return any(term in text for term in ["뭐", "어디", "보여", "알려", "남겨", "확인", "같이", "기준"])

    @staticmethod
    def _looks_like_unsupported_request(text: str) -> bool:
        unsupported_terms = [
            "혼잡",
            "대기시간",
            "응급실",
            "병원",
            "약국",
            "가격",
            "요금",
            "입장료",
            "재고",
            "영업 중",
            "영업 여부",
            "휴무",
            "빈자리",
            "택시비",
            "날씨",
            "예약",
            "취소",
            "환불",
            "환율",
            "환전",
            "결제",
            "체크인",
            "체크아웃",
            "객실",
            "입실",
            "퇴실",
            "전화번호",
            "번호 안내",
            "렌터카",
            "버스요금",
            "버스 요금",
            "버스 예약",
            "버스 번호",
            "버스 소요시간",
            "가는 버스",
            "버스로 갈",
            "버스로 가",
            "몇 번 버스",
            "버스 타면",
            "갈아타",
            "노선",
            "얼마나 걸리",
            "가는 방법",
            "할인",
            "시간표",
            "정형외과",
            "편의점",
            "예매",
            "티켓",
            "해열제",
            "소아과",
            "공연 표",
            "몇 시",
            "닫아",
            "닫나요",
            "웨이팅",
            "줄 길",
            "짐 맡",
        ]
        if "실시간" in text and any(term in text for term in ["혼잡", "대기", "좌석", "빈자리", "주차장"]):
            return True
        return any(term in text for term in unsupported_terms)

    @staticmethod
    def _looks_like_show_more(text: str) -> bool:
        if any(term in text for term in ["출처", "근거", "원자료", "자료 기준"]):
            return False
        if any(term in text for term in ["최신", "최근", "오늘", "새로 조회", "새로 검색", "새로 확인"]):
            return False
        if any(term in text for term in ["빼줘", "빼고", "제외", "사양", "안 갈", "안 가고", "추천 안", "됐어"]):
            return False
        more_terms = [
            "더 보기",
            "더보기",
            "더 보여",
            "더 꺼내",
            "더 이어",
            "더 줘",
            "나머지",
            "전체",
            "전부",
            "계속 보여",
            "목록 더",
            "다음 것도",
            "추가 후보",
            "다른 후보",
            "다른 곳",
            "다른 추천",
            "다른 옵션",
            "다른 선택지",
            "있는 만큼",
            "가능한 만큼",
            "남은 정보",
            "다 보여",
            "다음 추천",
            "다음 페이지",
            "더 긴 리스트",
            "더 많은",
            "더 볼",
        ]
        if any(term in text for term in more_terms):
            return True
        return bool(re.search(r"(3곳|5곳|10곳|몇 군데).{0,8}더", text))

    @staticmethod
    def _looks_like_live_topup(text: str) -> bool:
        if any(term in text for term in ["출처", "근거", "원자료", "자료 기준"]):
            return False
        if TourismIntentClassifier._looks_like_add_condition(text):
            return False
        if "방금 결과" in text and TourismIntentClassifier._looks_like_recommend_request(text):
            return False
        fresh_terms = [
            "최신",
            "최근",
            "오늘",
            "현재",
            "방금",
            "새로",
            "새 자료",
            "새롭게",
            "따끈따끈",
            "업뎃",
            "업데이트",
            "바뀐",
            "새로고침",
            "실시간 정보",
            "지금도 맞",
        ]
        topup_terms = ["검색", "조회", "확인", "찾아", "보강", "추가", "반영", "업데이트"]
        if any(fresh in text for fresh in fresh_terms) and any(topup in text for topup in topup_terms):
            return True
        if any(term in text for term in ["다시 확인", "방금 나온", "최근 정보", "바뀐 거", "새로고침", "업뎃된"]):
            return True
        return bool(
            re.search(
                r"(저장된|가지고 있는|카드가 적|결과가 적|후보가 적).{0,12}(새로|추가|더|보강|조회|확인|찾아)",
                text,
            )
        )

    @staticmethod
    def _looks_like_add_condition(text: str) -> bool:
        if not any(term in text for term in TourismIntentClassifier._condition_terms()):
            return False
        region_pattern = "|".join(re.escape(region) for region in TourismIntentClassifier._region_terms())
        has_region = bool(re.search(rf"({region_pattern})", text))
        has_followup_context = any(term in text for term in ["조건", "추가", "까지", "도 봐", "도 가능", "필터"])
        if has_region and not has_followup_context:
            return False
        comparison_text = text.replace("방금 결과 말고", "")
        if TourismIntentClassifier._looks_like_exclude_preference(comparison_text):
            return False
        if any(marker in comparison_text for marker in ["말고", "대신", "보다", "취소하고", "아니고", "빼고"]):
            return False
        return bool(
            re.search(
                r"(조건을 추가|조건 추가|까지 봐|도 봐|도 되는|도 가능|동반 가능|확인되는|되는 곳|있는 곳|중심으로|위주로|추려|편의시설|이동 편리|갈 만한|갈 곳|괜찮은 곳|좋은 길|설치된|넓은 곳)",
                text,
            )
        )

    @staticmethod
    def _looks_like_exclude_preference(text: str) -> bool:
        if TourismIntentClassifier._looks_like_region_switch(text):
            return False
        if TourismIntentClassifier._looks_like_condition_replacement(text):
            return False
        return bool(
            re.search(
                r"(빼고|빼줘|제외|사양|패스|안 갈래|안 가고|안 가려고|안 가고 싶|추천 안|안 해줘도|됐어|필요 없어)",
                text,
            )
        )

    @staticmethod
    def _looks_like_recommend_request(text: str) -> bool:
        region_terms = [
            "서울",
            "부산",
            "대구",
            "인천",
            "광주광역시",
            "대전",
            "울산",
            "세종",
            "제주",
            "제주시",
            "서귀포",
            "강릉",
            "속초",
            "전주",
            "창원",
            "경기",
            "강원",
            "경남",
            "경북",
            "전남",
            "전북",
            "충남",
            "충북",
            "광주",
        ]
        request_terms = ["추천", "찾아", "관광지", "관광", "여행지", "볼거리", "갈 곳", "갈만한 곳", "가볼만한 곳", "여행 정보"]
        qualified_ambiguous = re.search(
            r"(서울|부산|대구|인천|광주|대전|울산|강원|경남|경북|전남|전북|제주|청주).{0,8}(중구|동구|서구|남구|북구|강서구|고성군)",
            text,
        )
        return (any(region in text for region in region_terms) or bool(qualified_ambiguous)) and any(term in text for term in request_terms)

    @staticmethod
    def _looks_like_region_change(text: str) -> bool:
        if any(marker in text for marker in ["중에서도", "아닌 건 빼고"]):
            return False
        if re.search(r"(지역|장소|도시|시군구).{0,8}(바꾸|변경|다시|고르|선택)", text):
            return True
        if re.search(r"(그|이|저|전|전에 말한|아까|방금)?\s*(지역|장소|도시|시군구)?.{0,8}말고\s*(다른|딴|새로운)\s*(데|곳|지역|장소|도시|시군구)", text):
            return True
        if re.search(r"(전|전에 말한|아까|방금)\s*(곳|지역|장소)\s*말고\s*.+", text):
            return True
        if re.search(r"(다른|딴|새로운)\s*(지역|장소|도시|시군구)", text):
            return True
        qualified_count = len(
            re.findall(
                r"(서울|부산|대구|인천|광주|대전|울산|강원|경남|경북|전남|전북|제주|청주).{0,4}(중구|동구|서구|남구|북구|강서구|고성군)",
                text,
            )
        )
        if qualified_count == 1 and re.search(r"(시장|식당|카페|숙소|호텔|쇼핑몰|먹자골목)\s*말고\s*관광지", text):
            return False
        if (
            any(marker in text for marker in ["말고", "아니고", "대신", "됐고", "갈아탈"])
            and TourismIntentClassifier._looks_like_region_switch(text)
            and (qualified_count != 1 or re.search(r"(서울|부산|대구|인천|광주|대전|울산|강원|경남|경북|전남|전북|제주|청주).{5,}", text))
        ):
            return True
        region_pattern = "|".join(re.escape(region) for region in TourismIntentClassifier._region_terms())
        if re.search(rf"({region_pattern})\s*(으로|로|쪽으로)\s*(바꿔|변경|갈아탈|다시|검색|찾아|알려|보여|가보자|갈래)", text):
            return True
        if re.search(rf"({region_pattern})에서\s*(다른|딴)\s*(곳|지역|장소)(으로)?\s*(옮겨|바꿔|갈아)", text):
            return True
        if re.search(rf"({region_pattern})\s*(지역|여행|정보|후보|쪽)(은|는|도|으로|으로는|요|이요)?", text) and any(
            marker in text for marker in ["이번엔", "이번에는", "다음엔", "다음에는", "지금 여기 말고", "방금 결과 말고", "아까 거에서"]
        ):
            return True
        if re.search(r"(지역을|이번엔|이번에는|다음엔|다음에는).{0,16}(바꿔|변경|선택|가볼|가고|볼래|가보자|가고 싶)", text):
            return True
        return False

    @staticmethod
    def _looks_like_condition_replacement(text: str) -> bool:
        comparison_text = text.replace("방금 결과 말고", "")
        if re.search(r"(가지고 있는 것|저장된 것|나온 것|결과).{0,8}말고.{0,8}(더|다시|새로).{0,8}(찾아|검색|조회)", comparison_text):
            return False
        if re.search(r"(말고|빼고)\s*관광지(로만|만)", comparison_text):
            return False
        if re.search(r"빼고.{0,8}(추천|알려|보여|찾아)", comparison_text) and "으로" not in comparison_text:
            return False
        replacement_markers = ["말고", "대신", "보다", "취소하고", "바꿔", "변경", "아니고"]
        if not any(marker in comparison_text for marker in replacement_markers):
            if not re.search(r"(.+는|조건|기준).{0,8}빼고.+(되는 곳|으로|위주|기준)", comparison_text):
                return False
        if TourismIntentClassifier._looks_like_region_switch(text):
            return False
        terms = TourismIntentClassifier._condition_terms()
        if sum(1 for term in terms if term in comparison_text) >= 2:
            return True
        if re.search(r".+(바꿔|변경|취소하고).+", comparison_text):
            return True
        if re.search(r".+(말고|대신|보다|아니고).+(쪽|위주|기준|중심|코스|투어|시설|자연|경관|공원|으로|는요|은요|없나요|바꿔|변경|되는 곳|좋은 데|좋은 곳|같은 데|같은 곳)", comparison_text):
            return True
        return False

    @staticmethod
    def _looks_like_narrow_region(text: str) -> bool:
        if any(keyword in text for keyword in ["좁혀", "쪽만", "지역만", "안에서만", "카드만", "만 보여", "범위"]):
            return True
        narrow_markers = ["쪽", "근처", "주변", "부근", "위주", "중심", "만", "내", "시내"]
        subregions = [
            "강남구",
            "해운대구",
            "분당구",
            "진해구",
            "서귀포시",
            "송파구",
            "수영구",
            "종로구",
            "용산구",
            "영등포구",
            "기장군",
            "유성구",
            "수성구",
            "팔달",
            "명동",
            "잠실",
            "종로",
            "용산",
            "해운대",
            "서면",
            "남포동",
            "광안리",
            "애월",
            "성산",
            "중문",
            "한림",
            "어진동",
            "성수동",
            "안목해변",
            "불국사",
            "고창읍성",
            "가야테마파크",
            "독일마을",
            "자갈치",
            "부산대",
            "부산역",
            "백제문화단지",
            "유달산",
            "태화강",
            "하회마을",
            "동피랑",
            "홍대입구",
        ]
        ambiguous = ["중구", "동구", "서구", "남구", "북구", "강서구", "고성군"]
        place_markers = ["쪽", "근처", "주변", "부근", "부근만", "인근"]
        if re.search(r"(아까 지역 중|방금 목록에서|아까 말한 데서).{0,20}(위주|만|후보|카드)", text):
            return True
        if re.search(r"(서울|부산|대구|인천|광주|대전|울산|강원|경남|경북|전남|전북|제주|청주).{0,8}(중구|동구|서구|남구|북구|강서구|고성군).{0,8}(후보만|카드만|위주로만|쪽만|만 다시|만요|만$)", text):
            return True
        if any(region in text for region in subregions) and any(marker in text for marker in place_markers):
            return True
        if any(region in text for region in subregions) and (
            any(marker in text for marker in ["좁혀", "쪽만", "지역만", "안에서만", "카드만", "만 보여", "범위", "까지 줄여", "남겨"])
            or re.search(r"(쪽으로만|안으로|안에서|후보로 줄|만 남)", text)
        ):
            return True
        qualified_ambiguous = re.search(
            r"(서울|부산|대구|인천|광주|대전|울산|제주|청주|경기|강원|경남|경북|전남|전북).{0,8}(중구|동구|서구|남구|북구|강서구|고성군)",
            text,
        )
        if qualified_ambiguous and any(marker in text for marker in place_markers):
            return True
        if qualified_ambiguous and (
            any(marker in text for marker in ["좁혀", "쪽만", "지역만", "안에서만", "카드만", "만 보여", "범위", "까지 줄여", "남겨"])
            or re.search(r"(쪽으로만|안으로|안에서|후보로 줄|만 남)", text)
        ):
            return True
        return False

    @staticmethod
    def _looks_like_ambiguous_region_request(text: str) -> bool:
        ambiguous = ["중구", "동구", "서구", "남구", "북구", "강서구", "고성군"]
        if not any(region in text for region in ambiguous):
            return False
        if re.search(r"(중구|동구|서구|남구|북구|강서구|고성군).{0,20}(어디|어느|모르겠|애매|너무 많|둘 다|여러)", text):
            return True
        if re.search(r"(중구|동구|서구|남구|북구|강서구|고성군)만 말(하면|했는데).*(어디|지역|애매|찾아줄 수)", text):
            return True
        qualifiers = ["서울", "부산", "대구", "인천", "광주", "대전", "울산", "강원", "경남", "경북", "전남", "전북", "제주", "청주"]
        if "인지" in text and sum(1 for qualifier in qualifiers if qualifier in text) >= 2:
            return True
        if any(qualifier in text for qualifier in qualifiers):
            return False
        return bool(
            re.search(
                r"(중구|동구|서구|남구|북구|강서구|고성군)(?=$|[\s에에서은는이가쪽관여맛볼숙카공유장시])",
                text,
            )
        )

    @staticmethod
    def _tokens(text: str) -> list[str]:
        normalized = " ".join(text.lower().split())
        tokens = []
        for size in (2, 3, 4):
            tokens.extend(normalized[index : index + size] for index in range(max(len(normalized) - size + 1, 0)))
        tokens.extend(part for part in normalized.split() if part)
        return tokens

    @staticmethod
    def _softmax(log_scores: dict[str, float]) -> dict[str, float]:
        max_score = max(log_scores.values())
        exp_scores = {label: math.exp(score - max_score) for label, score in log_scores.items()}
        total = sum(exp_scores.values()) or 1.0
        return {label: round(score / total, 4) for label, score in exp_scores.items()}


def train_intent_model(rows: list[dict[str, str]]) -> dict[str, Any]:
    by_label: dict[str, Counter[str]] = defaultdict(Counter)
    label_counts: Counter[str] = Counter()
    vocabulary: set[str] = set()

    for row in rows:
        text = str(row.get("text") or "").strip()
        label = str(row.get("intent") or "").strip()
        if not text or not label:
            continue
        tokens = TourismIntentClassifier._tokens(text)
        by_label[label].update(tokens)
        label_counts[label] += 1
        vocabulary.update(tokens)

    labels = sorted(label_counts)
    vocabulary_size = max(len(vocabulary), 1)
    total_rows = sum(label_counts.values()) or 1
    priors = {label: math.log(label_counts[label] / total_rows) for label in labels}
    token_log_probs = {}
    unknown_log_probs = {}

    for label in labels:
        token_counts = by_label[label]
        denominator = sum(token_counts.values()) + vocabulary_size
        token_log_probs[label] = {
            token: math.log((count + 1) / denominator)
            for token, count in token_counts.items()
        }
        unknown_log_probs[label] = math.log(1 / denominator)

    return {
        "model_type": "char_ngram_multinomial_nb",
        "version": 1,
        "labels": labels,
        "row_count": total_rows,
        "vocabulary_size": vocabulary_size,
        "priors": priors,
        "token_log_probs": token_log_probs,
        "unknown_log_probs": unknown_log_probs,
    }
