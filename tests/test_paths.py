"""Tests for platform candidate locations and safe path selection."""

from __future__ import annotations

from pathlib import Path

import pytest

from conftest import write_settings
from ttr_aspect_lock.config import Config
from ttr_aspect_lock.errors import AmbiguousSettingsError, SettingsNotFoundError
from ttr_aspect_lock.paths import (
    discover_settings_paths,
    platform_settings_candidates,
    resolve_settings_paths,
)


@pytest.mark.parametrize(
    ("platform", "expected_fragment"),
    [
        ("win32", "AppData"),
        ("darwin", "Application Support"),
        ("linux", ".local"),
    ],
)
def test_candidates_are_platform_specific(platform: str, expected_fragment: str):
    candidates = platform_settings_candidates(platform)
    assert candidates
    assert any(expected_fragment in str(path) for path in candidates)
    assert all(path.name == "settings.json" for path in candidates)


@pytest.mark.parametrize("platform", ["win32", "darwin", "linux"])
def test_candidates_include_resources_variant(platform: str):
    candidates = platform_settings_candidates(platform)
    assert any(path.parent.name == "resources" for path in candidates)


def test_linux_candidates_include_wine_prefix(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("WINEPREFIX", str(tmp_path / "prefix"))
    candidates = platform_settings_candidates("linux")
    assert any("drive_c" in str(path) for path in candidates)


def test_candidates_never_touch_the_filesystem(isolated_home: Path):
    platform_settings_candidates("linux")
    assert list(isolated_home.iterdir()) == []


def test_discover_returns_only_existing_files(isolated_home: Path):
    assert discover_settings_paths(platform="linux") == []
    expected = write_settings(
        isolated_home / ".local" / "share" / "Toontown Rewritten" / "settings.json"
    )
    assert discover_settings_paths(platform="linux") == [expected.resolve()]


def test_discover_includes_configured_paths_first(tmp_path: Path):
    configured = write_settings(tmp_path / "custom" / "settings.json")
    config = Config(settings_paths=(configured,))
    assert discover_settings_paths(config=config, platform="linux")[0] == configured.resolve()


def test_discover_deduplicates(tmp_path: Path):
    configured = write_settings(tmp_path / "custom" / "settings.json")
    config = Config(settings_paths=(configured, Path(str(configured))))
    assert discover_settings_paths(config=config, platform="linux") == [configured.resolve()]


def test_resolve_prefers_explicit_paths(tmp_path: Path):
    explicit = write_settings(tmp_path / "explicit" / "settings.json")
    assert resolve_settings_paths([explicit], platform="linux") == [explicit.resolve()]


def test_resolve_rejects_missing_explicit_path(tmp_path: Path):
    with pytest.raises(SettingsNotFoundError):
        resolve_settings_paths([tmp_path / "missing.json"], platform="linux")


def test_resolve_without_any_candidate(isolated_home: Path):
    with pytest.raises(SettingsNotFoundError):
        resolve_settings_paths(platform="linux")


def test_resolve_refuses_ambiguity_by_default(isolated_home: Path):
    write_settings(isolated_home / ".local" / "share" / "Toontown Rewritten" / "settings.json")
    write_settings(isolated_home / ".config" / "Toontown Rewritten" / "settings.json")
    with pytest.raises(AmbiguousSettingsError) as excinfo:
        resolve_settings_paths(platform="linux")
    # The message must list the choices so the user can pass --settings.
    assert str(excinfo.value).count("settings.json") >= 2


def test_resolve_all_returns_every_match(isolated_home: Path):
    write_settings(isolated_home / ".local" / "share" / "Toontown Rewritten" / "settings.json")
    write_settings(isolated_home / ".config" / "Toontown Rewritten" / "settings.json")
    assert len(resolve_settings_paths(all_paths=True, platform="linux")) == 2
