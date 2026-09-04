"""End-to-end tests for the command-line interface."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from conftest import read_json, write_settings
from ttr_aspect_lock import constants
from ttr_aspect_lock.cli import EXIT_ERROR, EXIT_OK, EXIT_USAGE, is_locked, main
from ttr_aspect_lock.settings import apply_aspect_ratio, available_backups

TARGET = constants.TARGET_ASPECT_RATIO


def run(capsys, *argv: str) -> tuple[int, str, str]:
    code = main(list(argv))
    captured = capsys.readouterr()
    return code, captured.out, captured.err


def run_json(capsys, *argv: str) -> tuple[int, dict]:
    code, out, _ = run(capsys, "--json", *argv)
    return code, json.loads(out)


@pytest.fixture
def installed(settings_file: Path) -> Path:
    """A settings file with the lock already applied and one backup present."""
    apply_aspect_ratio(settings_file)
    return settings_file


def test_no_command_prints_help(capsys):
    code, out, _ = run(capsys)
    assert code == EXIT_USAGE
    assert "COMMAND" in out


def test_version(capsys):
    with pytest.raises(SystemExit) as excinfo:
        main(["--version"])
    assert excinfo.value.code == 0
    assert "ttr-aspect-lock" in capsys.readouterr().out


@pytest.mark.parametrize(
    "command", ["discover", "status", "install", "restore", "uninstall", "doctor"]
)
def test_every_command_is_registered(command: str):
    from ttr_aspect_lock.cli import build_parser

    args = build_parser().parse_args([command])
    assert args.command == command
    assert callable(args.handler)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (TARGET, True),
        (1.7777777778, True),
        (16 / 9, True),
        (0.0, False),
        (1.3333333, False),
        (None, False),
        (True, False),
        ("1.7777777778", False),
    ],
)
def test_is_locked(value, expected: bool):
    assert is_locked(value) is expected


def test_discover_reports_nothing_found(capsys, isolated_home: Path):
    code, payload = run_json(capsys, "discover")
    assert code == EXIT_OK
    assert payload["found"] == []
    assert payload["candidates"]


def test_discover_lists_found_file(capsys, isolated_home: Path):
    expected = write_settings(
        isolated_home / ".local" / "share" / "Toontown Rewritten" / "settings.json"
    )
    code, out, _ = run(capsys, "discover", "--verbose")
    assert code == EXIT_OK
    assert str(expected) in out


def test_status_without_settings_fails(capsys, isolated_home: Path):
    code, out, _ = run(capsys, "status")
    assert code == EXIT_ERROR
    assert "No settings.json found" in out


def test_status_reports_unlocked(capsys, settings_file: Path):
    code, payload = run_json(capsys, "--settings", str(settings_file), "status")
    assert code == EXIT_OK
    entry = payload["settings"][0]
    assert entry["locked"] is False
    assert entry["value"] == 0.0
    assert entry["backups"] == 0


def test_status_reports_locked_after_install(capsys, installed: Path):
    code, payload = run_json(capsys, "--settings", str(installed), "status")
    assert code == EXIT_OK
    entry = payload["settings"][0]
    assert entry["locked"] is True
    assert entry["value"] == TARGET
    assert entry["backups"] == 1
    assert entry["latest_backup"]


def test_status_human_output_mentions_key(capsys, installed: Path):
    code, out, _ = run(capsys, "--settings", str(installed), "status", "--verbose")
    assert code == EXIT_OK
    assert "video.forced-aspect-ratio" in out
    assert "locked to 16:9" in out


def test_status_reports_broken_json(capsys, tmp_path: Path):
    broken = tmp_path / "settings.json"
    broken.write_text("{ broken", encoding="utf-8")
    code, payload = run_json(capsys, "--settings", str(broken), "status")
    assert code == EXIT_ERROR
    assert payload["ok"] is False
    assert payload["settings"][0]["error"]


def test_status_reads_every_discovered_file_without_all(capsys, isolated_home: Path):
    write_settings(isolated_home / ".local" / "share" / "Toontown Rewritten" / "settings.json")
    write_settings(isolated_home / ".config" / "Toontown Rewritten" / "settings.json")
    code, payload = run_json(capsys, "status")
    assert code == EXIT_OK
    assert len(payload["settings"]) == 2


def test_install_writes_target_and_backup(capsys, settings_file: Path):
    code, payload = run_json(capsys, "--settings", str(settings_file), "install")
    assert code == EXIT_OK
    assert payload["results"][0]["changed"] is True
    assert read_json(settings_file)["video"]["forced-aspect-ratio"] == TARGET
    assert Path(payload["results"][0]["backup"]).is_file()


def test_install_dry_run_changes_nothing(capsys, settings_file: Path):
    before = settings_file.read_text(encoding="utf-8")
    code, out, _ = run(capsys, "--settings", str(settings_file), "install", "--dry-run")
    assert code == EXIT_OK
    assert "would set" in out
    assert settings_file.read_text(encoding="utf-8") == before
    assert available_backups(settings_file) == []


def test_install_is_idempotent(capsys, installed: Path):
    code, payload = run_json(capsys, "--settings", str(installed), "install")
    assert code == EXIT_OK
    assert payload["results"][0]["changed"] is False
    assert len(available_backups(installed)) == 1


def test_install_refuses_ambiguous_selection(capsys, isolated_home: Path):
    first = write_settings(
        isolated_home / ".local" / "share" / "Toontown Rewritten" / "settings.json"
    )
    write_settings(isolated_home / ".config" / "Toontown Rewritten" / "settings.json")
    code, out, err = run(capsys, "install")
    assert code == EXIT_ERROR
    assert "--all" in err
    assert read_json(first)["video"]["forced-aspect-ratio"] == 0.0


def test_install_all_updates_every_file(capsys, isolated_home: Path):
    paths = [
        write_settings(isolated_home / ".local" / "share" / "Toontown Rewritten" / "settings.json"),
        write_settings(isolated_home / ".config" / "Toontown Rewritten" / "settings.json"),
    ]
    code, payload = run_json(capsys, "install", "--all")
    assert code == EXIT_OK
    assert len(payload["results"]) == 2
    assert all(read_json(path)["video"]["forced-aspect-ratio"] == TARGET for path in paths)


def test_install_missing_settings_path(capsys, tmp_path: Path):
    code, _, err = run(capsys, "--settings", str(tmp_path / "nope.json"), "install")
    assert code == EXIT_ERROR
    assert "not found" in err


def test_install_relative_backup_dir_resolves_beside_settings(capsys, settings_file, tmp_path):
    code, payload = run_json(
        capsys, "--settings", str(settings_file), "install", "--backup-dir", "vault"
    )
    assert code == EXIT_OK
    backup = Path(payload["results"][0]["backup"])
    assert backup.parent == settings_file.parent / "vault"
    assert not (Path.cwd() / "vault").exists()


def test_install_absolute_backup_dir(capsys, settings_file: Path, tmp_path: Path):
    vault = tmp_path / "elsewhere"
    code, payload = run_json(
        capsys, "--settings", str(settings_file), "install", "--backup-dir", str(vault)
    )
    assert code == EXIT_OK
    assert Path(payload["results"][0]["backup"]).parent == vault


def test_restore_latest_round_trip(capsys, settings_file: Path):
    original = settings_file.read_text(encoding="utf-8")
    run(capsys, "--settings", str(settings_file), "install")
    code, out, _ = run(capsys, "--settings", str(settings_file), "restore", "--latest")
    assert code == EXIT_OK
    assert "restored" in out
    assert settings_file.read_text(encoding="utf-8") == original


def test_restore_defaults_to_latest(capsys, settings_file: Path):
    original = settings_file.read_text(encoding="utf-8")
    run(capsys, "--settings", str(settings_file), "install")
    code, _, _ = run(capsys, "--settings", str(settings_file), "restore")
    assert code == EXIT_OK
    assert settings_file.read_text(encoding="utf-8") == original


def test_uninstall_is_an_alias_for_restore(capsys, settings_file: Path):
    original = settings_file.read_text(encoding="utf-8")
    run(capsys, "--settings", str(settings_file), "install")
    code, payload = run_json(capsys, "--settings", str(settings_file), "uninstall")
    assert code == EXIT_OK
    assert payload["command"] == "uninstall"
    assert settings_file.read_text(encoding="utf-8") == original


def test_restore_specific_backup(capsys, settings_file: Path):
    code, payload = run_json(capsys, "--settings", str(settings_file), "install")
    backup = payload["results"][0]["backup"]
    code, payload = run_json(
        capsys, "--settings", str(settings_file), "restore", "--backup", backup
    )
    assert code == EXIT_OK
    assert payload["results"][0]["backup"] == backup


def test_restore_rejects_backup_with_latest(capsys, installed: Path):
    code, _, err = run(
        capsys, "--settings", str(installed), "restore", "--backup", "x.bak", "--latest"
    )
    assert code == EXIT_ERROR
    assert "not both" in err


def test_restore_rejects_backup_with_multiple_targets(capsys, isolated_home: Path):
    for parent in (".local/share", ".config"):
        write_settings(isolated_home / parent / "Toontown Rewritten" / "settings.json")
    code, _, err = run(capsys, "restore", "--all", "--backup", "x.bak")
    assert code == EXIT_ERROR
    assert "single file" in err


def test_restore_without_backup_fails_clearly(capsys, settings_file: Path):
    code, _, err = run(capsys, "--settings", str(settings_file), "restore")
    assert code == EXIT_ERROR
    assert "No TTR Aspect Lock backup" in err


def test_restore_dry_run_keeps_current_file(capsys, installed: Path):
    changed = installed.read_text(encoding="utf-8")
    code, out, _ = run(capsys, "--settings", str(installed), "restore", "--dry-run")
    assert code == EXIT_OK
    assert "would restore" in out
    assert installed.read_text(encoding="utf-8") == changed


def test_restore_all(capsys, isolated_home: Path):
    paths = [
        write_settings(isolated_home / ".local" / "share" / "Toontown Rewritten" / "settings.json"),
        write_settings(isolated_home / ".config" / "Toontown Rewritten" / "settings.json"),
    ]
    originals = [path.read_text(encoding="utf-8") for path in paths]
    run(capsys, "install", "--all")
    code, payload = run_json(capsys, "restore", "--all", "--latest")
    assert code == EXIT_OK
    assert len(payload["results"]) == 2
    assert [path.read_text(encoding="utf-8") for path in paths] == originals


def test_config_file_supplies_settings_path(capsys, tmp_path: Path, settings_file: Path):
    config = tmp_path / "config.toml"
    config.write_text(
        f'settings_path = "{settings_file.as_posix()}"\nbackup_directory = "vault"\n',
        encoding="utf-8",
    )
    code, payload = run_json(capsys, "--config", str(config), "install")
    assert code == EXIT_OK
    assert Path(payload["results"][0]["backup"]).parent == settings_file.parent / "vault"


def test_missing_config_file_is_an_error(capsys, tmp_path: Path):
    code, _, err = run(capsys, "--config", str(tmp_path / "absent.toml"), "status")
    assert code == EXIT_ERROR
    assert "not found" in err


def test_doctor_reports_healthy_installation(capsys, installed: Path):
    code, payload = run_json(capsys, "--settings", str(installed), "doctor")
    assert code == EXIT_OK
    assert payload["ok"] is True
    names = {check["name"] for check in payload["checks"]}
    assert {"python", "version", "config", "discovery", "settings", "writable", "backups"} <= names


def test_doctor_flags_missing_settings(capsys, isolated_home: Path):
    code, payload = run_json(capsys, "doctor")
    assert code == EXIT_ERROR
    assert payload["ok"] is False
    discovery = [c for c in payload["checks"] if c["name"] == "discovery"][0]
    assert discovery["level"] == "error"


def test_doctor_flags_broken_json(capsys, tmp_path: Path):
    broken = tmp_path / "settings.json"
    broken.write_text("nope", encoding="utf-8")
    code, payload = run_json(capsys, "--settings", str(broken), "doctor")
    assert code == EXIT_ERROR
    assert any(c["name"] == "settings" and c["level"] == "error" for c in payload["checks"])


def test_doctor_warns_when_client_is_running(capsys, installed: Path, monkeypatch):
    monkeypatch.setattr("ttr_aspect_lock.cli._client_running", lambda: True)
    code, payload = run_json(capsys, "--settings", str(installed), "doctor")
    assert code == EXIT_OK
    client = [c for c in payload["checks"] if c["name"] == "client"][0]
    assert client["level"] == "warn"
    assert "Quit it first" in client["message"]


def test_doctor_human_output_has_a_summary(capsys, installed: Path):
    code, out, _ = run(capsys, "--settings", str(installed), "doctor")
    assert code == EXIT_OK
    assert "problem(s)." in out
    assert "[OK  ]" in out


def test_json_mode_emits_only_json(capsys, installed: Path):
    code, out, _ = run(capsys, "--json", "--settings", str(installed), "status")
    assert code == EXIT_OK
    json.loads(out)  # a single parseable document, no human lines mixed in


def test_status_finds_backups_in_custom_directory(capsys, settings_file: Path, tmp_path: Path):
    run(capsys, "--settings", str(settings_file), "install", "--backup-dir", "vault")
    # No --backup-dir here: the settings directory tree is still searched.
    code, payload = run_json(capsys, "--settings", str(settings_file), "status")
    assert code == EXIT_OK
    assert payload["settings"][0]["backups"] == 0

    code, payload = run_json(
        capsys, "--settings", str(settings_file), "status", "--backup-dir", "vault"
    )
    assert payload["settings"][0]["backups"] == 1


def test_restore_falls_back_to_the_settings_directory(capsys, settings_file: Path):
    """An undo works even when the caller forgets the install's --backup-dir."""
    original = settings_file.read_text(encoding="utf-8")
    run(capsys, "--settings", str(settings_file), "install")
    code, payload = run_json(
        capsys, "--settings", str(settings_file), "uninstall", "--backup-dir", "vault"
    )
    assert code == EXIT_OK
    assert Path(payload["results"][0]["backup"]).parent == settings_file.parent
    assert settings_file.read_text(encoding="utf-8") == original


def test_restore_prefers_the_selected_backup_directory(capsys, settings_file: Path):
    run(capsys, "--settings", str(settings_file), "install")
    stale = available_backups(settings_file)[0]
    run(capsys, "--settings", str(settings_file), "restore", "--latest")
    run(capsys, "--settings", str(settings_file), "install", "--backup-dir", "vault")
    code, payload = run_json(
        capsys, "--settings", str(settings_file), "uninstall", "--backup-dir", "vault"
    )
    assert code == EXIT_OK
    chosen = Path(payload["results"][0]["backup"])
    assert chosen.parent == settings_file.parent / "vault"
    assert chosen != stale


def test_dry_run_is_reported_as_a_boolean(capsys, settings_file: Path):
    code, payload = run_json(capsys, "--settings", str(settings_file), "install")
    assert payload["results"][0]["dry_run"] is False


def test_flags_are_accepted_after_the_command(capsys, installed: Path):
    code, payload = run_json(capsys, "status", "--settings", str(installed))
    assert code == EXIT_OK
    assert payload["settings"][0]["path"] == str(installed)
