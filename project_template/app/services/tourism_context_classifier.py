from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
import json
import math
from pathlib import Path
import re
from typing import Any

from app.core.config import PROJECT_ROOT
from app.services.korean_query_normalizer import KoreanQueryNormalizer


DEFAULT_CONTEXT_MODEL_PATH = PROJECT_ROOT / "data" / "processed" / "tourism_context_classifier.json"

CONTEXT_LABELS = [
    "strict_and",
    "soft_and",
    "or_condition",
    "add_condition",
    "replace_condition",
    "exclude_condition",
    "family_context",
    "mobility_context",
    "specific_facility_required",
]


@dataclass(frozen=True)
class TourismContextPrediction:
    labels: list[str]
    confidence_by_label: dict[str, float]
    source_by_label: dict[str, str]


class TourismContextClassifier:
    def __init__(self, model_path: Path | None = None, threshold: float = 0.62):
        self.model_path = model_path or DEFAULT_CONTEXT_MODEL_PATH
        self.threshold = threshold
        self.model: dict[str, Any] | None = self._load_model(self.model_path)
        self.query_normalizer = KoreanQueryNormalizer()

    def predict(self, text: str) -> TourismContextPrediction:
        normalized = " ".join(text.strip().split())
        query_normalizer = getattr(self, "query_normalizer", KoreanQueryNormalizer())
        normalized_query = query_normalizer.normalize(normalized)
        candidates = list(
            dict.fromkeys(
                candidate
                for candidate in [
                    normalized,
                    normalized_query.normalized_text,
                    normalized_query.rewrite_text,
                ]
                if candidate
            )
        )
        confidence_by_label: dict[str, float] = {}
        source_by_label: dict[str, str] = {}

        for candidate_index, candidate_text in enumerate(candidates):
            suffix = "" if candidate_index == 0 else ":normalized"
            rule_labels = self.rule_labels(candidate_text)
            candidate_confidence_by_label = {label: 0.98 for label in rule_labels}
            candidate_source_by_label = {label: f"rule{suffix}" for label in rule_labels}

            if self.model and candidate_text:
                probabilities = self._predict_model_probabilities(candidate_text)
                for label, probability in probabilities.items():
                    if probability < self.threshold:
                        continue
                    if probability > candidate_confidence_by_label.get(label, 0.0):
                        candidate_confidence_by_label[label] = round(probability, 4)
                        candidate_source_by_label[label] = f"model{suffix}"

            candidate_confidence_by_label, candidate_source_by_label = _postprocess_prediction_labels(
                candidate_text,
                set(rule_labels),
                candidate_confidence_by_label,
                candidate_source_by_label,
            )
            for label, confidence in candidate_confidence_by_label.items():
                if confidence > confidence_by_label.get(label, 0.0):
                    confidence_by_label[label] = confidence
                    source_by_label[label] = candidate_source_by_label[label]

        labels = [label for label in CONTEXT_LABELS if label in confidence_by_label]
        return TourismContextPrediction(labels=labels, confidence_by_label=confidence_by_label, source_by_label=source_by_label)

    @staticmethod
    def rule_labels(text: str) -> set[str]:
        if not text:
            return set()

        labels: set[str] = set()
        if _looks_like_strict_and(text):
            labels.add("strict_and")
        if _looks_like_or_condition(text):
            labels.add("or_condition")
        if _looks_like_replace(text):
            labels.add("replace_condition")
        elif _looks_like_exclude(text):
            labels.add("exclude_condition")
        if _looks_like_add(text):
            labels.add("add_condition")
        if _looks_like_family_context(text):
            labels.add("family_context")
        if _looks_like_mobility_context(text):
            labels.add("mobility_context")
        if _looks_like_specific_facility_required(text):
            labels.add("specific_facility_required")
        if _looks_like_soft_and(text, labels):
            labels.add("soft_and")
        return labels

    @staticmethod
    def _load_model(path: Path) -> dict[str, Any] | None:
        if not path.exists():
            return None
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        return payload if isinstance(payload, dict) else None

    def _predict_model_probabilities(self, text: str) -> dict[str, float]:
        tokens = _tokens(text)
        if not tokens:
            return {}

        labels = list(self.model.get("labels") or []) if self.model else []
        models: dict[str, Any] = dict(self.model.get("models") or {}) if self.model else {}
        probabilities: dict[str, float] = {}
        for label in labels:
            label_model = dict(models.get(label) or {})
            positive = _label_log_score(tokens, label_model, "positive")
            negative = _label_log_score(tokens, label_model, "negative")
            probabilities[label] = _binary_probability(positive, negative)
        return probabilities


STRICT_AND_MARKERS = [
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
    "빠짐없이",
    "없으면 안",
    "하나만 되는 곳은 제외",
    "하나라도 근거 없으면",
    "근거 없으면 빼",
    "빠지면",
    "없으면 패스",
    "빠지면 패스",
    "동시에 확인",
    "같이 확인",
    "같이 확인된",
    "함께 있는",
    "둘이 함께",
    "둘 다 필요",
    "빠지면 곤란",
    "는 물론",
    "까지 근거",
]
GENERIC_STRICT_FALSE_POSITIVE_PATTERNS = [
    "모두가 좋아할",
    "모두 좋아할",
    "전부 좋아할",
    "동시에 요구하는 건 아니",
    "다 요구하는 건 아니",
    "둘 다 요구하는 건 아니",
    "둘 다 말하긴 했지만",
    "꼭 맞출 필요는 없어",
]

FAMILY_CONTEXT_TERMS = [
    "애기",
    "아가",
    "아이가",
    "초등학생",
    "아이는",
    "아이도",
    "아이에게",
    "아이 기준",
    "아이랑",
    "아이와",
    "아이 동반",
    "아이 있",
    "아이 때문에",
    "아이 데리고",
    "아이를 데리고",
    "아이 ",
    "아이 휴식",
    "아이용 의자",
    "어린이",
    "가족",
    "영유아",
    "아기",
    "유아 의자",
]
FAMILY_FACILITY_TERMS = [
    "수유",
    "기저귀",
]

MOBILITY_CONTEXT_TERMS = [
    "휠체어",
    "전동휠체어",
    "전동 스쿠터",
    "계단",
    "턱",
    "이동 편",
    "걷기 편",
    "동선",
    "보행",
    "어르신",
    "노약자",
    "유모차",
    "유아차",
    "유모차로 이동",
    "오래 걷",
    "오르막",
    "오르내림",
    "이동 반경",
    "무릎이 불편",
    "발목 다친",
    "이동 거리",
    "오래 서서",
    "줄 서는 시간이 길지",
    "걷는 시간이 짧",
    "짧은 코스",
    "짧게 둘러",
    "앉아 쉴",
    "버겁지 않은",
    "걷기 부담",
    "평지",
    "동선 짧",
    "계단이 적",
    "계단 적",
    "부담 없는",
    "부담 적",
    "이동 부담",
    "움직이기 쉬운",
    "걷지 않는",
    "짧게 다녀",
    "힘들지 않은",
    "피하고 싶",
]
MOBILITY_FACILITY_TERMS = ["경사로", "엘리베이터", "승강기"]

SPECIFIC_FACILITY_TERMS = [
    "점자블록",
    "점자",
    "촉지도",
    "음성안내",
    "오디오가이드",
    "수어",
    "수화",
    "자막",
    "문자안내",
    "영상안내",
    "보조견",
    "안내견",
    "장애인 주차",
    "장애인주차",
    "주차장",
    "장애인 화장실",
    "화장실",
    "엘리베이터",
    "엘베",
    "승강기",
    "경사로",
    "수유실",
    "기저귀",
    "유아용 의자",
    "유아 의자",
    "아이용 의자",
    "수유 공간",
    "유모차 대여",
]

ADD_MARKERS = [
    "추가",
    "까지",
    "도 봐",
    "도 되는",
    "도 가능",
    "있는 곳",
    "되는 곳",
    "확인되는 곳",
    "조건 추가",
    "근거도",
    "필터",
    "더해",
    "얹어",
    "붙여",
    "충족하는지",
    "같은 카드 안",
    "목록 안에서",
    "후보들에",
    "방금 후보",
    "아까 카드",
    "위 카드",
    "위 목록",
    "이전 결과",
    "이전 추천",
    "남겨줘",
    "좁혀줘",
    "같은 결과에서",
]
EXCLUDE_MARKERS = [
    "말고",
    "빼고",
    "빼줘",
    "제외",
    "사양",
    "아닌 곳",
    "필요 없어",
    "안 갈",
    "원하지 않아",
    "뒤로 보내",
    "뒤로 미루",
    "위주 결과는 뒤로",
    "느낌만 아니면",
    "성격은 빼",
    "빼되",
    "이번엔 빼",
]
REPLACE_MARKERS = [
    "대신",
    "바꿔",
    "변경",
    "로 바꿔",
    "기준 말고",
    "취소하고",
    "내려놓고",
    "그만하고",
    "갈아타자",
    "잊고",
    "버리고",
    "더 보지 말고",
    "이제",
]
OR_MARKERS = [
    " 또는 ",
    " 혹은 ",
    " 아니면 ",
    " 중 하나",
    " 둘 중",
    "거나",
    "든지",
    "라도",
    "/",
    "하나면 충분",
    "하나면 된다",
    "다 요구하는 건 아니",
    "둘 다 요구하는 건 아니",
    "아니어도",
    "동시에 요구하는 건 아니",
]

CONDITION_GROUP_TERMS = [
    ["휠체어", "전동휠체어", "경사로", "엘리베이터", "승강기", "계단", "주차"],
    ["유모차", "유아차", "아이", "어린이", "유아", "가족", "수유실", "기저귀"],
    ["점자", "점자블록", "촉지도", "음성안내", "오디오가이드", "시각장애"],
    ["수어", "수화", "자막", "청각장애", "문자안내"],
    ["보조견", "안내견"],
    ["시장", "먹거리", "식당", "카페", "음식점"],
    ["공원", "산책", "자연", "해변", "숲", "조용한 곳", "조용한"],
    ["실내", "실내 관람", "박물관", "미술관", "전시", "관람"],
]


def train_context_model(rows: list[dict[str, Any]]) -> dict[str, Any]:
    labels = list(CONTEXT_LABELS)
    token_counts: dict[str, dict[str, Counter[str]]] = {
        label: {"positive": Counter(), "negative": Counter()} for label in labels
    }
    doc_counts: dict[str, dict[str, int]] = {label: {"positive": 0, "negative": 0} for label in labels}
    vocab: set[str] = set()

    for row in rows:
        text = str(row.get("text") or "")
        expected_labels = set(row.get("labels") or [])
        tokens = _tokens(text)
        vocab.update(tokens)
        for label in labels:
            bucket = "positive" if label in expected_labels else "negative"
            doc_counts[label][bucket] += 1
            token_counts[label][bucket].update(tokens)

    models: dict[str, Any] = {}
    vocab_size = max(1, len(vocab))
    for label in labels:
        label_model: dict[str, Any] = {
            "priors": {},
            "token_log_probs": {"positive": {}, "negative": {}},
            "unknown_log_probs": {},
        }
        total_docs = doc_counts[label]["positive"] + doc_counts[label]["negative"]
        for bucket in ("positive", "negative"):
            prior = (doc_counts[label][bucket] + 1) / (total_docs + 2) if total_docs else 0.5
            label_model["priors"][bucket] = math.log(prior)
            total_tokens = sum(token_counts[label][bucket].values())
            denominator = total_tokens + vocab_size
            label_model["unknown_log_probs"][bucket] = math.log(1 / denominator)
            for token in sorted(vocab):
                probability = (token_counts[label][bucket][token] + 1) / denominator
                label_model["token_log_probs"][bucket][token] = math.log(probability)
        models[label] = label_model

    return {"version": 1, "labels": labels, "models": models}


def _label_log_score(tokens: list[str], label_model: dict[str, Any], bucket: str) -> float:
    value = float(dict(label_model.get("priors") or {}).get(bucket, math.log(0.5)))
    token_log_probs = dict(dict(label_model.get("token_log_probs") or {}).get(bucket) or {})
    unknown = float(dict(label_model.get("unknown_log_probs") or {}).get(bucket, -20.0))
    for token in tokens:
        value += float(token_log_probs.get(token, unknown))
    return value


def _binary_probability(positive: float, negative: float) -> float:
    maximum = max(positive, negative)
    positive_exp = math.exp(positive - maximum)
    negative_exp = math.exp(negative - maximum)
    return positive_exp / (positive_exp + negative_exp)


def _postprocess_prediction_labels(
    text: str,
    rule_labels: set[str],
    confidence_by_label: dict[str, float],
    source_by_label: dict[str, str],
) -> tuple[dict[str, float], dict[str, str]]:
    labels = dict(confidence_by_label)
    sources = dict(source_by_label)

    def discard(label: str) -> None:
        labels.pop(label, None)
        sources.pop(label, None)

    # Family/mobility are user-context labels, not a synonym for every child/mobility facility field.
    for context_label in ("family_context", "mobility_context"):
        if context_label in labels and context_label not in rule_labels:
            discard(context_label)
    for structural_label in ("strict_and", "or_condition"):
        if structural_label in labels and structural_label not in rule_labels:
            discard(structural_label)

    # Soft conditions should not be attached to explicit follow-up actions.
    if "soft_and" in labels and labels.keys() & {
        "strict_and",
        "or_condition",
        "add_condition",
        "replace_condition",
        "exclude_condition",
    }:
        discard("soft_and")
    if "soft_and" in labels and "soft_and" not in rule_labels:
        discard("soft_and")

    if "specific_facility_required" in labels and not _looks_like_specific_facility_required(text):
        discard("specific_facility_required")
    for action_label in ("add_condition", "replace_condition", "exclude_condition"):
        if action_label in labels and action_label not in rule_labels:
            discard(action_label)

    return labels, sources


def _tokens(text: str) -> list[str]:
    normalized = re.sub(r"\s+", " ", text.strip().lower())
    chars = [char for char in normalized if not char.isspace()]
    tokens = [normalized]
    for size in (1, 2, 3, 4):
        tokens.extend("".join(chars[index : index + size]) for index in range(max(0, len(chars) - size + 1)))
    tokens.extend(part for part in re.split(r"[^0-9a-z가-힣]+", normalized) if part)
    return tokens


def _has_any(text: str, terms: list[str]) -> bool:
    return any(term in text for term in terms)


def _looks_like_strict_and(text: str) -> bool:
    if _has_any(text, GENERIC_STRICT_FALSE_POSITIVE_PATTERNS):
        return False
    if re.search(r"(따로따로\s*말고|추천하지\s*말고).{0,16}(한\s*장소|같은\s*카드|같은\s*곳|있어야)", text):
        return True
    if re.search(r"(한\s*장소|같은\s*카드).{0,24}(같이|함께|동시에).{0,18}(없으면|있어야|적힌|확인|후보에서\s*빼)", text):
        return True
    if re.search(r"(기저귀|수유실|수유\s*공간|유모차|아이용|유아용|유아\s*의자).{0,24}(같은\s*카드|둘\s*다|도\s*있고).{0,24}(적힌|되는|방문지만|곳만)", text):
        return True
    if re.search(r"(한\s*장소|같이|동시에|둘\s*다|둘이\s*함께|함께).{0,18}(확인|맞|해결|있는지만|되는지만|적힌|남겨|있는\s*곳)", text):
        return True
    if re.search(r"(만\s*있거나|만\s*있는).{0,24}말고.{0,20}(둘이\s*함께|함께\s*있는|같이\s*있는|둘\s*다)", text):
        return True
    if re.search(r"(둘\s*중\s*하나라도|하나라도).{0,12}빠지면.{0,10}(제외|빼|패스)", text):
        return True
    if re.search(r"둘\s*중\s*하나\s*빠지면.{0,12}(제외|빼|패스)", text):
        return True
    if re.search(r"두\s*근거가.{0,12}(같이|함께).{0,10}(있어야|확인)", text):
        return True
    if re.search(r"(하나라도|한쪽만|하나만|둘\s*중\s*하나라도).{0,20}(빠지|없|말고|제외|패스)", text):
        return True
    if re.search(r"(까지|하고|랑|와|과).{0,18}(같이\s*맞|두\s*조건이\s*같이|둘\s*다)", text):
        return True
    return _has_any(text, STRICT_AND_MARKERS)


def _looks_like_family_context(text: str) -> bool:
    text = _active_requirement_text(text)
    if (
        re.search(r"(수유실|기저귀|유아용 의자|유아 의자|유모차 대여).{0,24}(참고만|있으면 좋|있으면 더 좋|필수는 아니|꼭 맞출 필요는 없어|덤)", text)
        and not re.search(r"(아이|아기|영유아|유아|어린이|가족|동반|데리고|같이|함께)", text)
    ):
        return False
    if re.search(r"(수유실|기저귀|유아용 의자|유아 의자).{0,12}(근거 없으면|문구|확인된 카드)", text):
        return False
    if re.search(r"가족\s*편의.{0,8}(상관없|빼줘|필요 없)", text):
        return False
    if re.search(r"(가족|아이|아기|영유아|유아).{0,8}(아니|아냐|아님)", text):
        return False
    if re.search(r"(부모|부모님).{0,14}(아이|아기|어린이|유아|가족)|(?:아이|아기|어린이|유아|가족).{0,14}(부모|부모님)", text):
        return True
    if _has_any(text, FAMILY_CONTEXT_TERMS):
        return True
    if re.search(r"(수유실|기저귀\s*교환대|기저귀\s*갈).{0,18}(없으면|안\s*보이면).{0,18}(수유실|기저귀\s*교환대|기저귀\s*갈)", text):
        return True
    if _has_any(text, FAMILY_FACILITY_TERMS):
        return bool(re.search(r"(아이|아기|영유아|가족|동반|데리고|같이|함께|돌봄|수유|기저귀).{0,12}(편한|편하|좋|쉬|부담|동선|여행)", text))
    return False


def _looks_like_mobility_context(text: str) -> bool:
    original_text = text
    text = _active_requirement_text(text)
    if re.search(r"유모차\s*대여", text) and not re.search(
        r"(유모차로|유아차로|바퀴|이동|동선|보행|걷|계단|턱|오래 걷|부담|움직이기)",
        text,
    ):
        return False
    if (
        "휠체어 접근" in text
        and re.search(r"(만 있고|없으면 안|둘 다|둘\s*중|는 물론|까지 근거|빠지면 곤란|동시에 확인|같이 확인)", text)
        and not re.search(r"(휠체어로|휠체어\s*이동|이동|동선|보행|걷|계단|턱|오래 걷|부담|움직이기)", text)
    ):
        return False
    if (
        re.search(r"(경사로|엘리베이터|승강기|장애인 화장실|장애인 주차).{0,12}(참고만|덤|있으면 좋|필수는 아니|꼭 맞출 필요는 없어)", text)
        and not re.search(r"(휠체어|전동휠체어|유모차|유아차|어르신|노약자|계단|턱|이동|동선|보행|걷)", text)
    ):
        return False
    if re.search(r"(조건을 말한 건 아니고|시설 요청은 아니|얘기가 아니라|근거\s*찾지\s*말고)", text):
        return False
    if (
        re.search(
            r"(수유실|기저귀|유아용 의자).{0,8}보다.{0,18}(가족|아이|아기|영유아|어린이).{0,14}(지치지 않는|쉬운|편한).{0,8}동선",
            text,
        )
        and not re.search(r"(휠체어|전동휠체어|유모차|유아차|어르신|노약자|계단|턱|경사로|엘리베이터|승강기)", text)
    ):
        return False
    if _has_any(text, MOBILITY_CONTEXT_TERMS) or _has_any(
        original_text,
        [
            "오래 걷",
            "덜 걷",
            "무릎이 불편",
            "발목 다친",
            "오르막",
            "오르내림",
            "이동 거리가 짧",
            "이동 반경",
            "넓게 볼",
            "넓게 움직",
            "오래 서서",
            "오래 줄 서지",
            "바로 둘러",
            "걷는 시간이 짧",
            "걷는 거리가 짧",
            "앉아 쉴",
            "잠깐 쉬어",
            "벤치",
            "덜 피곤",
            "이동이 버겁지",
            "걷기 부담",
            "평지",
            "짧은 나들이",
        ],
    ):
        return True
    if _has_any(text, MOBILITY_FACILITY_TERMS) and (
        sum(1 for term in MOBILITY_FACILITY_TERMS if term in text) >= 2
        or re.search(r"두\s*근거가.{0,12}(같이|함께).{0,10}(있어야|확인)", text)
        or re.search(r"(바퀴|이동|동선|부담|휠체어|유모차|유아차|어르신|노약자)", text)
    ):
        return True
    if _has_any(text, MOBILITY_FACILITY_TERMS):
        return bool(re.search(r"(이동|동선|보행|걷|계단|턱|휠체어|유모차|어르신|노약자|편|쉬|부담)", text))
    return False


def _looks_like_specific_facility_required(text: str) -> bool:
    if re.search(
        r"(수유\s*공간|수유실|기저귀\s*교환대|기저귀\s*갈).{0,18}(없으면|안\s*보이면|없다면).{0,18}(수유\s*공간|수유실|기저귀\s*교환대|기저귀\s*갈).{0,12}(라도|확인)",
        text,
    ):
        return True
    if re.search(
        r"(작품\s*제목|작품\s*설명|상호|상호명|별명|캐릭터|테마\s*전시).{0,16}(점자|수어|보조견|엘리베이터|화장실).{0,16}(아니라|말고).{0,24}(실제|편의정보|안내\s*여부|동반\s*가능|여부가\s*필요)",
        text,
    ):
        return True
    if (
        _has_any(text, SPECIFIC_FACILITY_TERMS)
        and re.search(r"(두\s*근거|둘\s*다|둘이\s*함께|같이|함께|하나라도\s*빠지면|표기된\s*곳)", text)
        and not re.search(r"(필수는\s*아니|필수로\s*묶지|부가\s*조건|선택\s*조건|참고|덤|후보\s*많을\s*때만|없으면\s*넘어)", text)
    ):
        return True
    if re.search(
        r"(점자|수어|보조견|엘리베이터).{0,16}(느낌|이름|작품명|작품\s*설명|상호|상호명|별명|캐릭터|음악|얘기|이야기).{0,16}(아니라|말고).{0,24}(편의정보|안내\s*여부|실제)",
        text,
    ):
        return True
    if re.search(
        r"(작품\s*설명|상호|상호명|별명|캐릭터).{0,16}(아니라|말고).{0,24}(점자|수어|보조견|안내견|엘리베이터|화장실|주차|수유|기저귀).{0,16}(편의정보|안내|동반\s*가능|여부|근거)",
        text,
    ):
        return True
    if re.search(
        r"(점자블록|점자|촉지도|음성안내|오디오가이드|수어|수화|자막|문자안내|영상안내|보조견|안내견|장애인 주차|장애인주차|주차장|장애인 화장실|화장실|엘리베이터|엘베|승강기|경사로|수유실|기저귀|유아용 의자|유아 의자|유모차 대여|휠체어 접근).{0,24}만\s*있거나.{0,24}(점자블록|점자|촉지도|음성안내|오디오가이드|수어|수화|자막|문자안내|영상안내|보조견|안내견|장애인 주차|장애인주차|주차장|장애인 화장실|화장실|엘리베이터|엘베|승강기|경사로|수유실|기저귀|유아용 의자|유아 의자|유모차 대여|휠체어 접근).{0,24}만\s*있는.{0,24}말고.{0,20}(둘이\s*함께|함께\s*있는|같이\s*있는|둘\s*다)",
        text,
    ):
        return True
    if re.search(
        r"(점자블록|점자|촉지도|음성안내|오디오가이드|수어|수화|자막|문자안내|영상안내|보조견|안내견|장애인 주차|장애인주차|주차장|장애인 화장실|화장실|엘리베이터|엘베|승강기|경사로|수유실|기저귀|유아용 의자|유아 의자|유모차 대여|휠체어 접근).{0,40}둘\s*중\s*하나만\s*되는\s*곳은\s*제외",
        text,
    ):
        return True
    text = _active_requirement_text(text)
    if "수어지교" in text:
        return False
    if re.search(
        r"(시설\s*요청은\s*아니|조건을\s*말한\s*건\s*아니고|조건은\s*아니|조건은\s*아냐|라는\s*(?:단어|작품명|이름).{0,12}(?:들어가도|있어도)|이라는\s*전시\s*제목|캐릭터\s*전시\s*제목|상호명일\s*뿐|편의정보로\s*보지\s*마|편의조건으로\s*보지\s*마|접근성\s*조건은\s*아냐|조건은\s*묻지\s*않|조건은\s*묻지\s*마|시설\s*조건은\s*새로\s*추가하지\s*마|조건은\s*새로\s*추가하지\s*마|조건은\s*필요\s*없|근거\s*찾지\s*말고)",
        text,
    ):
        return False
    if re.search(r"(접근성|편의정보|편의조건|시설|주차|화장실).{0,10}(얘기는\s*아냐|얘기가\s*아니|조건\s*아님|조건을\s*묻는\s*건\s*아니|세지\s*마)", text):
        return False
    if re.search(r"(점자블록|점자|촉지도|음성안내|오디오가이드|수어|수화|자막|문자안내|영상안내|보조견|안내견|장애인 주차|장애인주차|주차장|장애인 화장실|화장실|엘리베이터|승강기|경사로|수유실|기저귀|유아용 의자|유모차 대여|휠체어 접근).{0,12}(이 아니라|가 아니라|얘기가 아니라|조건을 말한 건 아니|조건\s*아님|근거 찾지 말고|말고 주제|말고 분위기)", text):
        return False
    if re.search(
        r"(화장실|주차|수어|자막|점자|경사로|엘리베이터|엘베|수유실|수유\s*공간|기저귀|유아용 의자|유아 의자|아이용 의자).{0,30}(느낌|참고|참고\s*수준|덤|가산점|가산점으로만|보조\s*조건|부가\s*조건|선택\s*조건|필수까진 아니|필수로\s*보진\s*말|필수로\s*묶지|필수로\s*묶진\s*마|있으면 더 좋|같이 고려|괜찮은 후보|둘 다 말하긴 했지만|가능한 후보부터|후보가?\s*많을\s*때만|후보가?\s*여럿일\s*때만|고려해|보자|넘어가도|넘어가자|없어도)",
        text,
    ):
        return False
    if re.search(r"(점자블록|점자|촉지도|음성안내|오디오가이드|수어|수화|자막|문자안내|영상안내|보조견|안내견|장애인 주차|장애인주차|주차장|장애인 화장실|화장실|엘리베이터|승강기|경사로|수유실|기저귀|유아용 의자|유모차 대여|휠체어 접근).{0,18}후보가\s*적을\s*때만\s*참고", text):
        return False
    if re.search(r"(필수는 아니|필수까진 아니|필수 아님|필수로\s*보진\s*말|필수로\s*묶지|필수로\s*묶진\s*마|보조\s*조건|부가\s*조건|선택\s*조건|참고만|참고\s*수준|은 참고|는 참고|있으면 참고|없으면 넘어가도|없으면 넘어가자|후보가?\s*많을\s*때만|후보가?\s*여럿일\s*때만|없어도 된다|없어도|꼭 맞출 필요는 없어|가산점|가산점으로만|덤)", text):
        return False
    if re.search(r"(수유실|기저귀|유아용 의자|유아 의자|아이용 의자|화장실|주차|점자|수어|자막|경사로|엘리베이터).{0,8}보다.{0,20}중요", text):
        return False
    if re.search(r"(확인되면|있으면|되면|보이면).{0,8}(좋|가점|참고|고려)", text):
        return False
    return _has_any(text, SPECIFIC_FACILITY_TERMS)


def _looks_like_or_condition(text: str) -> bool:
    if _looks_like_strict_and(text):
        return False
    if re.search(r"없으면.{0,10}(후보로\s*세지\s*마|후보에서\s*빼|추천하지\s*마)", text):
        return False
    if re.search(r"근거\s*없으면.{0,12}제외", text):
        return False
    if re.search(r"(느낌|성격|위주).{0,8}아니면", text):
        return False
    if _has_any(text, OR_MARKERS):
        return True
    if re.search(r"(없으면|없다면).{0,18}(라도|가능|괜찮|후보|넣어)", text):
        return True
    if re.search(r"(베스트|제일\s*좋).{0,16}(없으면|안되면).{0,18}(라도|괜찮|넣어)", text):
        return True
    if re.search(r"(든|이든).{0,14}(하나만|하나라도|근거\s*하나)", text):
        return True
    return bool(
        re.search(
            r"(수어|수화|자막|점자|촉지도|음성|오디오|보조견|안내견|화장실|주차).{0,8}(나|이나|거나).{0,8}(수어|수화|자막|점자|촉지도|음성|오디오|보조견|안내견|화장실|주차)",
            text,
        )
    )


def _looks_like_replace(text: str) -> bool:
    if "추측하지 말고" in text:
        return False
    if re.search(r"(야외|실외|붐비|숙박|음식점|카페|시장|계단\s*많|오래\s*걷).{0,14}(빼고|제외하고).{0,20}(실내|조용|관람|산책|관광|평지|넓게|쉬운\s*동선|한적)", text):
        return False
    if re.search(r"새\s*지역\s*말고\s*같은\s*결과", text):
        return False
    if re.search(r"(가능성|따로따로|추천하지|근거\s*찾지|남은\s*관광지만)\s*말고", text):
        return False
    if re.search(r"말고.{0,12}남은\s*관광지만", text):
        return False
    if re.search(r"(지역|조건|기준).{0,8}말고.{0,16}(에서|쪽|위주|기준)", text):
        return True
    if re.search(r"[가-힣]{2,}(?:\s*시|\s*군|\s*구)?\s*말고\s*[가-힣]{2,}(?:\s*시|\s*군|\s*구)?에서", text):
        return True
    if re.search(r"(그만\s*보고|접고|내려놓고).{0,24}(중심|위주|코스|기준)", text):
        return True
    if _has_any(text, REPLACE_MARKERS):
        return True
    return bool(re.search(r"(말고|빼고).{0,20}(로|으로|쪽|위주|기준)", text))


def _looks_like_exclude(text: str) -> bool:
    if "추측하지 말고" in text:
        return False
    if re.search(r"(추측|짐작|상상|확대해석)(?:하지)?\s*말고", text):
        return False
    if re.search(r"(이름|상호|상호명|음악|얘기|이야기|작품명|작품\s*설명|별명|캐릭터|브랜드명|노래\s*제목|행사).{0,12}(말고|빼고)", text):
        return False
    if re.search(r"둘\s*중\s*하나만\s*되는\s*곳은\s*제외", text):
        return False
    if _looks_like_strict_and(text) and re.search(r"(말고|빼고|제외).{0,24}(둘\s*다|두\s*근거|같이|함께|표기된)", text):
        return False
    if _looks_like_strict_and(text) and re.search(r"(둘\s*중\s*하나|하나라도).{0,12}빠지면.{0,12}(제외|빼|패스)", text):
        return False
    if re.search(r"(만\s*있거나|만\s*있는).{0,24}말고.{0,20}(둘이\s*함께|함께\s*있는|같이\s*있는|둘\s*다)", text):
        return False
    if re.search(r"[가-힣]{2,}(?:\s*시|\s*군|\s*구)?\s*말고\s*[가-힣]{2,}(?:\s*시|\s*군|\s*구)?에서", text):
        return False
    if re.search(r"(조건|시설|대여).{0,8}말고.{0,20}(분위기|쉬기|아이|가족|관광지|주제)", text):
        return False
    if _looks_like_strict_and(text) and re.search(r"(아니면|아니라면).{0,12}(빼|제외|패스)", text):
        return False
    if re.search(r"(근거\s*없으면|하나라도\s*근거\s*없으면).{0,12}(제외|빼)", text):
        return False
    if re.search(r"(동시에\s*확인된|둘\s*다\s*확인된|같이\s*확인된).{0,12}후보\s*아니면\s*제외", text):
        return False
    if re.search(r"근거\s*찾지\s*말고", text):
        return False
    if re.search(r"새\s*지역\s*말고\s*같은\s*결과", text):
        return False
    if re.search(r"(가능성|따로따로|추천하지)\s*말고", text):
        return False
    if re.search(r"(주차|화장실|점자|수어|자막).{0,8}(말고|얘기|이야기).{0,8}(주제|풍경|분위기|관광지)", text):
        return False
    if re.search(r"(휠체어|전동휠체어|유모차|유아차|어르신|노약자).{0,12}기준\s*동선만\s*보고\s*아이\s*편의는\s*빼", text):
        return False
    if re.search(r"(성격|위주\s*결과|느낌만|골목|숙박|음식점|카페|야외|붐비|계단\s*많).{0,12}(빼되|뒤로|아니면|제외|빼|패스|말고)", text):
        return True
    if re.search(r"말고.{0,12}남은\s*관광지만", text):
        return True
    return _has_any(text, EXCLUDE_MARKERS)


def _looks_like_add(text: str) -> bool:
    if "추측하지 말고" in text:
        return False
    if re.search(r"(시설명만|여부만|표시 여부만|조건은 필요하지만|근거만 있으면|근거\s*찾지\s*말고|근거\s*없으면.{0,12}(?:제외|추천하지\s*마)|라고\s*확인된\s*카드만|문구가\s*있어야|문구가.{0,12}원문에\s*있는\s*카드만|새로 추가하지 마|꼭 맞출 필요는 없어|필수까진 아니|필수로\s*보진\s*말|필수로\s*묶진\s*마|조건을 말한 건 아니|얘기가 아니라|시설 요청은 아니|둘\s*중\s*하나만\s*되는\s*곳은\s*제외)", text):
        return False
    if re.search(r"(확인되면|있으면|보이면|되면).{0,10}(좋|가점|참고|고려|괜찮)", text):
        return False
    if _looks_like_soft_preference_phrase(text):
        return False
    if _looks_like_strict_and(text):
        return False
    if _looks_like_or_condition(text):
        return False
    if re.search(r"않아도\s*되는\s*(곳|장소|코스|후보)", text):
        return False
    if _looks_like_exclude(text) or _looks_like_replace(text):
        return False
    if re.search(r"(문구가\s*(?:카드|원문)에\s*있는지만|추측\s*말고\s*확인된\s*근거만)", text) and not re.search(
        r"(남겨|좁혀|걸어|필터|추가|더\s*봐|더\s*확인|같이\s*체크|되는지만\s*더)",
        text,
    ):
        return False
    if re.search(r"(확인\s*문구가\s*있는\s*후보|필드가\s*잡히는\s*장소)", text) and not re.search(
        r"(남겨|좁혀|필터|추가|더\s*봐|더\s*확인|같이\s*체크)",
        text,
    ):
        return False
    if re.search(r"(현재|기존|아까|위|그|전|이전)\s*(추천|카드|목록|후보|장소|결과)", text) and re.search(
        r"(더\s*봐|더\s*확인|같이\s*체크|필터|조건\s*추가|남겨|좁혀|유지하고|다시|추려|걸러)",
        text,
    ):
        return _mentions_condition(text)
    if re.search(r"(목록|후보|결과|카드|추천).{0,12}(안에서|중|에|에서).{0,40}(조건|필터|근거|문구|남겨|좁혀|체크|확인|추려|걸러)", text):
        return _mentions_condition(text)
    explicit_add_markers = [
        marker
        for marker in ADD_MARKERS
        if marker not in {"있는 곳", "되는 곳", "도 가능"}
    ]
    return _has_any(text, explicit_add_markers) and _mentions_condition(text)


def _mentions_condition(text: str) -> bool:
    return any(term in text for group in CONDITION_GROUP_TERMS for term in group) or _has_any(text, SPECIFIC_FACILITY_TERMS)


def _looks_like_soft_and(text: str, labels: set[str]) -> bool:
    if labels & {"strict_and", "or_condition", "add_condition", "replace_condition", "exclude_condition"}:
        return False
    if re.search(r"(근거만 있으면|근거 없으면|시설명만|문구가 카드에 있는지만|표시 여부만|동반자 맥락은 아냐|가족 여행은 아니)", text):
        return False
    if re.search(r"(대기 길지 않은 곳이면 좋|아이디어만|모두가 좋아할|모두 좋아할|전부 좋아할)", text):
        return False
    if re.search(r"(가족\s*편의는\s*상관없|아이\s*편의는\s*빼줘)", text):
        return False
    if (
        re.search(r"(조건을 말한 건 아니고|얘기가 아니라|근거\s*찾지\s*말고)", text)
        and re.search(r"(전시|분위기|중심|좋은 곳)", text)
        and not _looks_like_soft_preference_phrase(text)
    ):
        return False
    text = _active_requirement_text(text)
    if _looks_like_soft_preference_phrase(text):
        return _mentions_condition(text)
    if re.search(r"(우선|먼저|위주).{0,28}(있으면|보이면|후보\s*적|가산점|필수까진 아니|덤)", text):
        return _mentions_condition(text)
    if re.search(r"(필수까진 아니|필수로\s*보진\s*말|가산점|가산점으로만|보조\s*조건|참고\s*수준|덤으로|없으면 말고|있으면 고맙|좋으면 좋고)", text):
        return _mentions_condition(text)
    if re.search(r"(있으면\s*참고|없으면\s*그냥\s*넘어가도|없으면\s*넘어가도|없으면\s*넘어가자|필수로\s*묶지|필수로\s*묶진\s*마|참고만|덤으로만|후보가?\s*많을\s*때만\s*(?:고려|보자)|후보가?\s*여럿일\s*때만\s*(?:고려|보자)|부가\s*조건|선택\s*조건)", text):
        return _mentions_condition(text)
    if re.search(r"(보다는|보다).{0,32}(중요|우선|먼저)", text):
        return _mentions_condition(text)
    if re.search(r"(시설|의자|수유실|기저귀|교환대).{0,12}없어도.{0,24}(핵심|중요|흥미|편히|편한|쉬)", text):
        return _mentions_condition(text)
    if re.search(r"(찾는데|찾고|원하는데).{0,22}(도\s*)?참고만", text):
        return _mentions_condition(text)
    if re.search(r"(쉬운\s*곳이면\s*되고|보기\s*좋은\s*곳이면).{0,28}(필수\s*아님|없어도\s*된다|참고)", text):
        return _mentions_condition(text)
    if re.search(r"(느낌|분위기).{0,10}같이\s*고려", text):
        return _mentions_condition(text)
    if re.search(r"(위주로\s*보되|쪽이면\s*좋고).{0,28}(있으면|섞어|더 좋|필수는 아니)", text):
        return _mentions_condition(text)
    if re.search(r"둘\s*다\s*말하긴\s*했지만.{0,18}(가능한\s*후보|후보부터|되는\s*후보)", text):
        return _mentions_condition(text)
    if re.search(
        r"(휠체어|유모차|유아차|어르신|점자|수어|자막|주차|화장실|경사로|엘리베이터|승강기).{0,10}(와|과|랑|하고).{0,18}(휠체어|유모차|유아차|어르신|점자|수어|자막|주차|화장실|경사로|엘리베이터|승강기)",
        text,
    ):
        return _mentions_condition(text)
    return False


def _looks_like_soft_preference_phrase(text: str) -> bool:
    return bool(
        re.search(r"(제일 중요|우선|위주|먼저).{0,28}(참고|덤|필수 아님|필수는 아니|꼭 맞출 필요는 없어|있으면 좋)", text)
        or re.search(r"(참고|덤|필수 아님|필수는 아니|꼭 맞출 필요는 없어|있으면 좋).{0,28}(제일 중요|우선|위주|먼저)", text)
        or re.search(r"(만 맞아도 괜찮|면 충분).{0,28}(있으면 좋|덤|참고|필수는 아니)", text)
        or re.search(r"(우선|먼저|핵심|목적).{0,36}(확인되면|보이면|있으면|가능하면).{0,10}(좋|가점|참고|고려)", text)
        or re.search(r"(확인되면|보이면|있으면|가능하면).{0,10}(좋|가점|참고|고려).{0,36}(우선|먼저|핵심|목적)", text)
    )


def _active_requirement_text(text: str) -> str:
    """Return the part that describes the requested replacement condition."""
    markers = [
        "말고",
        "빼고",
        "대신",
        "제외하고",
        "취소하고",
        "그만하고",
        "내려놓고",
        "잊고",
        "버리고",
        "더 보지 말고",
        "대신 이제",
        "별로라",
    ]
    candidates: list[tuple[int, str]] = []
    for marker in markers:
        index = text.rfind(marker)
        if index >= 0:
            if marker == "말고" and re.search(r"(추측|짐작|상상|확대해석)(?:하지)?\s*$", text[:index]):
                continue
            if marker == "말고" and re.search(r"(가능성|따로따로|추천하지|근거\s*찾지)\s*$", text[:index]):
                continue
            candidates.append((index, text[index + len(marker) :]))
    if not candidates:
        return text
    _, active = max(candidates, key=lambda item: item[0])
    return active.strip() or text
