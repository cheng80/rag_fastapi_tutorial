from __future__ import annotations

import argparse
import os
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Final, Sequence


PROJECT_ROOT: Final = Path(__file__).resolve().parents[1]
DEFAULT_ORIGINAL_APP_ROOT: Final = Path(
    os.environ.get("ORIGINAL_APP_ROOT", "/Users/cheng80/Desktop/chatbot_rag")
)


@dataclass(frozen=True, slots=True)
class CopySpec:
    label: str
    relative_path: Path


COPY_SPECS: Final = (
    CopySpec(
        label="한국어 교정 모델",
        relative_path=Path("data/models/tourism_korean_corrector"),
    ),
    CopySpec(
        label="관광 조건 변환기 모델",
        relative_path=Path(
            "data/generated/tour_api/condition_transformer_residual_aug_e2_fast"
        ),
    ),
)


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="원본 앱에서 선택형 로컬 모델 파일을 project_template로 복원합니다."
    )
    parser.add_argument(
        "--original-app-root",
        type=Path,
        default=DEFAULT_ORIGINAL_APP_ROOT,
        help="원본 앱 루트입니다. 기본값은 ORIGINAL_APP_ROOT 또는 /Users/cheng80/Desktop/chatbot_rag입니다.",
    )
    parser.add_argument(
        "--project-root",
        type=Path,
        default=PROJECT_ROOT,
        help="모델을 복원할 project_template 루트입니다.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="대상 디렉터리가 있으면 지운 뒤 다시 복사합니다.",
    )
    return parser.parse_args(argv)


def directory_size_bytes(path: Path) -> int:
    total = 0
    for current_root, _, files in os.walk(path):
        root_path = Path(current_root)
        for filename in files:
            file_path = root_path / filename
            try:
                total += file_path.stat().st_size
            except FileNotFoundError:
                continue
    return total


def human_size(byte_count: int) -> str:
    size = float(byte_count)
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024 or unit == "GB":
            return f"{size:.1f}{unit}"
        size /= 1024
    return f"{size:.1f}GB"


def copy_spec(spec: CopySpec, original_root: Path, project_root: Path, force: bool) -> None:
    source = original_root / spec.relative_path
    destination = project_root / spec.relative_path

    if not source.exists():
        raise FileNotFoundError(f"{spec.label} 원본 경로가 없습니다: {source}")
    if not source.is_dir():
        raise NotADirectoryError(f"{spec.label} 원본 경로가 디렉터리가 아닙니다: {source}")

    if destination.exists():
        if not force:
            copied_size = human_size(directory_size_bytes(destination))
            print(f"[skip] {spec.label}: 이미 있음 ({copied_size}) -> {destination}")
            return
        shutil.rmtree(destination)

    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(
        source,
        destination,
        ignore=shutil.ignore_patterns(".DS_Store", "__pycache__", "*.pyc"),
    )
    copied_size = human_size(directory_size_bytes(destination))
    print(f"[ok] {spec.label}: {copied_size} -> {destination}")


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    original_root = args.original_app_root.expanduser().resolve()
    project_root = args.project_root.expanduser().resolve()

    for spec in COPY_SPECS:
        copy_spec(
            spec=spec,
            original_root=original_root,
            project_root=project_root,
            force=args.force,
        )

    print("[done] 선택형 모델 복원이 끝났습니다.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
