from pathlib import Path

from scripts.restore_optional_models import copy_spec, CopySpec


def test_copy_spec_restores_directory_when_destination_is_missing(tmp_path):
    original_root = tmp_path / "original"
    project_root = tmp_path / "template"
    relative_path = Path("data/models/tourism_korean_corrector")
    source = original_root / relative_path
    source.mkdir(parents=True)
    (source / "config.json").write_text("{}", encoding="utf-8")
    (source / ".DS_Store").write_text("ignored", encoding="utf-8")

    copy_spec(
        spec=CopySpec(label="test model", relative_path=relative_path),
        original_root=original_root,
        project_root=project_root,
        force=False,
    )

    destination = project_root / relative_path
    assert (destination / "config.json").read_text(encoding="utf-8") == "{}"
    assert not (destination / ".DS_Store").exists()


def test_copy_spec_skips_existing_directory_without_force(tmp_path):
    original_root = tmp_path / "original"
    project_root = tmp_path / "template"
    relative_path = Path("data/models/tourism_korean_corrector")
    source = original_root / relative_path
    destination = project_root / relative_path
    source.mkdir(parents=True)
    destination.mkdir(parents=True)
    (source / "config.json").write_text('{"source": true}', encoding="utf-8")
    (destination / "config.json").write_text('{"existing": true}', encoding="utf-8")

    copy_spec(
        spec=CopySpec(label="test model", relative_path=relative_path),
        original_root=original_root,
        project_root=project_root,
        force=False,
    )

    assert (destination / "config.json").read_text(encoding="utf-8") == '{"existing": true}'
