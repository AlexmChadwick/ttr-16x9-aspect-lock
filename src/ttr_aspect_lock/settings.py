"""Read, change, back up, and restore settings.json without client modification."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
import math
import os
from pathlib import Path
import shutil
import stat
import tempfile
from typing import Any, Mapping, Optional

from .constants import ASPECT_RATIO_KEY, BACKUP_MARKER, TARGET_ASPECT_RATIO, VIDEO_KEY
from .errors import BackupNotFoundError, InvalidSettingsError, SettingsNotFoundError


@dataclass(frozen=True)
class ApplyResult:
    path: Path
    changed: bool
    previous_value: Any
    backup_path: Optional[Path]
    dry_run: bool


@dataclass(frozen=True)
class RestoreResult:
    path: Path
    backup_path: Path
    dry_run: bool


def ratios_match(value: Any, ratio: float = TARGET_ASPECT_RATIO) -> bool:
    """True when value is a number within float precision of the target ratio."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    return math.isclose(float(value), float(ratio), rel_tol=1e-9, abs_tol=1e-12)


def read_settings(path: Path) -> dict[str, Any]:
    """Parse a settings JSON object or raise a clear domain error."""
    path = Path(path)
    if not path.is_file():
        raise SettingsNotFoundError(f"Settings file not found: {path}")
    try:
        with path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        raise InvalidSettingsError(f"Could not parse JSON in {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise InvalidSettingsError(f"Settings file must contain a JSON object: {path}")
    return data


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError as exc:
        raise InvalidSettingsError(f"Could not read settings file {path}: {exc}") from exc


def _indent_for(text: str) -> int:
    # Preserve the common indentation style where detectable. JSON permits no
    # comments, so rewriting it through the standard library remains safe.
    for line in text.splitlines()[1:]:
        stripped = line.lstrip(" ")
        if stripped.startswith('"'):
            return len(line) - len(stripped)
    return 2


def _serialise(data: Mapping[str, Any], original_text: str) -> str:
    payload = json.dumps(data, ensure_ascii=False, indent=_indent_for(original_text))
    return payload + ("\n" if original_text.endswith(("\n", "\r")) else "")


def _backup_filename(settings_path: Path) -> str:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    return f"{settings_path.name}{BACKUP_MARKER}{timestamp}.bak"


def create_backup(settings_path: Path, backup_dir: Optional[Path] = None) -> Path:
    """Copy settings metadata and contents to a unique timestamped backup file."""
    directory = Path(backup_dir) if backup_dir else settings_path.parent
    try:
        directory.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise InvalidSettingsError(f"Could not create backup directory {directory}: {exc}") from exc
    candidate = directory / _backup_filename(settings_path)
    suffix = 1
    while candidate.exists():
        candidate = directory / f"{_backup_filename(settings_path)}.{suffix}"
        suffix += 1
    try:
        shutil.copy2(settings_path, candidate)
    except OSError as exc:
        raise InvalidSettingsError(f"Could not create backup {candidate}: {exc}") from exc
    return candidate


def _atomic_write(path: Path, text: str) -> None:
    """Write beside the target and replace it only after a complete flush."""
    try:
        source_mode = stat.S_IMODE(path.stat().st_mode)
        descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
        temporary = Path(temporary_name)
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8", newline="") as handle:
                handle.write(text)
                handle.flush()
                os.fsync(handle.fileno())
            os.chmod(temporary, source_mode)
            os.replace(temporary, path)
        except BaseException:
            temporary.unlink(missing_ok=True)
            raise
    except OSError as exc:
        raise InvalidSettingsError(f"Could not write settings file {path}: {exc}") from exc


def apply_aspect_ratio(
    path: Path,
    ratio: float = TARGET_ASPECT_RATIO,
    *,
    backup_dir: Optional[Path] = None,
    dry_run: bool = False,
) -> ApplyResult:
    """Set ``video.forced-aspect-ratio`` and create a backup before changing it."""
    if not isinstance(ratio, (float, int)) or isinstance(ratio, bool) or ratio <= 0:
        raise ValueError("ratio must be a positive number")
    path = Path(path)
    text = _read_text(path)
    data = read_settings(path)
    video = data.get(VIDEO_KEY)
    if video is None:
        video = {}
        data[VIDEO_KEY] = video
    if not isinstance(video, dict):
        raise InvalidSettingsError(f"{path}: {VIDEO_KEY!r} must be a JSON object")
    previous = video.get(ASPECT_RATIO_KEY)
    target = float(ratio)
    if ratios_match(previous, target):
        return ApplyResult(path, False, previous, None, dry_run)
    if dry_run:
        return ApplyResult(path, True, previous, None, True)
    backup_path = create_backup(path, backup_dir)
    video[ASPECT_RATIO_KEY] = target
    _atomic_write(path, _serialise(data, text))
    return ApplyResult(path, True, previous, backup_path, False)


def _is_backup_name(name: str, prefix: str) -> bool:
    """Match ``<settings>.<marker><stamp>.bak`` and its ``.bak.N`` collision form."""
    if not name.startswith(prefix):
        return False
    remainder = name[len(prefix) :]
    if remainder.endswith(".bak"):
        return True
    head, _, tail = remainder.rpartition(".")
    return head.endswith(".bak") and tail.isdigit()


def available_backups(settings_path: Path, backup_dir: Optional[Path] = None) -> list[Path]:
    """List compatible backups newest first, limited to this settings filename."""
    directory = Path(backup_dir) if backup_dir else settings_path.parent
    if not directory.is_dir():
        return []
    prefix = f"{settings_path.name}{BACKUP_MARKER}"
    return sorted(
        (
            candidate
            for candidate in directory.iterdir()
            if candidate.is_file() and _is_backup_name(candidate.name, prefix)
        ),
        key=lambda candidate: candidate.name,
        reverse=True,
    )


def latest_backup(settings_path: Path, backup_dir: Optional[Path] = None) -> Path:
    backups = available_backups(settings_path, backup_dir)
    if not backups:
        raise BackupNotFoundError(f"No TTR Aspect Lock backup found for {settings_path}")
    return backups[0]


def restore_settings(path: Path, backup_path: Path, *, dry_run: bool = False) -> RestoreResult:
    """Restore an explicitly selected backup atomically after JSON validation."""
    path = Path(path)
    backup_path = Path(backup_path)
    if not path.is_file():
        raise SettingsNotFoundError(f"Settings file not found: {path}")
    if not backup_path.is_file():
        raise BackupNotFoundError(f"Backup file not found: {backup_path}")
    # Validate the backup before touching the live settings file.
    read_settings(backup_path)
    if not dry_run:
        _atomic_write(path, _read_text(backup_path))
    return RestoreResult(path, backup_path, dry_run)
