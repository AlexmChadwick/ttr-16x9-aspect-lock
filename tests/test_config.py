"""Tests for the optional TOML configuration file."""

from __future__ import annotations

from pathlib import Path

import pytest

from ttr_aspect_lock.config import default_config_path, load_config
from ttr_aspect_lock.errors import AspectLockError


def write_config(path: Path, body: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")
    return path


def test_missing_optional_config_is_empty(tmp_path: Path):
    config = load_config(tmp_path / "absent.toml")
    assert config.settings_paths == ()
    assert config.backup_directory is None


def test_missing_required_config_raises(tmp_path: Path):
    with pytest.raises(AspectLockError):
        load_config(tmp_path / "absent.toml", required=True)


def test_directory_instead_of_file(tmp_path: Path):
    with pytest.raises(AspectLockError):
        load_config(tmp_path, required=True)


def test_invalid_toml(tmp_path: Path):
    path = write_config(tmp_path / "config.toml", "settings_path = [oops")
    with pytest.raises(AspectLockError):
        load_config(path)


def test_relative_settings_path_resolves_beside_config(tmp_path: Path):
    path = write_config(tmp_path / "config.toml", 'settings_path = "ttr/settings.json"')
    config = load_config(path)
    assert config.settings_paths == (tmp_path / "ttr" / "settings.json",)


def test_absolute_settings_path_is_kept(tmp_path: Path):
    target = (tmp_path / "abs" / "settings.json").as_posix()
    path = write_config(tmp_path / "config.toml", f'settings_path = "{target}"')
    assert load_config(path).settings_paths == (Path(target),)


def test_settings_paths_list_is_appended(tmp_path: Path):
    path = write_config(
        tmp_path / "config.toml",
        'settings_path = "one/settings.json"\nsettings_paths = ["two/settings.json"]\n',
    )
    config = load_config(path)
    assert [p.parent.name for p in config.settings_paths] == ["one", "two"]


def test_namespaced_table_is_supported(tmp_path: Path):
    path = write_config(
        tmp_path / "config.toml",
        '[ttr-aspect-lock]\nbackup_directory = "vault"\n',
    )
    assert load_config(path).backup_directory == Path("vault")


def test_relative_backup_directory_stays_relative(tmp_path: Path):
    """Callers anchor it beside each settings file, so it must not absolutise here."""
    path = write_config(tmp_path / "config.toml", 'backup_directory = "ttr-backups"')
    backup_directory = load_config(path).backup_directory
    assert backup_directory == Path("ttr-backups")
    assert not backup_directory.is_absolute()


def test_absolute_backup_directory_is_kept(tmp_path: Path):
    target = (tmp_path / "vault").as_posix()
    path = write_config(tmp_path / "config.toml", f'backup_directory = "{target}"')
    assert load_config(path).backup_directory == Path(target)


@pytest.mark.parametrize(
    "body",
    [
        "settings_path = 5",
        'settings_path = ""',
        'settings_paths = "not-a-list"',
        "settings_paths = [7]",
        "backup_directory = true",
        "ttr-aspect-lock = 3",
    ],
)
def test_invalid_values_are_rejected(tmp_path: Path, body: str):
    path = write_config(tmp_path / "config.toml", body)
    with pytest.raises(AspectLockError):
        load_config(path)


def test_example_config_loads(tmp_path: Path):
    example = Path(__file__).resolve().parents[1] / "config.example.toml"
    config = load_config(example)
    assert config.backup_directory == Path("ttr-aspect-lock-backups")
    assert config.settings_paths == ()


@pytest.mark.parametrize(("platform", "fragment"), [("nt", "AppData"), ("posix", ".config")])
def test_default_config_path(platform: str, fragment: str):
    path = default_config_path(platform)
    assert path.name == "config.toml"
    assert fragment in str(path)
