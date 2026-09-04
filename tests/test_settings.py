"""Tests for reading, applying, backing up, and restoring settings.json."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from conftest import read_json, write_settings
from ttr_aspect_lock import constants
from ttr_aspect_lock.errors import (
    BackupNotFoundError,
    InvalidSettingsError,
    SettingsNotFoundError,
)
from ttr_aspect_lock.settings import (
    apply_aspect_ratio,
    available_backups,
    create_backup,
    latest_backup,
    read_settings,
    restore_settings,
)

TARGET = constants.TARGET_ASPECT_RATIO


def test_target_is_exactly_sixteen_ninths():
    assert TARGET == 16 / 9


def test_read_settings_returns_object(settings_file: Path):
    data = read_settings(settings_file)
    assert data["video"]["forced-aspect-ratio"] == 0.0


def test_read_settings_missing_file(tmp_path: Path):
    with pytest.raises(SettingsNotFoundError):
        read_settings(tmp_path / "nope.json")


@pytest.mark.parametrize("payload", ["[]", "null", '"text"', "{"])
def test_read_settings_rejects_non_object(tmp_path: Path, payload: str):
    path = tmp_path / "settings.json"
    path.write_text(payload, encoding="utf-8")
    with pytest.raises(InvalidSettingsError):
        read_settings(path)


def test_apply_sets_target_and_creates_backup(settings_file: Path):
    result = apply_aspect_ratio(settings_file)
    assert result.changed is True
    assert result.previous_value == 0.0
    assert result.backup_path is not None and result.backup_path.is_file()
    assert read_json(settings_file)["video"]["forced-aspect-ratio"] == TARGET
    # The backup keeps the pre-change value so restore is lossless.
    assert read_json(result.backup_path)["video"]["forced-aspect-ratio"] == 0.0


def test_apply_preserves_unrelated_keys(settings_file: Path):
    before = read_json(settings_file)
    apply_aspect_ratio(settings_file)
    after = read_json(settings_file)
    assert after["audio"] == before["audio"]
    assert after["toon"] == before["toon"]
    assert after["video"]["fullscreen"] is True


def test_apply_is_idempotent(settings_file: Path):
    apply_aspect_ratio(settings_file)
    second = apply_aspect_ratio(settings_file)
    assert second.changed is False
    assert second.backup_path is None
    assert len(available_backups(settings_file)) == 1


def test_apply_treats_near_target_float_as_already_locked(tmp_path: Path):
    # Status and install must agree: float noise near 16/9 is already locked.
    near = TARGET * (1 + 1e-12)
    assert near != TARGET
    path = write_settings(tmp_path / "settings.json", {"video": {"forced-aspect-ratio": near}})
    result = apply_aspect_ratio(path)
    assert result.changed is False
    assert result.backup_path is None
    assert available_backups(path) == []


def test_apply_dry_run_writes_nothing(settings_file: Path):
    original = settings_file.read_text(encoding="utf-8")
    result = apply_aspect_ratio(settings_file, dry_run=True)
    assert result.changed is True and result.dry_run is True
    assert result.backup_path is None
    assert settings_file.read_text(encoding="utf-8") == original
    assert available_backups(settings_file) == []


def test_apply_creates_missing_video_table(tmp_path: Path):
    path = write_settings(tmp_path / "settings.json", {"audio": {"music-volume": 1.0}})
    result = apply_aspect_ratio(path)
    assert result.previous_value is None
    assert read_json(path)["video"] == {"forced-aspect-ratio": TARGET}


def test_apply_rejects_non_object_video(tmp_path: Path):
    path = write_settings(tmp_path / "settings.json", {"video": "wide"})
    with pytest.raises(InvalidSettingsError):
        apply_aspect_ratio(path)


@pytest.mark.parametrize("ratio", [0, -1, "1.77", None, True])
def test_apply_rejects_invalid_ratio(settings_file: Path, ratio):
    with pytest.raises(ValueError):
        apply_aspect_ratio(settings_file, ratio)


def test_apply_preserves_indentation_and_trailing_newline(tmp_path: Path):
    path = write_settings(tmp_path / "settings.json", indent=4)
    apply_aspect_ratio(path)
    text = path.read_text(encoding="utf-8")
    assert text.endswith("\n")
    assert '\n    "video"' in text


def test_apply_uses_custom_backup_directory(settings_file: Path, tmp_path: Path):
    backups = tmp_path / "vault"
    result = apply_aspect_ratio(settings_file, backup_dir=backups)
    assert result.backup_path.parent == backups
    assert available_backups(settings_file, backups) == [result.backup_path]
    assert available_backups(settings_file) == []


def test_backup_names_are_unique(settings_file: Path):
    first = create_backup(settings_file)
    second = create_backup(settings_file)
    assert first != second
    assert len(available_backups(settings_file)) == 2


def test_available_backups_are_newest_first(settings_file: Path, tmp_path: Path):
    marker = f"settings.json{constants.BACKUP_MARKER}"
    for stamp in ("20240101T000000000000Z", "20260101T000000000000Z"):
        (settings_file.parent / f"{marker}{stamp}.bak").write_text("{}", encoding="utf-8")
    names = [path.name for path in available_backups(settings_file)]
    assert names[0].startswith(f"{marker}2026")
    assert latest_backup(settings_file).name == names[0]


def test_available_backups_includes_collision_suffix(settings_file: Path):
    marker = f"settings.json{constants.BACKUP_MARKER}20240101T000000000000Z"
    (settings_file.parent / f"{marker}.bak").write_text("{}", encoding="utf-8")
    (settings_file.parent / f"{marker}.bak.1").write_text("{}", encoding="utf-8")
    assert len(available_backups(settings_file)) == 2


def test_available_backups_ignores_other_files(settings_file: Path):
    (settings_file.parent / "settings.json.bak").write_text("{}", encoding="utf-8")
    (settings_file.parent / "other.json.ttr-aspect-lock.x.bak").write_text("{}", encoding="utf-8")
    assert available_backups(settings_file) == []


def test_latest_backup_without_any(settings_file: Path):
    with pytest.raises(BackupNotFoundError):
        latest_backup(settings_file)


def test_restore_round_trip(settings_file: Path):
    original = settings_file.read_text(encoding="utf-8")
    applied = apply_aspect_ratio(settings_file)
    restore_settings(settings_file, applied.backup_path)
    assert settings_file.read_text(encoding="utf-8") == original


def test_restore_dry_run_leaves_file(settings_file: Path):
    applied = apply_aspect_ratio(settings_file)
    changed = settings_file.read_text(encoding="utf-8")
    result = restore_settings(settings_file, applied.backup_path, dry_run=True)
    assert result.dry_run is True
    assert settings_file.read_text(encoding="utf-8") == changed


def test_restore_requires_existing_backup(settings_file: Path, tmp_path: Path):
    with pytest.raises(BackupNotFoundError):
        restore_settings(settings_file, tmp_path / "missing.bak")


def test_restore_validates_backup_before_writing(settings_file: Path, tmp_path: Path):
    broken = tmp_path / "broken.bak"
    broken.write_text("{ not json", encoding="utf-8")
    before = settings_file.read_text(encoding="utf-8")
    with pytest.raises(InvalidSettingsError):
        restore_settings(settings_file, broken)
    assert settings_file.read_text(encoding="utf-8") == before


def test_restore_requires_existing_settings(tmp_path: Path):
    backup = tmp_path / "backup.bak"
    backup.write_text(json.dumps({"video": {}}), encoding="utf-8")
    with pytest.raises(SettingsNotFoundError):
        restore_settings(tmp_path / "absent.json", backup)


def test_apply_leaves_no_temporary_files(settings_file: Path):
    apply_aspect_ratio(settings_file)
    assert not [p for p in settings_file.parent.iterdir() if p.suffix == ".tmp"]
