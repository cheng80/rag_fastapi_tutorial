from __future__ import annotations

from pathlib import Path
import json
import logging
import re

from app.core.config import PROJECT_ROOT, get_settings
from app.services.korean_external_corrector import DEFAULT_PROTECTED_TERMS, ExternalCorrectionResult, ExternalKoreanCorrector
from app.services.tourism_condition_transformer import TourismConditionTransformer
from app.services.tourism_context_classifier import TourismContextClassifier
from app.services.tourism_intent_classifier import TourismIntentClassifier
from app.services.korean_query_normalizer import KoreanQueryNormalizer, NormalizedQuery


AREA_CODES = {
    "서울": "1",
    "인천": "2",
    "대전": "3",
    "대구": "4",
    "광주": "5",
    "부산": "6",
    "울산": "7",
    "세종": "8",
    "경기": "31",
    "강원": "32",
    "강릉": "32",
    "충북": "33",
    "충남": "34",
    "경북": "35",
    "경남": "36",
    "전북": "37",
    "전남": "38",
    "제주": "39",
}

SIGUNGU_CODES = {
    "강릉": "1",
}

DEFAULT_AREA_CODE_CACHE_PATH = PROJECT_ROOT / "data" / "processed" / "tour_area_codes.json"
DEFAULT_ADMIN_REGION_ALIAS_PATH = PROJECT_ROOT / "data" / "processed" / "admin_region_aliases.json"

CONDITION_KEYWORDS = {
    "휠체어": [
        "휠체어",
        "무장애",
        "접근성",
        "이동약자",
        "베리어프리",
        "휠챠",
        "바퀴 의자",
        "바퀴의자",
        "바퀴 달린 의자",
        "걸음이 불편해도",
        "계단 없이 갈 수",
        "턱이 적은",
    ],
    "유모차": ["유모차", "유아차", "아기차", "애기차", "애기", "아기", "영유아", "영아", "유아", "아이", "어린이", "가족", "수유", "수유실", "기저귀"],
    "고령자": [
        "고령자",
        "어르신",
        "노인",
        "할머니",
        "할아버지",
        "부모님",
        "무릎 불편",
        "무릎불편",
        "많이 걷기 어려",
        "많이안걷",
        "오래 안 걷",
        "오래안걷",
        "걷기 어려",
        "오래 걷기 힘든 분",
        "무리 없는",
        "쉬어 갈 곳",
    ],
    "주차": ["주차", "주챠", "주차ㅏ", "주자창", "차대기", "차 댈", "차댈곳", "차 댈 곳", "차 대는 곳", "차 세우", "장애인 주차"],
    "화장실": ["화장실", "장애인 화장실", "장실", "장애인 장실"],
    "접근로": [
        "접근로",
        "출입통로",
        "출입 통로",
        "동선",
        "경사로",
        "턱 없음",
        "턱없음",
        "턱이 없어",
        "입구에 턱이 없는",
        "유모차 바퀴가 걸리지",
        "무단차",
        "평탄한 길",
        "평탄한길",
        "길이 평평한",
        "계단",
        "걷기 힘",
        "걷기 어려",
    ],
    "대중교통": ["대중교통", "버스", "지하철"],
    "엘리베이터": [
        "엘리베이터",
        "엘레베터",
        "승강기",
        "휠체어 리프트",
        "장애인 리프트",
        "승강 리프트",
        "승강용 리프트",
        "계단 리프트",
        "지하철 리프트",
        "공공기관 리프트",
        "공공시설 리프트",
        "관광시설 리프트",
        "건물 리프트",
        "시설 리프트",
        "층 이동이 편한",
        "위아래 이동이 쉬운",
        "계단 말고 올라갈",
    ],
    "보조견": ["보조견", "안내견"],
    "시각장애": [
        "시각장애",
        "시각장애인 안내",
        "점자",
        "점자블록",
        "촉지도",
        "촉지 안내도",
        "촉지안내도",
        "촉지 안내판",
        "촉지안내판",
        "촉지판",
        "음성안내",
        "음성 안내",
        "소리 안내",
        "손으로 만져 확인할 안내",
        "오디오가이드",
    ],
    "청각장애": [
        "청각장애",
        "수어",
        "수화",
        "자막",
        "문자안내",
        "문자 안내",
        "영상안내",
        "영상 안내",
        "영상에 글자 안내",
        "소리 없이도 안내를 볼 수",
    ],
}

EXPANSION_KEYWORDS = [
    "전체로",
    "전체까지",
    "전체 범위",
    "범위 넓혀",
    "범위를 넓혀",
    "넓혀서",
    "넓혀 줘",
    "넓혀줘",
    "상위 지역",
]
CONDITIONAL_EXPANSION_KEYWORDS = [
    "부족하면",
    "부족할 때",
    "부족할때",
    "모자라면",
    "모자를 때",
    "모자를때",
    "적으면",
    "없으면",
    "안 나오면",
    "안나오면",
]
FEATURE_KEYWORDS = {
    "바닷가": ["바닷가", "바다", "해변", "해수욕장", "해안", "해변가"],
}
PREFERENCE_KEYWORDS = {
    "실내": ["실내", "비 와도", "비오는", "비 오는", "더운 날", "추운 날"],
    "박물관_전시": ["박물관", "전시관", "전시", "미술관", "체험관"],
    "시장_먹거리": ["시장", "먹거리", "맛집", "음식", "식당", "먹자골목"],
    "공원_산책": ["공원", "산책", "산책로", "숲길", "정원", "둘레길"],
    "숙박": ["호텔", "숙박", "리조트", "펜션", "캠핑장", "야영장"],
    "카페_음식점": ["카페", "식당", "음식점", "맛집", "레스토랑"],
    "조용한": ["조용", "한적", "붐비지", "덜 붐비"],
}
NEGATION_NEARBY_KEYWORDS = ["말고", "빼고", "제외", "아닌", "말고는", "말고요", "취소", "패스"]
UNSUPPORTED_INTENT_KEYWORDS = {
    "wheelchair_rental_price": ["휠체어 대여", "대여 가격", "가격이 제일 싼", "제일 싼 곳", "최저가"],
    "medical_lookup": ["병원", "약국", "응급실", "응급의료"],
    "transport_booking": ["리프트 차량", "예약 업체", "업체 연결", "예약 가능한 업체", "예약 가능한 시간", "예약 가능", "예약 시간"],
    "realtime_crowd": ["실시간", "지금 제일 안 붐비", "혼잡도", "빈자리"],
    "price_sort": ["입장료", "가격순", "가장 싼", "싸고"],
    "itinerary_planning": ["하루 코스", "시간표", "이동시간", "이동 시간", "코스 시간표", "소요시간", "소요 시간", "버스 번호", "몇 번 버스", "버스 노선"],
    "current_operation": ["영업 중", "영업중", "운영 중", "운영중", "오늘 영업", "오늘 운영", "휴무"],
    "external_contact": ["렌터카", "전화번호", "전화 번호", "업체 번호"],
    "weather_based": ["날씨", "비 예보", "기온", "폭염", "한파"],
    "subway_direct": ["지하철역 바로 연결", "지하철 바로 연결"],
}
LEGACY_REGION_ALIASES = {
    "청원군": {
        "replacement_region": "청주시",
        "notice": "청원군은 현재 청주시 기준으로 안내드릴게요.",
    },
    "충청북도 청원군": {
        "replacement_region": "청주시",
        "notice": "청원군은 현재 청주시 기준으로 안내드릴게요.",
    },
    "충북 청원군": {
        "replacement_region": "청주시",
        "notice": "청원군은 현재 청주시 기준으로 안내드릴게요.",
    },
    "마산시": {
        "replacement_region": "창원시",
        "notice": "마산시는 현재 창원시 기준으로 안내드릴게요.",
    },
    "경상남도 마산시": {
        "replacement_region": "창원시",
        "notice": "마산시는 현재 창원시 기준으로 안내드릴게요.",
    },
    "경남 마산시": {
        "replacement_region": "창원시",
        "notice": "마산시는 현재 창원시 기준으로 안내드릴게요.",
    },
    "진해시": {
        "replacement_region": "창원시",
        "notice": "진해시는 현재 창원시 기준으로 안내드릴게요.",
    },
    "경상남도 진해시": {
        "replacement_region": "창원시",
        "notice": "진해시는 현재 창원시 기준으로 안내드릴게요.",
    },
    "경남 진해시": {
        "replacement_region": "창원시",
        "notice": "진해시는 현재 창원시 기준으로 안내드릴게요.",
    },
    "남제주군": {
        "replacement_region": "서귀포시",
        "notice": "남제주군은 현재 서귀포시 기준으로 안내드릴게요.",
    },
    "제주특별자치도 남제주군": {
        "replacement_region": "서귀포시",
        "notice": "남제주군은 현재 서귀포시 기준으로 안내드릴게요.",
    },
    "제주도 남제주군": {
        "replacement_region": "서귀포시",
        "notice": "남제주군은 현재 서귀포시 기준으로 안내드릴게요.",
    },
    "북제주군": {
        "replacement_region": "제주시",
        "notice": "북제주군은 현재 제주시 기준으로 안내드릴게요.",
    },
    "제주특별자치도 북제주군": {
        "replacement_region": "제주시",
        "notice": "북제주군은 현재 제주시 기준으로 안내드릴게요.",
    },
    "제주도 북제주군": {
        "replacement_region": "제주시",
        "notice": "북제주군은 현재 제주시 기준으로 안내드릴게요.",
    },
}
logger = logging.getLogger(__name__)


class TourismQueryService:
    def __init__(
        self,
        area_code_cache_path: Path | None = None,
        admin_region_alias_path: Path | None = None,
        intent_classifier: TourismIntentClassifier | None = None,
        context_classifier: TourismContextClassifier | None = None,
        external_corrector: ExternalKoreanCorrector | None = None,
        enable_external_correction: bool | None = None,
        condition_transformer: TourismConditionTransformer | None = None,
    ):
        self.area_code_cache_path = area_code_cache_path or DEFAULT_AREA_CODE_CACHE_PATH
        self.admin_region_alias_path = admin_region_alias_path or DEFAULT_ADMIN_REGION_ALIAS_PATH
        self.intent_classifier = intent_classifier or TourismIntentClassifier()
        self.context_classifier = context_classifier or TourismContextClassifier()
        self.query_normalizer = KoreanQueryNormalizer()
        settings = get_settings()
        self.settings = settings
        self.external_correction_enabled = (
            settings.tourism_korean_correction_enabled if enable_external_correction is None else enable_external_correction
        )
        self.external_corrector = external_corrector or (
            ExternalKoreanCorrector(settings) if self.external_correction_enabled else None
        )
        self.condition_transformer = condition_transformer or (
            TourismConditionTransformer(settings, labels=list(CONDITION_KEYWORDS))
            if settings.tourism_condition_transformer_enabled
            else None
        )
        self.cache_status = "loaded"
        self.cache_warning: str | None = None
        self.ambiguous_region_aliases: dict[str, list[dict[str, str | None]]] = {}
        self.region_index = self._load_region_index()

    def extract(self, message: str) -> dict[str, list[str] | str | None]:
        region_names = list(self.region_index) + list(AREA_CODES)
        normalization = self.query_normalizer.normalize(message, region_names=region_names)
        normalized_message = normalization.normalized_text
        rewrite_message = normalization.rewrite_text
        external_correction = self._external_correction(message, region_names, normalization)
        external_normalization = (
            self.query_normalizer.normalize(external_correction.corrected_text, region_names=region_names)
            if external_correction and external_correction.accepted
            else None
        )
        interpretation_messages = list(
            dict.fromkeys(
                [
                    message,
                    normalized_message,
                    rewrite_message,
                    external_correction.corrected_text if external_correction and external_correction.accepted else "",
                    external_normalization.normalized_text if external_normalization else "",
                    external_normalization.rewrite_text if external_normalization else "",
                ]
            )
        )
        interpretation_messages = [candidate for candidate in interpretation_messages if candidate]
        condition_messages = list(interpretation_messages)
        external_region_damaged = self._external_region_damaged(external_correction, region_names)
        if external_region_damaged and external_correction:
            damaged_external_normalization = self.query_normalizer.normalize(external_correction.corrected_text, region_names=region_names)
            condition_messages = list(
                dict.fromkeys(
                    [
                        *condition_messages,
                        external_correction.corrected_text,
                        damaged_external_normalization.normalized_text,
                        damaged_external_normalization.rewrite_text,
                    ]
                )
            )
            condition_messages = [candidate for candidate in condition_messages if candidate]
        legacy_region = self._first_legacy_region(interpretation_messages)
        region = str(legacy_region["replacement_region"]) if legacy_region else self._first_region(interpretation_messages)
        multiple_region_conflict = self._find_multiple_area_conflict(interpretation_messages)
        ambiguous_region = (
            self._first_ambiguous_region(interpretation_messages, region)
            or (multiple_region_conflict["alias"] if multiple_region_conflict else None)
        )
        ambiguous_region_candidates = (
            multiple_region_conflict["candidates"]
            if multiple_region_conflict and ambiguous_region == multiple_region_conflict["alias"]
            else self.ambiguous_region_aliases.get(ambiguous_region or "", [])
        )
        conditions, excluded_conditions = self._merge_condition_filters(condition_messages)
        transformer_gate = self._condition_transformer_gate(
            message=message,
            normalization=normalization,
            external_correction=external_correction,
            rule_conditions=conditions,
            condition_messages=condition_messages,
        )
        transformer_prediction = self._condition_transformer_prediction(condition_messages, gate=transformer_gate)
        if transformer_prediction["labels"]:
            conditions = list(
                dict.fromkeys(
                    [
                        *conditions,
                        *[
                            label
                            for label in transformer_prediction["labels"]
                            if str(label) not in excluded_conditions
                        ],
                    ]
                )
        )
        ambiguous_conditions = self._find_ambiguous_condition_request(condition_messages, conditions)
        preferences, excluded_preferences = self._merge_preference_filters(condition_messages)
        required_evidence_terms, alternative_evidence_terms = self._merge_evidence_filters(condition_messages)
        required_evidence_terms = self._filter_required_evidence_terms(required_evidence_terms, excluded_conditions)
        alternative_evidence_terms = self._filter_required_evidence_terms(alternative_evidence_terms, excluded_conditions)
        cached_region = self.region_index.get(region or "", {})
        sigungu_code = cached_region.get("sigungu_code") or SIGUNGU_CODES.get(region or "")
        area_name = cached_region.get("area_name")
        intent_prediction = self._best_intent_prediction(interpretation_messages)
        unsupported_intent = self._first_unsupported_intent(interpretation_messages)
        if (
            not unsupported_intent
            and intent_prediction.intent == "unsupported_request"
            and not any(self._has_negated_unsupported_keyword(candidate) for candidate in interpretation_messages)
        ):
            unsupported_intent = "unsupported_request"
        context_prediction = self._best_context_prediction(interpretation_messages)
        allow_region_expansion = any(
            keyword in candidate for keyword in EXPANSION_KEYWORDS for candidate in interpretation_messages
        )
        return {
            "region": region,
            "area_code": cached_region.get("area_code") or AREA_CODES.get(region or ""),
            "sigungu_code": sigungu_code,
            "area_name": area_name,
            "sigungu_name": cached_region.get("sigungu_name"),
            "is_sigungu": bool(sigungu_code),
            "allow_region_expansion": allow_region_expansion,
            "conditional_region_expansion": allow_region_expansion
            and any(keyword in candidate for keyword in CONDITIONAL_EXPANSION_KEYWORDS for candidate in interpretation_messages),
            "conditions": conditions,
            "excluded_conditions": excluded_conditions,
            "ambiguous_conditions": ambiguous_conditions,
            "require_all_conditions": self._requires_all_conditions(message),
            "preferences": preferences,
            "excluded_preferences": excluded_preferences,
            "features": [
                label
                for label, keywords in FEATURE_KEYWORDS.items()
                if any(keyword in candidate for keyword in keywords for candidate in condition_messages)
            ],
            "required_evidence_terms": required_evidence_terms,
            "alternative_evidence_terms": alternative_evidence_terms,
            "unsupported_intent": unsupported_intent,
            "ml_intent": intent_prediction.intent,
            "ml_intent_confidence": intent_prediction.confidence,
            "context_labels": context_prediction.labels,
            "context_confidence_by_label": context_prediction.confidence_by_label,
            "context_source_by_label": context_prediction.source_by_label,
            "ambiguous_region": ambiguous_region,
            "ambiguous_region_candidates": ambiguous_region_candidates,
            "region_cache_status": self.cache_status,
            "region_cache_warning": self.cache_warning,
            "legacy_region": legacy_region.get("alias") if legacy_region else None,
            "legacy_region_replacement": legacy_region.get("replacement_region") if legacy_region else None,
            "legacy_region_notice": legacy_region.get("notice") if legacy_region else None,
            "raw_query": normalization.raw_text,
            "normalized_query": normalization.normalized_text,
            "rewrite_query": normalization.rewrite_text,
            "normalization_corrections": normalization.corrections,
            "normalization_risk_tags": normalization.risk_tags,
            "external_correction_enabled": self.external_correction_enabled,
            "external_correction_accepted": external_correction.accepted if external_correction else False,
            "external_correction_provider": external_correction.provider if external_correction else None,
            "external_correction_model": external_correction.model if external_correction else None,
            "external_correction_query": external_correction.corrected_text if external_correction else None,
            "external_correction_reason": external_correction.reason if external_correction else None,
            "external_correction_damaged_terms": external_correction.damaged_terms if external_correction else [],
            "external_correction_region_damaged": external_region_damaged,
            "condition_transformer_enabled": bool(self.condition_transformer),
            "condition_transformer_invoked": transformer_prediction["invoked"],
            "condition_transformer_gate_reason": transformer_gate["reason"],
            "condition_transformer_labels": transformer_prediction["labels"],
            "condition_transformer_reason": transformer_prediction["reason"],
            "condition_transformer_confidence_by_label": transformer_prediction["confidence_by_label"],
        }

    def _external_correction(
        self,
        message: str,
        region_names: list[str],
        normalization: NormalizedQuery,
    ) -> ExternalCorrectionResult | None:
        if not self.external_correction_enabled or not self.external_corrector:
            return None
        if not self._should_try_external_correction(message, normalization):
            return None
        protected_terms = sorted(set(DEFAULT_PROTECTED_TERMS + region_names), key=len, reverse=True)
        return self.external_corrector.correct(message, protected_terms=protected_terms)

    def _should_try_external_correction(self, message: str, normalization: NormalizedQuery) -> bool:
        if not self.settings.tourism_korean_correction_risky_only:
            return True
        if any(tag in {"no-spacing-input", "spacing-noise-input"} for tag in normalization.risk_tags):
            return True
        if normalization.corrections:
            return True
        compact = "".join(str(message or "").split())
        if re.search(r"[가-힣]{10,}", compact) and " " not in str(message or ""):
            return True
        risky_fragments = [
            "휄",
            "휠쳐",
            "휠체여",
            "휠채",
            "유모챠",
            "유아챠",
            "엘리배",
            "앨리",
            "승강끼",
            "보조갼",
            "무릅",
            "자 막",
            "촉 지",
            "장애 인",
        ]
        return any(fragment in str(message or "") for fragment in risky_fragments)

    @staticmethod
    def _external_region_damaged(correction: ExternalCorrectionResult | None, region_names: list[str]) -> bool:
        if not correction or correction.accepted:
            return False
        damaged_terms = set(correction.damaged_terms or [])
        region_term_set = set(region_names)
        return bool(damaged_terms and damaged_terms <= region_term_set)

    def _condition_transformer_gate(
        self,
        message: str,
        normalization: NormalizedQuery,
        external_correction: ExternalCorrectionResult | None,
        rule_conditions: list[str],
        condition_messages: list[str],
    ) -> dict[str, object]:
        if not self.condition_transformer:
            return {"invoke": False, "reason": "disabled"}
        if not rule_conditions:
            return {"invoke": True, "reason": "no_rule_condition"}
        if rule_conditions == ["대중교통"]:
            return {"invoke": True, "reason": "weak_public_transport_only"}
        if external_correction and external_correction.accepted and external_correction.changed:
            return {"invoke": True, "reason": "external_correction_candidate"}
        if self._is_noisy_condition_input(message, normalization):
            return {"invoke": True, "reason": "noisy_input"}
        if any(self._has_hard_semantic_condition_marker(candidate) for candidate in condition_messages):
            return {"invoke": True, "reason": "hard_semantic_marker"}
        return {"invoke": False, "reason": "clean_rule_confident"}

    def _condition_transformer_prediction(self, messages: list[str], gate: dict[str, object] | None = None) -> dict[str, object]:
        if not self.condition_transformer:
            return {"labels": [], "confidence_by_label": {}, "reason": "disabled", "invoked": False}
        if gate is not None and not gate.get("invoke"):
            return {
                "labels": [],
                "confidence_by_label": {},
                "reason": f"skipped:{gate.get('reason') or 'gate'}",
                "invoked": False,
            }
        predictions = [self.condition_transformer.predict(candidate) for candidate in messages if candidate]
        if not predictions:
            return {"labels": [], "confidence_by_label": {}, "reason": "empty", "invoked": True}
        labels: list[str] = []
        confidence_by_label: dict[str, float] = {}
        reasons: list[str] = []
        for prediction in predictions:
            labels.extend(str(label) for label in prediction.get("labels") or [])
            for label, confidence in (prediction.get("confidence_by_label") or {}).items():
                current = confidence_by_label.get(str(label), 0.0)
                confidence_by_label[str(label)] = max(current, float(confidence))
            reason = str(prediction.get("reason") or "")
            if reason:
                reasons.append(reason)
        return {
            "labels": list(dict.fromkeys(labels)),
            "confidence_by_label": confidence_by_label,
            "reason": ",".join(dict.fromkeys(reasons)) or "ok",
            "invoked": True,
        }

    def _is_noisy_condition_input(self, message: str, normalization: NormalizedQuery) -> bool:
        if any(tag in {"no-spacing-input", "spacing-noise-input"} for tag in normalization.risk_tags):
            return True
        if normalization.corrections:
            return True
        compact = re.sub(r"\s+", "", str(message or ""))
        if re.search(r"[가-힣]{10,}", compact) and " " not in str(message or ""):
            return True
        noisy_fragments = [
            "휄",
            "휠챠",
            "휠쳐",
            "휠체여",
            "휠채",
            "유모챠",
            "아기차",
            "애기차",
            "주챠",
            "주차ㅏ",
            "주자창",
            "장실",
            "엘베",
            "앨베",
            "엘레베터",
            "보조갼",
            "점자블럭",
            "수어자막",
        ]
        return any(fragment in str(message or "") for fragment in noisy_fragments)

    @staticmethod
    def _has_hard_semantic_condition_marker(message: str) -> bool:
        compact = re.sub(r"\s+", "", str(message or ""))
        markers = [
            "오래안걷",
            "많이안걷",
            "계단적",
            "무릎",
            "허리불편",
            "쉬엄쉬엄",
            "쉬어가",
            "영상에글자",
            "소리없이",
            "손으로만져",
            "바퀴의자",
            "차댈",
            "차대기",
        ]
        return any(marker in compact for marker in markers)

    def _first_legacy_region(self, messages: list[str]) -> dict[str, str] | None:
        for candidate in messages:
            legacy_region = self._find_legacy_region(candidate)
            if legacy_region:
                return legacy_region
        return None

    def _first_region(self, messages: list[str]) -> str | None:
        for candidate in messages:
            region = self._find_region(candidate)
            if region:
                return region
        return None

    def _first_ambiguous_region(self, messages: list[str], region: str | None) -> str | None:
        for candidate in messages:
            ambiguous_region = self._find_ambiguous_region(candidate, region)
            if ambiguous_region:
                return ambiguous_region
        return None

    def _best_intent_prediction(self, messages: list[str]):
        predictions = [self.intent_classifier.predict(candidate) for candidate in messages]
        return max(predictions, key=lambda prediction: prediction.confidence)

    def _first_unsupported_intent(self, messages: list[str]) -> str | None:
        for candidate in messages:
            unsupported_intent = self._find_unsupported_intent(candidate)
            if unsupported_intent:
                return unsupported_intent
        return None

    def _best_context_prediction(self, messages: list[str]):
        predictions = [self.context_classifier.predict(candidate) for candidate in messages]
        return max(
            predictions,
            key=lambda prediction: (len(prediction.labels), sum(prediction.confidence_by_label.values())),
        )

    @classmethod
    def _merge_condition_filters(cls, messages: list[str]) -> tuple[list[str], list[str]]:
        conditions: list[str] = []
        excluded_conditions: list[str] = []
        for candidate in messages:
            candidate_conditions, candidate_excluded = cls._extract_condition_filters(candidate)
            conditions.extend(candidate_conditions)
            excluded_conditions.extend(candidate_excluded)
        excluded_conditions = list(dict.fromkeys(excluded_conditions))
        conditions = [label for label in dict.fromkeys(conditions) if label not in excluded_conditions]
        return conditions, excluded_conditions

    @classmethod
    def _extract_condition_filters(cls, message: str) -> tuple[list[str], list[str]]:
        conditions: list[str] = []
        excluded_conditions: list[str] = []
        compact = re.sub(r"\s+", "", message)
        for label, keywords in CONDITION_KEYWORDS.items():
            label_excluded = False
            for keyword in sorted(keywords, key=lambda value: len(re.sub(r"\s+", "", value)), reverse=True):
                compact_keyword = re.sub(r"\s+", "", keyword)
                if keyword not in message and compact_keyword not in compact:
                    continue
                if cls._is_condition_excluded(message, keyword) or cls._is_condition_excluded_by_anaphora(message, keyword):
                    excluded_conditions.append(label)
                    label_excluded = True
                    break
                conditions.append(label)
                break
            if label_excluded:
                conditions = [condition for condition in conditions if condition != label]
        return list(dict.fromkeys(conditions)), list(dict.fromkeys(excluded_conditions))

    @staticmethod
    def _is_condition_excluded(message: str, keyword: str) -> bool:
        compact = re.sub(r"\s+", "", message)
        compact_keyword = re.sub(r"\s+", "", keyword)
        if not compact_keyword:
            return False
        escaped = re.escape(compact_keyword)
        exclusion_patterns = [
            rf"{escaped}(은|는|이|가|을|를|도|만)?(있는|잇는|되는|가능한|가능|편한)?(말고|빼고|제외|제외하고|아니고|아닌)",
            rf"{escaped}(조건|기준|정보)?(은|는|이|가|을|를|도|만)?(있는|잇는|되는|가능한|가능|편한)?(취소|빼줘|빼고)",
        ]
        return any(re.search(pattern, compact) for pattern in exclusion_patterns)

    @staticmethod
    def _is_condition_excluded_by_anaphora(message: str, keyword: str) -> bool:
        compact = re.sub(r"\s+", "", message)
        compact_keyword = re.sub(r"\s+", "", keyword)
        if not compact_keyword:
            return False
        escaped = re.escape(compact_keyword)
        patterns = [
            rf"{escaped}(이었|였|이였|였었|이었었)?(는데|지만|다가).{{0,14}}(그건|그거|그조건|그기준|이건|이거)(은|는|을|를)?(빼고|말고|제외|제외하고)",
            rf"(처음엔|처음에는|처음은).{{0,12}}{escaped}.{{0,14}}(그건|그거|그조건|그기준|이건|이거)(은|는|을|를)?(빼고|말고|제외|제외하고)",
        ]
        return any(re.search(pattern, compact) for pattern in patterns)

    @classmethod
    def _find_ambiguous_condition_request(cls, messages: list[str], conditions: list[str]) -> list[str]:
        if not messages:
            return []
        condition_set = set(conditions)
        if not condition_set & {"휠체어", "접근로", "고령자"}:
            return []
        text = " ".join(messages)
        if cls._has_explicit_condition_anchor(text):
            return []
        compact = re.sub(r"\s+", "", text)
        ambiguous_markers = [
            "걷기편",
            "걷기좋",
            "이동편",
            "편한곳",
            "편하게",
            "편한관광",
            "계단적",
            "계단오르내림",
            "많이안걷",
            "오래안걷",
            "무리적",
            "부담적",
            "막히지않",
            "돌아나오지",
            "접근성좋",
            "접근좋",
        ]
        if not any(marker in compact for marker in ambiguous_markers):
            return []
        if any(marker in compact for marker in ["접근성좋", "접근좋"]):
            labels = ["휠체어", "접근로", "고령자"]
            return [label for label in labels if label in condition_set or label in {"접근로", "고령자"}]
        if any(marker in compact for marker in ["계단적", "많이안걷", "오래안걷", "무리적", "부담적"]):
            labels = ["고령자", *[label for label in ["접근로"] if label in condition_set]]
            return list(dict.fromkeys(labels))
        if "고령자" in condition_set and condition_set & {"휠체어", "접근로"}:
            return ["고령자", *[label for label in ["휠체어", "접근로"] if label in condition_set]]
        if {"휠체어", "접근로"} <= condition_set:
            return ["휠체어", "접근로"]
        return []

    @staticmethod
    def _has_explicit_condition_anchor(text: str) -> bool:
        explicit_terms = [
            "휠체어",
            "휠챠",
            "휠체여",
            "휠채",
            "바퀴의자",
            "바퀴 의자",
            "이동 보조기구",
            "경사로",
            "접근로",
            "출입통로",
            "출입 통로",
            "단차",
            "문턱",
            "턱",
            "어르신",
            "고령자",
            "노약자",
            "부모님",
            "무릎",
            "허리 불편",
            "많이 안 걷",
            "많이안걷",
            "오래 안 걷",
            "오래안걷",
            "쉬어",
            "앉",
        ]
        return any(term in text for term in explicit_terms)

    @classmethod
    def _merge_preference_filters(cls, messages: list[str]) -> tuple[list[str], list[str]]:
        preferences: list[str] = []
        excluded_preferences: list[str] = []
        for candidate in messages:
            candidate_preferences, candidate_excluded = cls._extract_preference_filters(candidate)
            preferences.extend(candidate_preferences)
            excluded_preferences.extend(candidate_excluded)
        return list(dict.fromkeys(preferences)), list(dict.fromkeys(excluded_preferences))

    @classmethod
    def _merge_required_evidence_terms(cls, messages: list[str]) -> list[list[str]]:
        merged: list[list[str]] = []
        seen: set[tuple[str, ...]] = set()
        for candidate in messages:
            for group in cls._extract_required_evidence_terms(candidate):
                key = tuple(group)
                if key in seen:
                    continue
                seen.add(key)
                merged.append(group)
        return merged

    @classmethod
    def _merge_evidence_filters(cls, messages: list[str]) -> tuple[list[list[str]], list[list[str]]]:
        required: list[list[str]] = []
        alternative: list[list[str]] = []
        seen_required: set[tuple[str, ...]] = set()
        seen_alternative: set[tuple[str, ...]] = set()
        for candidate in messages:
            candidate_required, candidate_alternative = cls._extract_evidence_filters(candidate)
            for group in candidate_required:
                key = tuple(group)
                if key not in seen_required:
                    seen_required.add(key)
                    required.append(group)
            for group in candidate_alternative:
                key = tuple(group)
                if key not in seen_alternative:
                    seen_alternative.add(key)
                    alternative.append(group)
        return required, alternative

    @classmethod
    def _filter_required_evidence_terms(cls, required_groups: list[list[str]], excluded_conditions: list[str]) -> list[list[str]]:
        if not required_groups or not excluded_conditions:
            return required_groups
        return [
            group
            for group in required_groups
            if cls._condition_label_for_evidence_terms(group) not in excluded_conditions
        ]

    @staticmethod
    def _condition_label_for_evidence_terms(terms: list[str]) -> str | None:
        term_set = set(terms)
        if term_set & {"유모차", "유아차", "수유실", "영유아", "기저귀", "유아용 의자"}:
            return "유모차"
        if term_set & {"주차", "주차장"}:
            return "주차"
        if term_set & {"화장실"}:
            return "화장실"
        if term_set & {"엘리베이터", "승강기"}:
            return "엘리베이터"
        if term_set & {"경사로"}:
            return "접근로"
        if term_set & {"보조견", "안내견"}:
            return "보조견"
        if term_set & {
            "점자",
            "점자블록",
            "촉지도",
            "촉지 안내도",
            "촉지안내도",
            "촉지 안내판",
            "촉지안내판",
            "촉지판",
            "음성안내",
            "오디오가이드",
            "점자홍보물",
        }:
            return "시각장애"
        if term_set & {"수어", "수화", "자막", "문자안내", "영상안내"}:
            return "청각장애"
        return None

    @staticmethod
    def _extract_required_evidence_terms(message: str) -> list[list[str]]:
        required, alternative = TourismQueryService._extract_evidence_filters(message)
        return [*required, *alternative]

    @staticmethod
    def _extract_evidence_filters(message: str) -> tuple[list[list[str]], list[list[str]]]:
        term_groups: list[list[str]] = []
        alternative_groups: list[list[str]] = []
        skip_individual_terms: set[str] = set()
        hearing_or_request = (
            any(term in message for term in ["수어", "수화"])
            and "자막" in message
            and any(marker in message for marker in ["나", "이나", "또는", "혹은"])
        )
        if hearing_or_request:
            alternative_groups.append(["수어", "수화", "자막", "문자안내", "영상안내"])
            skip_individual_terms.update({"수어", "수화", "자막"})
        sensory_or_patterns = [
            (
                ("점자", "점자블록"),
                ("음성안내", "음성 안내", "오디오가이드"),
                ["점자", "점자블록", "음성안내", "음성 안내", "오디오가이드", "점자홍보물"],
            ),
            (
                ("점자블록", "점자 블럭", "점자 유도블록"),
                ("촉지도", "촉지 안내도"),
                ["점자블록", "점자", "촉지도"],
            ),
            (
                ("보조견", "안내견"),
                ("점자", "점자 안내", "점자블록", "촉지도"),
                ["보조견", "안내견", "점자", "점자블록", "촉지도"],
            ),
        ]
        compact = re.sub(r"\s+", "", message)
        for left_terms, right_terms, evidence_terms in sensory_or_patterns:
            left_match = any(term in message or re.sub(r"\s+", "", term) in compact for term in left_terms)
            right_match = any(term in message or re.sub(r"\s+", "", term) in compact for term in right_terms)
            has_or_marker = any(marker in message for marker in ["나", "이나", "또는", "혹은", "둘 중", "둘중"]) or any(
                marker in compact for marker in ["나", "이나", "또는", "혹은", "둘중"]
            )
            if left_match and right_match and has_or_marker:
                alternative_groups.append(evidence_terms)
                for term in [*left_terms, *right_terms]:
                    skip_individual_terms.add(term)
        tactile_evidence_terms = [
            "촉지도",
            "촉지 안내도",
            "촉지안내도",
            "촉지 안내판",
            "촉지안내판",
            "촉지판",
            "촉지·음성 안내판",
            "촉지",
        ]
        term_map = [
            (["점자블록", "점자"], ["점자블록", "점자"]),
            (["오디오가이드", "음성안내", "음성 안내"], ["오디오가이드", "음성안내", "음성 안내"]),
            (
                [
                    "촉지도",
                    "촉지 안내도",
                    "촉지안내도",
                    "촉지 안내판",
                    "촉지안내판",
                    "촉지판",
                    "손으로 만져 확인할 안내",
                    "손으로만져확인할안내",
                    "손으로 만져 확인",
                    "손으로만져확인",
                ],
                tactile_evidence_terms,
            ),
            (["시각장애", "시각 장애"], ["점자", "점자블록", *tactile_evidence_terms, "음성안내", "오디오가이드", "점자홍보물"]),
            (["보조견", "안내견"], ["보조견", "안내견"]),
            (["청각장애", "청각 장애"], ["수어", "수화", "자막", "문자안내", "영상안내"]),
            (["수어", "수화"], ["수어", "수화"]),
            (["자막"], ["자막"]),
            (["장애인 주차", "주차장", "주차"], ["주차", "주차장"]),
            (["장애인 화장실", "화장실"], ["화장실"]),
            (["엘리베이터", "승강기"], ["엘리베이터", "승강기"]),
            (["경사로"], ["경사로"]),
            (["수유실"], ["수유실"]),
            (["기저귀"], ["기저귀", "기저귀교환대", "기저귀 교환대"]),
            (["유모차 대여"], ["유모차 대여", "유모차"]),
            (["유아용 의자"], ["유아용 의자"]),
        ]
        for triggers, terms in term_map:
            if skip_individual_terms and any(term in skip_individual_terms for term in triggers):
                continue
            if any(trigger in message or re.sub(r"\s+", "", trigger) in compact for trigger in triggers):
                term_groups.append(terms)
        family_context_terms = ["아이랑", "아이와", "아이 동반", "어린이", "가족", "영유아", "아기"]
        if any(term in message for term in family_context_terms):
            term_groups.append(["유모차", "수유실", "영유아", "기저귀", "어린이", "아이", "가족", "유아용 의자"])
        if (
            "시장" in message
            and not any(term in message or re.sub(r"\s+", "", term) in compact for term in ["먹거리", "음식", "식당", "맛집"])
            and not TourismQueryService._is_preference_excluded(message, "시장")
        ):
            term_groups.append(["시장", "먹자골목", "전통시장"])
        return term_groups, alternative_groups

    @staticmethod
    def _requires_all_conditions(message: str) -> bool:
        explicit_all_markers = [
            "둘 다",
            "둘다",
            "모두",
            "전부",
            "동시에",
            "같이 만족",
            "함께 만족",
            "둘 모두",
            "다 되는",
            "다 가능한",
            "전부 가능한",
            "모두 가능한",
            "반드시",
            "꼭",
        ]
        return any(marker in message for marker in explicit_all_markers)

    @staticmethod
    def _extract_preference_filters(message: str) -> tuple[list[str], list[str]]:
        preferences: list[str] = []
        excluded_preferences: list[str] = []
        for label, keywords in PREFERENCE_KEYWORDS.items():
            matched_keywords = [keyword for keyword in keywords if keyword in message]
            if not matched_keywords:
                continue
            if any(TourismQueryService._is_preference_excluded(message, keyword) for keyword in matched_keywords):
                excluded_preferences.append(label)
            elif any(TourismQueryService._is_preference_replacement_target(message, keyword) for keyword in matched_keywords):
                preferences.append(label)
            else:
                preferences.append(label)
        return preferences, excluded_preferences

    @staticmethod
    def _is_preference_replacement_target(message: str, keyword: str) -> bool:
        start = message.find(keyword)
        if start == -1:
            return False
        for marker in ["말고", "대신", "아니고"]:
            marker_index = message.find(marker)
            if marker_index != -1 and marker_index < start:
                return True
        return False

    @staticmethod
    def _is_preference_excluded(message: str, keyword: str) -> bool:
        start = message.find(keyword)
        if start == -1:
            return False
        end = start + len(keyword)
        tail = message[end : min(len(message), end + 32)].lstrip()
        for particle in ["은", "는", "이", "가", "을", "를", "이나", "나", "하고", "랑", "와", "과"]:
            if tail.startswith(particle):
                tail = tail[len(particle) :].lstrip()
                break
        same_clause_tail = re.split(r"[.!?。！？,，]", tail, maxsplit=1)[0]
        return any(
            same_clause_tail.startswith(negation) or negation in same_clause_tail[:16]
            for negation in NEGATION_NEARBY_KEYWORDS
        )

    @staticmethod
    def _is_negated_near_keyword(message: str, keyword: str) -> bool:
        start = message.find(keyword)
        if start == -1:
            return False
        end = start + len(keyword)
        window = message[max(0, start - 8) : min(len(message), end + 8)]
        return any(negation in window for negation in NEGATION_NEARBY_KEYWORDS)

    @staticmethod
    def _find_unsupported_intent(message: str) -> str | None:
        for label, keywords in UNSUPPORTED_INTENT_KEYWORDS.items():
            if any(keyword in message and not TourismQueryService._is_negated_near_keyword(message, keyword) for keyword in keywords):
                return label
        return None

    @staticmethod
    def _has_negated_unsupported_keyword(message: str) -> bool:
        return any(
            keyword in message and TourismQueryService._is_negated_near_keyword(message, keyword)
            for keywords in UNSUPPORTED_INTENT_KEYWORDS.values()
            for keyword in keywords
        )

    def _find_region(self, message: str) -> str | None:
        for name in sorted(self.region_index, key=len, reverse=True):
            if name and self._contains_region_name(message, name) and not self._is_region_negated(message, name):
                return name
        return next(
            (
                name
                for name in AREA_CODES
                if self._contains_region_name(message, name) and not self._is_region_negated(message, name)
            ),
            None,
        )

    @staticmethod
    def _find_multiple_area_conflict(messages: list[str]) -> dict[str, object] | None:
        for message in messages:
            matched = [
                name
                for name in AREA_CODES
                if name and TourismQueryService._contains_region_name(message, name) and not TourismQueryService._is_region_negated(message, name)
            ]
            matched = list(dict.fromkeys(matched))
            if len(matched) >= 2:
                return {
                    "alias": "/".join(matched),
                    "candidates": [
                        {
                            "area_name": name,
                            "sigungu_name": name,
                            "area_code": AREA_CODES.get(name),
                            "sigungu_code": None,
                        }
                        for name in matched
                    ],
                }
        return None

    @staticmethod
    def _contains_region_name(message: str, name: str) -> bool:
        if not name:
            return False
        if len(name) <= 2:
            suffixes = "광역시|특별시|특별자치시|특별자치도|도|시|군|구|로|에서|으로|에"
            return re.search(rf"(?<![가-힣]){re.escape(name)}(?=$|[^가-힣]|{suffixes})", message) is not None
        return name in message

    @staticmethod
    def _is_region_negated(message: str, name: str) -> bool:
        start = message.find(name)
        if start == -1:
            return False
        end = start + len(name)
        tail = message[end : min(len(message), end + 8)].lstrip()
        for suffix in ["시", "군", "구", "도"]:
            suffix_tail = tail[len(suffix) :].lstrip() if tail.startswith(suffix) else ""
            if suffix_tail and any(suffix_tail.startswith(negation) for negation in NEGATION_NEARBY_KEYWORDS):
                return True
        return any(tail.startswith(negation) for negation in NEGATION_NEARBY_KEYWORDS)

    @staticmethod
    def _find_legacy_region(message: str) -> dict[str, str] | None:
        for alias in sorted(LEGACY_REGION_ALIASES, key=len, reverse=True):
            if alias in message and not TourismQueryService._is_region_negated(message, alias):
                return {"alias": alias, **LEGACY_REGION_ALIASES[alias]}
        return None

    def _find_ambiguous_region(self, message: str, region: str | None) -> str | None:
        if any(term in message for term in ["층 이동", "이동 쉬", "이동이 쉬", "위아래 이동"]):
            message = message.replace("이동", "")
        for alias in sorted(self.ambiguous_region_aliases, key=len, reverse=True):
            candidates = self.ambiguous_region_aliases[alias]
            if alias not in message:
                continue
            compact = re.sub(r"\s+", "", message)
            if alias == "광주" and "광주광역시" in compact:
                return None
            if region:
                if region == alias:
                    return alias
                if region in AREA_CODES:
                    if any(candidate.get("area_name") == region for candidate in candidates):
                        return None
                    continue
                return None
            return alias
        return None

    def _load_region_index(self) -> dict[str, dict[str, str | None]]:
        if not self.area_code_cache_path.exists():
            self.cache_status = "missing"
            self.cache_warning = f"지역 코드 캐시를 찾지 못했습니다: {self.area_code_cache_path}"
            logger.warning(self.cache_warning)
            return {}
        try:
            payload = json.loads(self.area_code_cache_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            self.cache_status = "invalid"
            self.cache_warning = f"지역 코드 캐시를 읽을 수 없습니다: {self.area_code_cache_path}"
            logger.warning("%s (%s)", self.cache_warning, exc.__class__.__name__)
            return {}
        region_index = payload.get("region_index", {})
        if not isinstance(region_index, dict):
            self.cache_status = "invalid"
            self.cache_warning = f"지역 코드 캐시 형식이 올바르지 않습니다: {self.area_code_cache_path}"
            logger.warning(self.cache_warning)
            return {}
        ambiguous_region_aliases = payload.get("ambiguous_region_aliases", {})
        if isinstance(ambiguous_region_aliases, dict):
            self.ambiguous_region_aliases = {
                str(alias): [candidate for candidate in candidates if isinstance(candidate, dict)]
                for alias, candidates in ambiguous_region_aliases.items()
                if isinstance(candidates, list)
            }
        loaded_index = {
            str(name): value
            for name, value in region_index.items()
            if isinstance(value, dict)
        }
        for alias, candidates in self.ambiguous_region_aliases.items():
            for candidate in candidates:
                area_name = candidate.get("area_name")
                sigungu_name = candidate.get("sigungu_name") or alias
                if area_name:
                    loaded_index.setdefault(f"{area_name} {alias}", candidate)
                    loaded_index.setdefault(f"{area_name} {sigungu_name}", candidate)
        self._merge_admin_region_aliases(loaded_index)
        return loaded_index

    def _merge_admin_region_aliases(self, loaded_index: dict[str, dict[str, str | None]]) -> None:
        if not self.admin_region_alias_path.exists():
            return
        try:
            payload = json.loads(self.admin_region_alias_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning("행정동/법정동 매칭 데이터를 읽을 수 없습니다: %s (%s)", self.admin_region_alias_path, exc)
            return

        aliases = payload.get("aliases", {})
        if isinstance(aliases, dict):
            self._merge_alias_candidates(aliases, loaded_index)
        dong_aliases = payload.get("dong_aliases", {})
        if isinstance(dong_aliases, dict):
            self._merge_alias_candidates(dong_aliases, loaded_index)

    def _merge_alias_candidates(
        self,
        aliases: dict,
        loaded_index: dict[str, dict[str, str | None]],
    ) -> None:
        for alias, raw_candidates in aliases.items():
            if not isinstance(raw_candidates, list):
                continue
            candidates = [self._normalize_admin_alias_candidate(candidate) for candidate in raw_candidates]
            candidates = [candidate for candidate in candidates if candidate.get("area_code")]
            if not candidates:
                continue
            unique_candidates = self._unique_region_candidates(candidates)
            if len(unique_candidates) == 1:
                loaded_index.setdefault(str(alias), unique_candidates[0])
            else:
                self.ambiguous_region_aliases.setdefault(str(alias), unique_candidates)

    @staticmethod
    def _normalize_admin_alias_candidate(candidate: dict) -> dict[str, str | None]:
        return {
            "area_code": candidate.get("area_code") or candidate.get("tour_area_code"),
            "sigungu_code": candidate.get("sigungu_code") or candidate.get("tour_sigungu_code"),
            "area_name": candidate.get("area_name"),
            "sigungu_name": candidate.get("sigungu_name"),
        }

    @staticmethod
    def _unique_region_candidates(candidates: list[dict[str, str | None]]) -> list[dict[str, str | None]]:
        result = []
        seen = set()
        for candidate in candidates:
            key = (candidate.get("area_code"), candidate.get("sigungu_code"))
            if key in seen:
                continue
            seen.add(key)
            result.append(candidate)
        return result
