#!/usr/bin/env python3
"""Restore selected local Codex/agent skills from a portable backup directory."""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path


DEFAULT_DESTINATIONS = {
    "codex": "~/.codex/skills",
    "agents": "~/.agents/skills",
}


def load_manifest(backup_dir: Path) -> list[dict[str, object]]:
    manifest_path = backup_dir / "manifest.json"
    if not manifest_path.is_file():
        return discover_backup(backup_dir)

    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    skills = data.get("skills", [])
    if not isinstance(skills, list):
        raise SystemExit(f"invalid manifest skills list: {manifest_path}")
    return [skill for skill in skills if isinstance(skill, dict)]


def discover_backup(backup_dir: Path) -> list[dict[str, object]]:
    skills: list[dict[str, object]] = []
    for group in DEFAULT_DESTINATIONS:
        group_dir = backup_dir / group
        if not group_dir.is_dir():
            continue
        for skill_dir in sorted(group_dir.iterdir()):
            if skill_dir.is_dir():
                skills.append(
                    {
                        "name": skill_dir.name,
                        "group": group,
                        "backup_path": f"{group}/{skill_dir.name}",
                        "present": True,
                    }
                )
    return skills


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Restore selected ~/.codex/skills and ~/.agents/skills directories from backup."
    )
    parser.add_argument(
        "backup_dir",
        type=Path,
        help="Backup directory created by scripts/backup_selected_skills.py.",
    )
    parser.add_argument(
        "--replace",
        action="store_true",
        help="Replace existing destination skill directories.",
    )
    parser.add_argument(
        "--skip-existing",
        action="store_true",
        help="Keep existing destination skill directories and restore only missing skills.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print planned restore operations without copying files.",
    )
    return parser.parse_args()


def copy_skill(src: Path, dst: Path, replace: bool, skip_existing: bool, dry_run: bool) -> str:
    if dst.exists() or dst.is_symlink():
        if skip_existing:
            return "skipped-existing"
        if not replace:
            raise SystemExit(
                f"destination already exists: {dst} "
                "(use --replace to overwrite or --skip-existing to keep it)"
            )
        if not dry_run:
            if dst.is_dir() and not dst.is_symlink():
                shutil.rmtree(dst)
            else:
                dst.unlink()

    if not dry_run:
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(src, dst, symlinks=False)
    return "restored"


def main() -> int:
    args = parse_args()
    backup_dir = args.backup_dir.expanduser().resolve()

    if args.replace and args.skip_existing:
        raise SystemExit("--replace and --skip-existing cannot be used together")
    if not backup_dir.is_dir():
        raise SystemExit(f"backup directory not found: {backup_dir}")

    skills = load_manifest(backup_dir)
    if not skills:
        raise SystemExit(f"no skills found in backup directory: {backup_dir}")

    for skill in skills:
        if skill.get("present") is False:
            continue

        name = skill.get("name")
        group = skill.get("group")
        backup_path = skill.get("backup_path")
        if not isinstance(name, str) or not isinstance(group, str):
            raise SystemExit(f"invalid skill entry in manifest: {skill}")
        if group not in DEFAULT_DESTINATIONS:
            raise SystemExit(f"unknown backup group for {name}: {group}")

        rel_backup = backup_path if isinstance(backup_path, str) else f"{group}/{name}"
        src = backup_dir / rel_backup
        dst = Path(DEFAULT_DESTINATIONS[group]).expanduser() / name

        if not src.is_dir():
            raise SystemExit(f"backup skill directory not found: {src}")

        result = copy_skill(src, dst, args.replace, args.skip_existing, args.dry_run)
        print(f"{result}: {src} -> {dst}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
