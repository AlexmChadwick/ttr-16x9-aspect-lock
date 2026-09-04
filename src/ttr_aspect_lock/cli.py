"""Command-line interface: discover, status, install, restore/uninstall, doctor."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
import os
from pathlib import Path
import platform as platform_module
import subprocess
import sys
from typing import Any, Callable, Optional, Sequence

from . import __version__
from .config import Config, default_config_path, load_config
from .constants import APP_NAME, ASPECT_RATIO_KEY, TARGET_ASPECT_RATIO, VIDEO_KEY
from .errors import AspectLockError, InvalidSettingsError
from .paths import (
    discover_settings_paths,
    platform_settings_candidates,
    resolve_settings_paths,
)
from .settings import (
    apply_aspect_ratio,
    available_backups,
    latest_backup,
    ratios_match,
    read_settings,
    restore_settings,
)

EXIT_OK = 0
EXIT_ERROR = 1
EXIT_USAGE = 2

MIN_PYTHON = (3, 9)


@dataclass
class Output:
    """Collects human text and a JSON payload so both formats stay in sync."""

    json_mode: bool
    verbose: bool
    stream: Any = None
    payload: dict[str, Any] = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        self.stream = self.stream or sys.stdout
        self.payload = {}

    def line(self, text: str = "") -> None:
        if not self.json_mode:
            print(text, file=self.stream)

    def detail(self, text: str) -> None:
        if self.verbose:
            self.line(text)

    def emit(self, command: str, *, ok: bool = True, **fields: Any) -> None:
        self.payload = {"command": command, "ok": ok, **fields}
        if self.json_mode:
            print(json.dumps(self.payload, indent=2, default=str), file=self.stream)


def is_locked(value: Any, ratio: float = TARGET_ASPECT_RATIO) -> bool:
    """Treat any value within float display precision of the target as locked."""
    return ratios_match(value, ratio)


def current_ratio(settings_path: Path) -> Any:
    """Return the stored ``video.forced-aspect-ratio`` or ``None`` when unset."""
    data = read_settings(settings_path)
    video = data.get(VIDEO_KEY)
    if video is None:
        return None
    if not isinstance(video, dict):
        raise InvalidSettingsError(f"{settings_path}: {VIDEO_KEY!r} must be a JSON object")
    return video.get(ASPECT_RATIO_KEY)


def resolve_backup_dir(settings_path: Path, backup_dir: Optional[Path]) -> Optional[Path]:
    """Anchor a relative backup directory beside its settings file, never the cwd."""
    if backup_dir is None:
        return None
    backup_dir = Path(backup_dir).expanduser()
    if backup_dir.is_absolute():
        return backup_dir
    return settings_path.parent / backup_dir


def backup_search_dirs(settings_path: Path, backup_dir: Optional[Path]) -> list[Path]:
    """Return the backup directories to search, most specific first.

    A selected backup directory wins, but the settings file's own directory is
    still searched so an undo works even when the earlier install used a
    different ``--backup-dir``.
    """
    resolved = resolve_backup_dir(settings_path, backup_dir)
    directories = [resolved] if resolved else []
    if settings_path.parent not in directories:
        directories.append(settings_path.parent)
    return directories


def find_backups(settings_path: Path, backup_dir: Optional[Path]) -> list[Path]:
    """List every backup for this settings file across the searched directories."""
    found: list[Path] = []
    for directory in backup_search_dirs(settings_path, backup_dir):
        found.extend(
            candidate
            for candidate in available_backups(settings_path, directory)
            if candidate not in found
        )
    return found


def newest_backup(settings_path: Path, backup_dir: Optional[Path]) -> Path:
    """Return the newest backup, preferring the selected backup directory."""
    for directory in backup_search_dirs(settings_path, backup_dir):
        backups = available_backups(settings_path, directory)
        if backups:
            return backups[0]
    return latest_backup(settings_path, resolve_backup_dir(settings_path, backup_dir))


def _load_cli_config(args: argparse.Namespace) -> Config:
    if args.config:
        return load_config(Path(args.config), required=True)
    return load_config(default_config_path())


def _selected_backup_dir(args: argparse.Namespace, config: Config) -> Optional[Path]:
    if getattr(args, "backup_dir", None):
        return Path(args.backup_dir)
    return config.backup_directory


def _explicit_paths(args: argparse.Namespace) -> list[Path]:
    return [Path(value).expanduser() for value in (args.settings or [])]


def _readonly_paths(args: argparse.Namespace, config: Config) -> list[Path]:
    """Read-only commands report every discovered file instead of refusing."""
    explicit = _explicit_paths(args)
    if explicit:
        return resolve_settings_paths(explicit, config=config)
    return discover_settings_paths(config=config)


def _format_value(value: Any) -> str:
    if value is None:
        return "unset"
    return repr(value)


def cmd_discover(args: argparse.Namespace, config: Config, out: Output) -> int:
    candidates = list(platform_settings_candidates())
    configured = list(config.settings_paths)
    found = discover_settings_paths(config=config)

    out.line(f"Searched {len(candidates) + len(configured)} candidate location(s).")
    for candidate in (*configured, *candidates):
        out.detail(f"  [{'found' if candidate.is_file() else 'none '}] {candidate}")
    if not found:
        out.line("No settings.json found. Start Toontown Rewritten once, or pass --settings PATH.")
    else:
        out.line(f"Found {len(found)} settings file(s):")
        for path in found:
            out.line(f"  {path}")
    out.emit(
        "discover",
        ok=True,
        candidates=[str(path) for path in (*configured, *candidates)],
        found=[str(path) for path in found],
        config=str(config.source) if config.source else None,
    )
    return EXIT_OK


def _status_entry(path: Path, backup_dir: Optional[Path]) -> dict[str, Any]:
    entry: dict[str, Any] = {"path": str(path), "exists": path.is_file()}
    if not entry["exists"]:
        entry.update({"locked": False, "value": None, "error": "settings file not found"})
        return entry
    try:
        value = current_ratio(path)
    except AspectLockError as exc:
        entry.update({"locked": False, "value": None, "error": str(exc)})
        return entry
    backups = find_backups(path, backup_dir)
    entry.update(
        {
            "value": value,
            "locked": is_locked(value),
            "target": TARGET_ASPECT_RATIO,
            "backups": len(backups),
            "latest_backup": str(backups[0]) if backups else None,
        }
    )
    return entry


def cmd_status(args: argparse.Namespace, config: Config, out: Output) -> int:
    backup_dir = _selected_backup_dir(args, config)
    paths = _readonly_paths(args, config)
    if not paths:
        out.line("No settings.json found. Run `discover --verbose` or pass --settings PATH.")
        out.emit("status", ok=False, settings=[], error="no settings file found")
        return EXIT_ERROR

    entries = [_status_entry(path, backup_dir) for path in paths]
    failed = False
    for entry in entries:
        if entry.get("error"):
            failed = True
            out.line(f"{entry['path']}: {entry['error']}")
            continue
        state = "locked to 16:9" if entry["locked"] else "not locked"
        out.line(f"{entry['path']}")
        out.line(f"  {VIDEO_KEY}.{ASPECT_RATIO_KEY} = {_format_value(entry['value'])} ({state})")
        out.detail(f"  target = {TARGET_ASPECT_RATIO!r}")
        out.detail(f"  backups = {entry['backups']}")
        if entry["latest_backup"]:
            out.detail(f"  latest backup = {entry['latest_backup']}")
    out.emit("status", ok=not failed, settings=entries)
    return EXIT_ERROR if failed else EXIT_OK


def cmd_install(args: argparse.Namespace, config: Config, out: Output) -> int:
    backup_dir = _selected_backup_dir(args, config)
    paths = resolve_settings_paths(_explicit_paths(args), config=config, all_paths=args.all)
    results = []
    for path in paths:
        result = apply_aspect_ratio(
            path,
            TARGET_ASPECT_RATIO,
            backup_dir=resolve_backup_dir(path, backup_dir),
            dry_run=args.dry_run,
        )
        prefix = "would set" if result.dry_run else "set"
        if not result.changed:
            out.line(f"{path}: already locked to 16:9; no change made.")
        else:
            out.line(f"{path}: {prefix} {VIDEO_KEY}.{ASPECT_RATIO_KEY} = {TARGET_ASPECT_RATIO!r}")
            out.detail(f"  previous value = {_format_value(result.previous_value)}")
            if result.backup_path:
                out.line(f"  backup: {result.backup_path}")
            elif result.dry_run:
                out.detail("  backup: skipped for --dry-run")
        results.append(
            {
                "path": str(result.path),
                "changed": result.changed,
                "previous_value": result.previous_value,
                "backup": str(result.backup_path) if result.backup_path else None,
                "dry_run": result.dry_run,
            }
        )
    if not args.dry_run and any(item["changed"] for item in results):
        out.line("Fully quit and relaunch TTR to see the change.")
    out.emit("install", ok=True, value=TARGET_ASPECT_RATIO, results=results)
    return EXIT_OK


def cmd_restore(args: argparse.Namespace, config: Config, out: Output) -> int:
    backup_dir = _selected_backup_dir(args, config)
    paths = resolve_settings_paths(_explicit_paths(args), config=config, all_paths=args.all)
    if args.backup and args.latest:
        raise AspectLockError("Use either --backup PATH or --latest, not both.")
    if args.backup and len(paths) > 1:
        raise AspectLockError("--backup restores a single file; select one --settings path.")
    results = []
    for path in paths:
        backup = (
            Path(args.backup).expanduser()
            if args.backup
            else newest_backup(path, backup_dir)
        )
        result = restore_settings(path, backup, dry_run=args.dry_run)
        prefix = "would restore" if result.dry_run else "restored"
        out.line(f"{path}: {prefix} from {result.backup_path}")
        results.append(
            {
                "path": str(result.path),
                "backup": str(result.backup_path),
                "dry_run": result.dry_run,
            }
        )
    if not args.dry_run:
        out.line("Fully quit and relaunch TTR to see the restored settings.")
    out.emit(args.command, ok=True, results=results)
    return EXIT_OK


def _client_running() -> Optional[bool]:
    """Best-effort check for a live TTR process; ``None`` means undetermined."""
    try:
        if os.name == "nt":
            completed = subprocess.run(
                ["tasklist"], capture_output=True, text=True, timeout=10, check=False
            )
        else:
            completed = subprocess.run(
                ["ps", "-A", "-o", "comm="], capture_output=True, text=True, timeout=10, check=False
            )
    except (OSError, subprocess.SubprocessError):
        return None
    if completed.returncode != 0:
        return None
    listing = completed.stdout.lower()
    return any(name in listing for name in ("toontown", "ttrengine", "ttr-launcher"))


def _writable(path: Path) -> bool:
    return os.access(path, os.W_OK) and os.access(path.parent, os.W_OK)


def cmd_doctor(args: argparse.Namespace, config: Config, out: Output) -> int:
    checks: list[dict[str, Any]] = []

    def record(name: str, level: str, message: str, **extra: Any) -> None:
        checks.append({"name": name, "level": level, "message": message, **extra})

    python_ok = sys.version_info >= MIN_PYTHON
    record(
        "python",
        "ok" if python_ok else "error",
        f"Python {platform_module.python_version()} on {sys.platform}"
        + ("" if python_ok else f" (requires {MIN_PYTHON[0]}.{MIN_PYTHON[1]}+)"),
    )
    record("version", "ok", f"{APP_NAME} {__version__}")

    if config.source and config.source.is_file():
        record("config", "ok", f"Loaded configuration {config.source}", path=str(config.source))
    elif args.config:
        record("config", "error", f"Configuration file not found: {args.config}")
    else:
        record("config", "ok", "No configuration file in use (defaults apply)")

    paths = _readonly_paths(args, config)
    if paths:
        record(
            "discovery",
            "ok",
            f"Found {len(paths)} settings file(s)",
            found=[str(path) for path in paths],
        )
    else:
        record(
            "discovery",
            "error",
            "No settings.json found. Start TTR once, or pass --settings PATH.",
            candidates=[str(path) for path in platform_settings_candidates()],
        )

    backup_dir = _selected_backup_dir(args, config)
    for path in paths:
        entry = _status_entry(path, backup_dir)
        if entry.get("error"):
            record("settings", "error", f"{path}: {entry['error']}", path=str(path))
            continue
        record(
            "settings",
            "ok",
            f"{path}: readable JSON, {VIDEO_KEY}.{ASPECT_RATIO_KEY} = "
            f"{_format_value(entry['value'])}"
            + (" (locked to 16:9)" if entry["locked"] else ""),
            path=str(path),
            value=entry["value"],
            locked=entry["locked"],
        )
        record(
            "writable",
            "ok" if _writable(path) else "error",
            f"{path}: {'writable' if _writable(path) else 'not writable by this user'}",
            path=str(path),
        )
        record(
            "backups",
            "ok" if entry["backups"] else "warn",
            f"{path}: {entry['backups']} backup(s)"
            + ("" if entry["backups"] else " — none yet; install creates one"),
            path=str(path),
            count=entry["backups"],
        )

    running = _client_running()
    if running is None:
        record("client", "warn", "Could not determine whether TTR is running; close it to be safe.")
    elif running:
        record("client", "warn", "A Toontown Rewritten process appears to be running. Quit it first.")
    else:
        record("client", "ok", "No Toontown Rewritten process detected")

    symbols = {"ok": "OK  ", "warn": "WARN", "error": "FAIL"}
    for check in checks:
        out.line(f"[{symbols[check['level']]}] {check['name']}: {check['message']}")
    errors = [check for check in checks if check["level"] == "error"]
    warnings = [check for check in checks if check["level"] == "warn"]
    out.line()
    out.line(
        f"{len(checks) - len(errors) - len(warnings)} ok, {len(warnings)} warning(s), "
        f"{len(errors)} problem(s)."
    )
    out.emit("doctor", ok=not errors, checks=checks)
    return EXIT_ERROR if errors else EXIT_OK


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog=APP_NAME,
        description=(
            "Set Toontown Rewritten's experimental video.forced-aspect-ratio to 16:9 "
            "in your own settings.json, with a backup and a one-command undo."
        ),
    )
    parser.add_argument("--version", action="version", version=f"{APP_NAME} {__version__}")

    def add_common_options(target: argparse.ArgumentParser, *, after_command: bool = False) -> None:
        """Accept common options on either side of a command name.

        ``argparse`` normally only accepts global options before a subcommand,
        while people naturally use forms such as ``status --verbose``.  Child
        defaults are suppressed so they never replace a value already parsed at
        the top level.
        """
        default = argparse.SUPPRESS if after_command else None
        # Switches keep a real ``False`` at the top level so JSON output reports
        # ``false`` rather than ``null`` when a flag was simply not passed.
        flag_default = argparse.SUPPRESS if after_command else False
        target.add_argument("--config", metavar="PATH", default=default, help="TOML configuration file to load")
        target.add_argument(
            "--settings",
            "--path",
            dest="settings",
            metavar="PATH",
            action="append",
            default=default,
            help="settings.json to act on; repeatable (alias: --path)",
        )
        target.add_argument("--json", action="store_true", default=flag_default, help="emit machine-readable JSON only")
        target.add_argument("--verbose", "-v", action="store_true", default=flag_default, help="include extra detail")
        target.add_argument("--dry-run", action="store_true", default=flag_default, help="preview without writing")

    add_common_options(parser)
    subparsers = parser.add_subparsers(dest="command", metavar="COMMAND")

    def add(name: str, help_text: str, handler: Callable[..., int]) -> argparse.ArgumentParser:
        sub = subparsers.add_parser(name, help=help_text, description=help_text)
        add_common_options(sub, after_command=True)
        sub.set_defaults(handler=handler)
        return sub

    backup_dir_help = "backup directory; a relative path resolves beside each settings file"

    add("discover", "List candidate and existing settings.json locations.", cmd_discover)
    for name, help_text in (
        ("status", "Show the stored forced-aspect-ratio for each settings file."),
        ("doctor", "Run environment and settings diagnostics."),
    ):
        # Read-only commands take --backup-dir so they report the same backups
        # that install and restore would use.
        add(name, help_text, cmd_status if name == "status" else cmd_doctor).add_argument(
            "--backup-dir", metavar="PATH", help=backup_dir_help
        )

    install = add("install", "Set video.forced-aspect-ratio to 16:9 after backing up.", cmd_install)
    install.add_argument("--all", action="store_true", help="act on every discovered settings file")
    install.add_argument("--backup-dir", metavar="PATH", help=backup_dir_help)

    for name, help_text in (
        ("restore", "Restore a settings.json from a TTR Aspect Lock backup."),
        ("uninstall", "Undo the change by restoring the latest backup (alias of restore)."),
    ):
        sub = add(name, help_text, cmd_restore)
        sub.add_argument("--all", action="store_true", help="act on every discovered settings file")
        sub.add_argument("--backup", metavar="PATH", help="restore this specific backup file")
        sub.add_argument(
            "--latest", action="store_true", help="restore the newest backup (default)"
        )
        sub.add_argument("--backup-dir", metavar="PATH", help=backup_dir_help)

    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not getattr(args, "handler", None):
        parser.print_help()
        return EXIT_USAGE
    out = Output(json_mode=args.json, verbose=args.verbose)
    try:
        config = _load_cli_config(args)
        return args.handler(args, config, out)
    except AspectLockError as exc:
        if args.json:
            print(json.dumps({"command": args.command, "ok": False, "error": str(exc)}, indent=2))
        else:
            print(f"{APP_NAME}: error: {exc}", file=sys.stderr)
        return EXIT_ERROR
    except KeyboardInterrupt:  # pragma: no cover - interactive only
        print("Interrupted.", file=sys.stderr)
        return EXIT_ERROR
