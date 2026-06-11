from __future__ import annotations

from app.schemas.tourism import AccessibilityInfo, TourismPlaceCard


ACCESSIBILITY_FIELD_LABELS = {
    "parking": "주차",
    "route": "접근로",
    "publictransport": "대중교통",
    "ticketoffice": "매표소",
    "promotion": "홍보물",
    "wheelchair": "휠체어",
    "exit": "출입통로",
    "elevator": "엘리베이터",
    "restroom": "화장실",
    "auditorium": "관람석",
    "room": "객실",
    "handicapetc": "기타 장애인 편의",
    "braileblock": "점자블록",
    "helpdog": "보조견",
    "guidehuman": "안내요원",
    "audioguide": "오디오가이드",
    "bigprint": "큰활자",
    "brailepromotion": "점자홍보물",
    "guidesystem": "안내시스템",
    "blindhandicapetc": "시각장애 편의",
    "signguide": "수어안내",
    "videoguide": "자막/영상안내",
    "hearingroom": "청각장애 객실",
    "hearinghandicapetc": "청각장애 편의",
    "stroller": "유모차",
    "lactationroom": "수유실",
    "babysparechair": "유아용 의자",
    "infantsfamilyetc": "영유아 가족 편의",
}


class TourismCardMarkdownCodec:
    def to_markdown(self, card: TourismPlaceCard) -> str:
        accessibility_lines = [
            f"- {ACCESSIBILITY_FIELD_LABELS.get(key, key)}: {value}"
            for key, value in card.raw_fields.items()
        ]
        if not accessibility_lines:
            accessibility_lines = ["- 확인 필요: 세부 편의정보가 없습니다."]

        return "\n".join(
            [
                f"# {card.title}",
                "",
                f"관광지명: {card.title}",
                f"콘텐츠ID: {card.content_id}",
                f"주소: {card.address or '확인 필요'}",
                f"전화번호: {card.tel or '확인 필요'}",
                f"지도X: {card.map_x if card.map_x is not None else '확인 필요'}",
                f"지도Y: {card.map_y if card.map_y is not None else '확인 필요'}",
                f"대표이미지: {card.image_url or '확인 필요'}",
                f"추천근거: {card.recommendation_reason}",
                f"접근성태그: {', '.join(card.accessibility_tags) if card.accessibility_tags else '확인 필요'}",
                f"가족태그: {', '.join(card.family_tags) if card.family_tags else '확인 필요'}",
                f"출처: {card.source_name}",
                f"출처URL: {card.source_url or '확인 필요'}",
                "",
                "편의정보:",
                *accessibility_lines,
                "",
            ]
        )

    def from_markdown(self, text: str) -> TourismPlaceCard | None:
        fields: dict[str, str] = {}
        raw_fields: dict[str, str] = {}
        in_facilities = False
        for line in text.splitlines():
            stripped = line.strip()
            if stripped == "편의정보:":
                in_facilities = True
                continue
            if in_facilities and stripped.startswith("- ") and ":" in stripped:
                key, value = stripped[2:].split(":", 1)
                if value.strip() and value.strip() != "확인 필요":
                    raw_fields[key.strip()] = value.strip()
                continue
            if ":" in stripped:
                key, value = stripped.split(":", 1)
                fields[key.strip()] = value.strip()

        title = fields.get("관광지명")
        content_id = fields.get("콘텐츠ID")
        if not title or not content_id:
            return None

        return TourismPlaceCard(
            content_id=content_id,
            title=title,
            address=self._none_if_unknown(fields.get("주소")),
            image_url=self._none_if_unknown(fields.get("대표이미지")),
            tel=self._none_if_unknown(fields.get("전화번호")),
            map_x=self._optional_float(fields.get("지도X") or fields.get("map_x") or fields.get("mapx")),
            map_y=self._optional_float(fields.get("지도Y") or fields.get("map_y") or fields.get("mapy")),
            recommendation_reason=fields.get("추천근거") or f"{title}은(는) 무장애 여행 정보에 포함된 관광지입니다.",
            accessibility=AccessibilityInfo(
                wheelchair=self._find_raw(raw_fields, ["휠체어", "출입통로"]),
                parking=self._find_raw(raw_fields, ["주차"]),
                restroom=self._find_raw(raw_fields, ["화장실"]),
                stroller=self._find_raw(raw_fields, ["유모차"]),
                nursing_room=self._find_raw(raw_fields, ["수유실"]),
                elevator=self._find_raw(raw_fields, ["엘리베이터"]),
                route=self._find_raw(raw_fields, ["접근로", "대중교통"]),
            ),
            accessibility_tags=self._split_tags(fields.get("접근성태그")),
            family_tags=self._split_tags(fields.get("가족태그")),
            source_name=fields.get("출처") or "한국관광공사 무장애 여행 정보",
            source_url=self._none_if_unknown(fields.get("출처URL")),
            raw_fields=raw_fields,
        )

    @staticmethod
    def _split_tags(value: str | None) -> list[str]:
        if not value or value == "확인 필요":
            return []
        return [tag.strip() for tag in value.split(",") if tag.strip()]

    @staticmethod
    def _none_if_unknown(value: str | None) -> str | None:
        if not value or value == "확인 필요":
            return None
        return value

    @staticmethod
    def _optional_float(value: str | None) -> float | None:
        if not value or value == "확인 필요":
            return None
        try:
            return float(value)
        except ValueError:
            return None

    @staticmethod
    def _find_raw(raw_fields: dict[str, str], labels: list[str]) -> str | None:
        for label in labels:
            for key, value in raw_fields.items():
                if label in key:
                    return value
        return None
