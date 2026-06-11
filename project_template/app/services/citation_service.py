from app.schemas.chat import Source


class CitationService:
    def build_sources(self, contexts: list[dict]) -> list[Source]:
        sources: list[Source] = []
        seen: set[tuple[str, int | None, str]] = set()

        for item in contexts:
            metadata = item.get("metadata", {}) or {}
            raw_page = metadata.get("page")
            page = None if raw_page in (None, -1) else int(raw_page)
            source = str(metadata.get("source", ""))
            chunk_id = str(item.get("id", ""))
            chunk_index = metadata.get("chunk_index")
            distance = item.get("distance")

            key = (source, page, chunk_id)
            if key in seen:
                continue
            seen.add(key)

            sources.append(
                Source(
                    source=source,
                    page=page,
                    chunk_id=chunk_id,
                    chunk_index=int(chunk_index) if isinstance(chunk_index, int) else None,
                    distance=float(distance) if distance is not None else None,
                )
            )

        return sources
