#!/usr/bin/env python3
"""Back up selected local Codex/agent skills into a portable directory."""

from __future__ import annotations

import argparse
import json
import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


@dataclass(frozen=True)
class SkillSpec:
    name: str
    source_dir: str
    backup_group: str


SKILLS = [
    SkillSpec("app-store-screenshots", "~/.codex/skills/app-store-screenshots", "codex"),
    SkillSpec("codex-subagent-skill", "~/.codex/skills/codex-subagent-skill", "codex"),
    SkillSpec("gstack-claude", "~/.codex/skills/gstack-claude", "codex"),
    SkillSpec("slidev", "~/.codex/skills/slidev", "codex"),
    SkillSpec("design-md", "~/.agents/skills/design-md", "agents"),
    SkillSpec("enhance-prompt", "~/.agents/skills/enhance-prompt", "agents"),
    SkillSpec("react-components", "~/.agents/skills/react-components", "agents"),
    SkillSpec("remotion", "~/.agents/skills/remotion", "agents"),
    SkillSpec("shadcn-ui", "~/.agents/skills/shadcn-ui", "agents"),
    SkillSpec("stitch-loop", "~/.agents/skills/stitch-loop", "agents"),
]


IGNORE_NAMES = {
    ".DS_Store",
    ".git",
    "__pycache__",
    "node_modules",
}


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def default_output_dir() -> Path:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    return repo_root() / "data" / "generated" / "skill_backups" / f"skills-backup-{stamp}"


def ignore_patterns(_: str, names: list[str]) -> set[str]:
    return {name for name in names if name in IGNORE_NAMES or name.endswith(".pyc")}


def copy_skill(src: Path, dst: Path) -> None:
    if dst.exists() or dst.is_symlink():
        shutil.rmtree(dst)
    shutil.copytree(src, dst, symlinks=False, ignore=ignore_patterns)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Back up selected ~/.codex/skills and ~/.agents/skills directories."
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=default_output_dir(),
        help="Backup output directory. Defaults to data/generated/skill_backups/skills-backup-<timestamp>.",
    )
    parser.add_argument(
        "--replace",
        action="store_true",
        help="Replace output directory if it already exists.",
    )
    parser.add_argument(
        "--allow-missing",
        action="store_true",
        help="Continue when a configured skill directory is missing.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print planned backup operations without copying files.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output_dir = args.output_dir.expanduser().resolve()

    if output_dir.exists():
        if not args.replace:
            raise SystemExit(f"backup directory already exists: {output_dir}")
        if not args.dry_run:
            shutil.rmtree(output_dir)

    manifest: dict[str, object] = {
        "version": 1,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "layout": {"codex": "codex/<skill-name>", "agents": "agents/<skill-name>"},
        "skills": [],
    }

    missing: list[str] = []

    for spec in SKILLS:
        src = Path(spec.source_dir).expanduser()
        dst = output_dir / spec.backup_group / spec.name
        entry = {
            "name": spec.name,
            "source": spec.source_dir,
            "group": spec.backup_group,
            "backup_path": f"{spec.backup_group}/{spec.name}",
            "present": src.exists() or src.is_symlink(),
        }

        if not (src.exists() or src.is_symlink()):
            missing.append(spec.name)
            manifest["skills"].append(entry)
            print(f"missing: {spec.source_dir}")
            continue

        print(f"backup: {spec.source_dir} -> {dst}")
        if not args.dry_run:
            dst.parent.mkdir(parents=True, exist_ok=True)
            copy_skill(src, dst)
        manifest["skills"].append(entry)

    if missing and not args.allow_missing:
        raise SystemExit(
            "missing configured skill(s): "
            + ", ".join(missing)
            + " (rerun with --allow-missing to write a partial backup)"
        )

    if not args.dry_run:
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "manifest.json").write_text(
            json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

    print(f"backup_dir: {output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
