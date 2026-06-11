from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from app.api.deps import get_vector_store  # noqa: E402


def main() -> None:
    vector_store = get_vector_store()
    vector_store.clear_collection()
    print("Chroma collection 초기화 완료")
    print(vector_store.stats())


if __name__ == "__main__":
    main()
