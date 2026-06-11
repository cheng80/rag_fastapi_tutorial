from __future__ import annotations

from dataclasses import dataclass
import re


@dataclass(frozen=True)
class NormalizedQuery:
    raw_text: str
    normalized_text: str
    rewrite_text: str
    corrections: list[str]
    risk_tags: list[str]

    @property
    def changed(self) -> bool:
        return self.raw_text != self.normalized_text


class KoreanQueryNormalizer:
    """Deterministic Korean query normalization for tourism NLU.

    This is deliberately conservative: it does not invent missing intent, and it
    keeps the original text available for logging and parallel interpretation.
    """

    TYPO_REPLACEMENTS = {
        "휄체어": "휠체어",
        "휄체여": "휠체어",
        "휄채어": "휠체어",
        "휠쳐": "휠체어",
        "휠체 어": "휠체어",
        "휠 체어": "휠체어",
        "휠체여": "휠체어",
        "휠채어": "휠체어",
        "휠체어어": "휠체어",
        "유모챠": "유모차",
        "유모 차": "유모차",
        "유아챠": "유아차",
        "유아 차": "유아차",
        "애기랑": "아기랑",
        "아가랑": "아기랑",
        "엘베": "엘리베이터",
        "엘리배이터": "엘리베이터",
        "앨리베이터": "엘리베이터",
        "엘리 베이터": "엘리베이터",
        "승강끼": "승강기",
        "승 강기": "승강기",
        "경 사로": "경사로",
        "접근 로": "접근로",
        "출입 통로": "출입통로",
        "무 단차": "무단차",
        "턱없음": "턱 없음",
        "점자안내": "점자 안내",
        "점자블럭": "점자블록",
        "촉 지 도": "촉지도",
        "수어안내": "수어 안내",
        "수화안내": "수화 안내",
        "자막안내": "자막 안내",
        "자 막": "자막",
        "문자 안내": "문자안내",
        "영상 안내": "영상안내",
        "음성안내": "음성 안내",
        "음성 안내": "음성안내",
        "장애 인": "장애인",
        "청각 장애": "청각장애",
        "시각 장애": "시각장애",
        "장애인화장실": "장애인 화장실",
        "장애인주차": "장애인 주차",
        "장애인주챠": "장애인 주차",
        "주 차": "주차",
        "주챠": "주차",
        "주차ㅏ": "주차",
        "주자창": "주차장",
        "기저기": "기저귀",
        "수유 실": "수유실",
        "보조갼": "보조견",
        "보조 견": "보조견",
        "안내 견": "안내견",
        "부모 님": "부모님",
        "고령 자": "고령자",
        "어르 신": "어르신",
        "무릅 불편": "무릎 불편",
        "무릅불편": "무릎 불편",
        "가능한곳": "가능한 곳",
        "되는곳": "되는 곳",
        "있는곳": "있는 곳",
        "갈만한곳": "갈 만한 곳",
        "볼수있나": "볼 수 있나",
        "찾아바줘": "찾아봐줘",
        "추천좀": "추천해줘",
        "곳추천": "곳 추천",
        "청 원군": "청원군",
        "마 산시": "마산시",
        "진 해시": "진해시",
        "남 제주군": "남제주군",
        "북 제주군": "북제주군",
    }
    TOKEN_HINTS = [
        "휠체어",
        "유모차",
        "유아차",
        "전동휠체어",
        "바퀴 의자",
        "바퀴의자",
        "어르신",
        "고령자",
        "부모님",
        "장애인",
        "무장애",
        "점자",
        "점자 안내",
        "수어",
        "수어 안내",
        "수화",
        "자막",
        "문자안내",
        "영상안내",
        "장애인 화장실",
        "화장실",
        "장애인 주차",
        "주차",
        "엘리베이터",
        "승강기",
        "경사로",
        "접근로",
        "출입통로",
        "무단차",
        "턱 없음",
        "평탄한 길",
        "수유실",
        "기저귀",
        "박물관",
        "미술관",
        "전시관",
        "공원",
        "시장",
        "카페",
        "맛집",
        "숙박",
        "숲길",
        "산책",
        "실내",
        "말고",
        "빼고",
        "제외",
        "대신",
        "바꿔",
        "또는",
        "혹은",
        "아니면",
        "둘다",
        "둘 다",
        "모두",
        "반드시",
        "꼭",
        "추천해줘",
        "찾아줘",
        "보여줘",
    ]
    PHRASE_REPLACEMENTS = {
        "둘다": "둘 다",
        "장애인 주차장": "장애인 주차장",
        "주차 장": "주차장",
        "화장 실": "화장실",
        "수유 실": "수유실",
        "기저귀 교환 대": "기저귀 교환대",
        "오디오 가이드": "오디오가이드",
        "바퀴의자": "바퀴 의자",
        "무릎불편": "무릎 불편",
        "평탄한길": "평탄한 길",
        "청 원 군": "청원군",
        "마 산 시": "마산시",
        "진 해 시": "진해시",
        "남 제주 군": "남제주군",
        "북 제주 군": "북제주군",
        "청원 군": "청원군",
        "마산 시": "마산시",
        "진해 시": "진해시",
        "남제주 군": "남제주군",
        "북제주 군": "북제주군",
    }
    PARTICLE_SPACING = [
        ("말고", "말고"),
        ("빼고", "빼고"),
        ("제외", "제외"),
        ("대신", "대신"),
        ("아니면", "아니면"),
        ("또는", "또는"),
        ("혹은", "혹은"),
    ]

    def normalize(self, text: str, region_names: list[str] | None = None) -> NormalizedQuery:
        raw = " ".join(str(text or "").strip().split())
        normalized = raw
        corrections: list[str] = []
        risk_tags: list[str] = []

        if not raw:
            return NormalizedQuery(raw_text=raw, normalized_text=raw, rewrite_text=raw, corrections=[], risk_tags=[])

        if re.search(r"[가-힣]{10,}", raw.replace(" ", "")) and " " not in raw:
            risk_tags.append("no-spacing-input")
        elif _has_spacing_noise(raw):
            risk_tags.append("spacing-noise-input")

        for source, target in self.TYPO_REPLACEMENTS.items():
            if source in normalized:
                normalized = normalized.replace(source, target)
                corrections.append(f"{source}->{target}")

        normalized = self._restore_boundaries(normalized, region_names or [])
        normalized = re.sub(r"\s+", " ", normalized).strip()
        for source, target in self.PHRASE_REPLACEMENTS.items():
            if source in normalized:
                normalized = normalized.replace(source, target)
        for source, target in self.TYPO_REPLACEMENTS.items():
            if source in normalized:
                normalized = normalized.replace(source, target)
        normalized = re.sub(r"\s+", " ", normalized).strip()

        if normalized != raw and not any(tag.startswith("normalization") for tag in risk_tags):
            risk_tags.append("normalization-applied")

        return NormalizedQuery(
            raw_text=raw,
            normalized_text=normalized,
            rewrite_text=self._rewrite(normalized),
            corrections=corrections,
            risk_tags=risk_tags,
        )

    def _restore_boundaries(self, text: str, region_names: list[str]) -> str:
        restored = text
        hints = sorted(set(region_names + self.TOKEN_HINTS), key=len, reverse=True)
        for hint in hints:
            if not hint:
                continue
            compact_hint = hint.replace(" ", "")
            restored = re.sub(rf"(?<!\s){re.escape(compact_hint)}(?!\s)", f" {hint} ", restored)
        for source, target in self.PARTICLE_SPACING:
            restored = restored.replace(source, f" {target} ")
        return restored

    @staticmethod
    def _rewrite(text: str) -> str:
        rewritten = text
        rewritten = rewritten.replace("쪽으로", "지역으로")
        rewritten = rewritten.replace("가능?", "가능한 곳")
        rewritten = rewritten.replace("부탁", "추천해줘")
        rewritten = rewritten.replace("좀", "")
        return re.sub(r"\s+", " ", rewritten).strip()


def _has_spacing_noise(text: str) -> bool:
    compact = text.replace(" ", "")
    if len(compact) < 8:
        return False
    return any(pattern in text for pattern in ["  ", "장애 인", "유아 차", "화장 실", "수유 실"]) or bool(
        re.search(r"[가-힣]+(말고|빼고|되는곳|가능한곳|있는곳|추천좀|볼수있나)", text)
    )
