"""Loading of the small, optional TOML configuration file."""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
from typing import Any, Mapping, Optional, Sequence

from .errors import AspectLockError

try:  # Python 3.11+
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - covered on supported Python 3.9/3.10
    import tomli as tomllib  # type: ignore[no-redef]


@dataclass(frozen=True)
class Config:
    """Optional overrides read from TOML.

    Relative paths resolve beside the configuration file, not the caller's current
    directory. This makes a checked-in or portable configuration predictable.
    """

    settings_paths: tuple[Path, ...] = ()
    # Relative when the configuration used a relative backup_directory.
    backup_directory: Optional[Path] = None
    source: Optional[Path] = None


def default_config_path(platform: Optional[str] = None) -> Path:
    """Return the conventional config location without creating it."""
    platform = platform or os.name
    if platform == "nt":
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return base / "ttr-aspect-lock" / "config.toml"


def _as_path(value: Any, key: str, source: Path) -> Path:
    if not isinstance(value, str) or not value.strip():
        raise AspectLockError(f"{source}: {key} must be a non-empty string")
    path = Path(value).expanduser()
    return path if path.is_absolute() else source.parent / path


def _as_unanchored_path(value: Any, key: str, source: Path) -> Path:
    if not isinstance(value, str) or not value.strip():
        raise AspectLockError(f"{source}: {key} must be a non-empty string")
    return Path(value).expanduser()


def _as_path_list(value: Any, key: str, source: Path) -> Sequence[Path]:
    if not isinstance(value, list):
        raise AspectLockError(f"{source}: {key} must be an array of paths")
    return [_as_path(item, key, source) for item in value]


def load_config(path: Path, *, required: bool = False) -> Config:
    """Load a TOML config file, returning an empty config when it is optional."""
    path = Path(path).expanduser()
    if not path.exists():
        if required:
            raise AspectLockError(f"Configuration file not found: {path}")
        return Config(source=path)
    if not path.is_file():
        raise AspectLockError(f"Configuration path is not a file: {path}")
    try:
        with path.open("rb") as handle:
            raw = tomllib.load(handle)
    except (OSError, tomllib.TOMLDecodeError) as exc:
        raise AspectLockError(f"Could not read configuration {path}: {exc}") from exc
    if not isinstance(raw, Mapping):  # defensive: tomllib currently always returns dict
        raise AspectLockError(f"{path}: configuration root must be a TOML table")

    # Accept a named table as well as root keys so the short portable form and a
    # more namespaced form both remain stable.
    section = raw.get("ttr-aspect-lock", raw)
    if not isinstance(section, Mapping):
        raise AspectLockError(f"{path}: [ttr-aspect-lock] must be a TOML table")

    paths: list[Path] = []
    if "settings_path" in section:
        paths.append(_as_path(section["settings_path"], "settings_path", path))
    if "settings_paths" in section:
        paths.extend(_as_path_list(section["settings_paths"], "settings_paths", path))
    # A relative backup_directory stays relative here; callers anchor it beside
    # each settings file so a shared config never writes into the caller's cwd.
    backup_directory = (
        _as_unanchored_path(section["backup_directory"], "backup_directory", path)
        if "backup_directory" in section
        else None
    )
    return Config(settings_paths=tuple(paths), backup_directory=backup_directory, source=path)
