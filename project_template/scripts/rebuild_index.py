from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from app.api.deps import get_ingestion_service  # noqa: E402


def main() -> None:
    result = get_ingestion_service().ingest_directory(clear_existing=True)
    print("문서 재색인 완료")
    print(result)


if __name__ == "__main__":
    main()
