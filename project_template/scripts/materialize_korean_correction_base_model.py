from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.core.config import get_settings  # noqa: E402


DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "data" / "models" / "tourism_korean_corrector_base"


def copy_tree(source: Path, target: Path) -> None:
    if target.exists():
        shutil.rmtree(target)
    target.mkdir(parents=True, exist_ok=True)
    for item in source.iterdir():
        destination = target / item.name
        if item.is_dir():
            shutil.copytree(item, destination, symlinks=False)
        else:
            shutil.copy2(item, destination, follow_symlinks=True)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Download or materialize a Korean correction base model into a local project directory."
    )
    parser.add_argument("--model-name", default=get_settings().tourism_korean_correction_base_model)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument(
        "--local-files-only",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Use already cached files only. Default allows a one-time download during model preparation.",
    )
    args = parser.parse_args()

    from huggingface_hub import snapshot_download

    snapshot_path = Path(
        snapshot_download(
            repo_id=args.model_name,
            local_files_only=args.local_files_only,
            allow_patterns=[
                "config.json",
                "generation_config.json",
                "pytorch_model.bin",
                "model.safetensors",
                "spiece.model",
                "tokenizer_config.json",
                "special_tokens_map.json",
            ],
        )
    )
    copy_tree(snapshot_path, args.output_dir)
    manifest = {
        "source_model": args.model_name,
        "source_snapshot_revision": snapshot_path.name,
        "output_dir": str(args.output_dir.relative_to(PROJECT_ROOT)),
        "runtime_policy": "FastAPI must load this local directory or a fine-tuned derivative, not the remote model id.",
    }
    (args.output_dir / "materialize_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
