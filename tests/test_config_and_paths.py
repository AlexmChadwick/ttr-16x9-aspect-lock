from __future__ import annotations

from pathlib import Path

import pytest

from ttr_aspect_lock.config import Config, default_config_path, load_config
from ttr_aspect_lock.errors import AmbiguousSettingsError, AspectLockError, SettingsNotFoundError
from ttr_aspect_lock import paths


def make_settings(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text('{"video": {}}\n', encoding="utf-8")
    return path


def test_load_config_resolves_relative_paths_against_config_file(tmp_path: Path) -> None:
    config_path = tmp_path / "portable" / "config.toml"
    config_path.parent.mkdir()
    config_path.write_text(
        'settings_path = "profiles/main/settings.json"\nsettings_paths = ["second.json"]\nbackup_directory = "backups"\n',
        encoding="utf-8",
    )

    config = load_config(config_path)

    assert config.source == config_path
    assert config.settings_paths == (
        config_path.parent / "profiles/main/settings.json",
        config_path.parent / "second.json",
    )
    # A relative backup location intentionally stays portable; the CLI anchors it
    # beside each selected settings file at mutation time.
    assert config.backup_directory == Path("backups")


def test_load_config_supports_named_table_and_missing_optional_file(tmp_path: Path) -> None:
    config_path = tmp_path / "config.toml"
    config_path.write_text('[ttr-aspect-lock]\nsettings_paths = ["one.json"]\n', encoding="utf-8")
    assert load_config(config_path).settings_paths == (tmp_path / "one.json",)

    missing = tmp_path / "missing.toml"
    assert load_config(missing) == Config(source=missing)
    with pytest.raises(AspectLockError, match="Configuration file not found"):
        load_config(missing, required=True)


@pytest.mark.parametrize(
    ("toml", "message"),
    [
        ('settings_path = ""\n', "non-empty string"),
        ('settings_paths = "not-a-list"\n', "array of paths"),
        ('[ttr-aspect-lock]\nsettings_path = 4\n', "non-empty string"),
    ],
)
def test_load_config_rejects_invalid_values(tmp_path: Path, toml: str, message: str) -> None:
    config_path = tmp_path / "config.toml"
    config_path.write_text(toml, encoding="utf-8")
    with pytest.raises(AspectLockError, match=message):
        load_config(config_path)


def test_default_config_path_uses_mocked_platform_environment(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("ttr_aspect_lock.config.Path.home", lambda: tmp_path / "home")
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
    assert default_config_path("posix") == tmp_path / "xdg" / "ttr-aspect-lock" / "config.toml"
    monkeypatch.setenv("APPDATA", str(tmp_path / "roaming"))
    assert default_config_path("nt") == tmp_path / "roaming" / "ttr-aspect-lock" / "config.toml"


def test_platform_candidates_use_mocked_windows_environment(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("ttr_aspect_lock.paths.Path.home", lambda: tmp_path / "home")
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "local"))
    monkeypatch.setenv("APPDATA", str(tmp_path / "roaming"))

    assert paths.platform_settings_candidates("win32") == (
        tmp_path / "local" / "Toontown Rewritten" / "settings.json",
        tmp_path / "local" / "Toontown Rewritten" / "resources" / "settings.json",
        tmp_path / "roaming" / "Toontown Rewritten" / "settings.json",
        tmp_path / "roaming" / "Toontown Rewritten" / "resources" / "settings.json",
    )


def test_platform_candidates_cover_macos_and_linux_xdg(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("ttr_aspect_lock.paths.Path.home", lambda: tmp_path / "home")
    monkeypatch.setenv("USER", "testuser")
    assert paths.platform_settings_candidates("darwin") == (
        tmp_path / "home" / "Library" / "Application Support" / "Toontown Rewritten" / "settings.json",
        tmp_path
        / "home"
        / "Library"
        / "Application Support"
        / "Toontown Rewritten"
        / "resources"
        / "settings.json",
    )
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "data"))
    assert paths.platform_settings_candidates("linux") == (
        tmp_path / "data" / "Toontown Rewritten" / "settings.json",
        tmp_path / "data" / "Toontown Rewritten" / "resources" / "settings.json",
        tmp_path / "home" / ".config" / "Toontown Rewritten" / "settings.json",
        tmp_path / "home" / ".config" / "Toontown Rewritten" / "resources" / "settings.json",
        tmp_path / "home" / ".wine" / "drive_c" / "users" / "testuser" / "AppData" / "Local" / "Toontown Rewritten" / "settings.json",
        tmp_path / "home" / ".wine" / "drive_c" / "users" / "testuser" / "AppData" / "Local" / "Toontown Rewritten" / "resources" / "settings.json",
        tmp_path / "home" / ".wine" / "drive_c" / "users" / "testuser" / "AppData" / "Roaming" / "Toontown Rewritten" / "settings.json",
        tmp_path / "home" / ".wine" / "drive_c" / "users" / "testuser" / "AppData" / "Roaming" / "Toontown Rewritten" / "resources" / "settings.json",
        tmp_path / "home" / ".wine" / "drive_c" / "users" / "steamuser" / "AppData" / "Local" / "Toontown Rewritten" / "settings.json",
        tmp_path / "home" / ".wine" / "drive_c" / "users" / "steamuser" / "AppData" / "Local" / "Toontown Rewritten" / "resources" / "settings.json",
        tmp_path / "home" / ".wine" / "drive_c" / "users" / "steamuser" / "AppData" / "Roaming" / "Toontown Rewritten" / "settings.json",
        tmp_path / "home" / ".wine" / "drive_c" / "users" / "steamuser" / "AppData" / "Roaming" / "Toontown Rewritten" / "resources" / "settings.json",
    )


def test_discover_uses_existing_configured_and_platform_paths_once(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    configured = make_settings(tmp_path / "configured" / "settings.json")
    discovered = make_settings(tmp_path / "discovered" / "settings.json")
    missing = tmp_path / "missing" / "settings.json"
    monkeypatch.setattr(paths, "platform_settings_candidates", lambda platform=None: (configured, discovered, missing))

    found = paths.discover_settings_paths(config=Config(settings_paths=(configured, configured)))

    assert found == [configured.resolve(), discovered.resolve()]


def test_resolve_explicit_paths_are_deduplicated_and_missing_paths_fail(tmp_path: Path) -> None:
    settings = make_settings(tmp_path / "settings.json")
    assert paths.resolve_settings_paths((settings, settings)) == [settings.resolve()]
    with pytest.raises(SettingsNotFoundError, match="missing.json"):
        paths.resolve_settings_paths((tmp_path / "missing.json",))


def test_resolve_implicit_paths_requires_selection_when_ambiguous(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    first = make_settings(tmp_path / "one" / "settings.json")
    second = make_settings(tmp_path / "two" / "settings.json")
    monkeypatch.setattr(paths, "discover_settings_paths", lambda **kwargs: [first, second])

    with pytest.raises(AmbiguousSettingsError, match="--settings PATH or --all"):
        paths.resolve_settings_paths()
    assert paths.resolve_settings_paths(all_paths=True) == [first, second]


def test_resolve_implicit_paths_reports_no_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(paths, "discover_settings_paths", lambda **kwargs: [])
    with pytest.raises(SettingsNotFoundError, match="Could not find settings.json"):
        paths.resolve_settings_paths()
