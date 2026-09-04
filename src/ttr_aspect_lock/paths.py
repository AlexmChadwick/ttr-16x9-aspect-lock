"""Platform-aware discovery and safe selection of TTR's settings file."""

from __future__ import annotations

import os
from pathlib import Path
import sys
from typing import Iterable, Optional, Sequence

from .config import Config
from .constants import SETTINGS_FILENAME
from .errors import AmbiguousSettingsError, SettingsNotFoundError


TTR_DIRECTORY_NAME = "Toontown Rewritten"
# Launcher versions have kept settings.json either directly in the user-data
# directory or beside the downloaded resources.
_RELATIVE_SETTINGS = (Path(SETTINGS_FILENAME), Path("resources") / SETTINGS_FILENAME)


def _settings_in(root: Path) -> tuple[Path, ...]:
    return tuple(root / relative for relative in _RELATIVE_SETTINGS)


def _wine_roots(home: Path) -> tuple[Path, ...]:
    """Return Wine/Proton AppData roots for the common prefix layouts."""
    prefixes = [Path(os.environ["WINEPREFIX"])] if os.environ.get("WINEPREFIX") else []
    prefixes.append(home / ".wine")
    roots: list[Path] = []
    for prefix in prefixes:
        users = prefix / "drive_c" / "users"
        for user in (os.environ.get("USER") or home.name, "steamuser"):
            if not user:
                continue
            roots.append(users / user / "AppData" / "Local" / TTR_DIRECTORY_NAME)
            roots.append(users / user / "AppData" / "Roaming" / TTR_DIRECTORY_NAME)
    return tuple(roots)


def platform_settings_candidates(platform: Optional[str] = None) -> tuple[Path, ...]:
    """Return known user-data locations, whether or not they exist.

    TTR's storage location has varied between launcher versions. We only inspect
    user-data directories and never scan disks or an installation directory.
    """
    platform = platform or sys.platform
    home = Path.home()
    if platform.startswith("win") or platform == "cygwin" or os.name == "nt":
        local = Path(os.environ.get("LOCALAPPDATA", home / "AppData" / "Local"))
        roaming = Path(os.environ.get("APPDATA", home / "AppData" / "Roaming"))
        return (
            *_settings_in(local / TTR_DIRECTORY_NAME),
            *_settings_in(roaming / TTR_DIRECTORY_NAME),
        )
    if platform == "darwin":
        support = home / "Library" / "Application Support" / TTR_DIRECTORY_NAME
        return _settings_in(support)
    data_home = Path(os.environ.get("XDG_DATA_HOME", home / ".local" / "share"))
    roots = (
        data_home / TTR_DIRECTORY_NAME,
        home / ".config" / TTR_DIRECTORY_NAME,
        *_wine_roots(home),
    )
    return tuple(path for root in roots for path in _settings_in(root))


def _unique(paths: Iterable[Path]) -> list[Path]:
    seen: set[Path] = set()
    result: list[Path] = []
    for path in paths:
        expanded = Path(path).expanduser()
        try:
            normalized = expanded.resolve(strict=False)
        except OSError:
            normalized = expanded.absolute()
        if normalized not in seen:
            seen.add(normalized)
            result.append(normalized)
    return result


def discover_settings_paths(
    *, config: Optional[Config] = None, platform: Optional[str] = None
) -> list[Path]:
    """Find existing settings files from configuration and platform conventions."""
    configured = config.settings_paths if config else ()
    candidates = _unique((*configured, *platform_settings_candidates(platform)))
    return [path for path in candidates if path.is_file()]


def resolve_settings_paths(
    explicit_paths: Sequence[Path] = (),
    *,
    config: Optional[Config] = None,
    all_paths: bool = False,
    platform: Optional[str] = None,
) -> list[Path]:
    """Select settings paths, refusing an ambiguous implicit mutation by default."""
    if explicit_paths:
        selected = _unique(explicit_paths)
        missing = [str(path) for path in selected if not path.is_file()]
        if missing:
            raise SettingsNotFoundError("Settings file not found: " + ", ".join(missing))
        return selected
    found = discover_settings_paths(config=config, platform=platform)
    if not found:
        raise SettingsNotFoundError(
            "Could not find settings.json. Start Toontown Rewritten once, or pass --settings PATH."
        )
    if len(found) > 1 and not all_paths:
        rendered = "\n  ".join(str(path) for path in found)
        raise AmbiguousSettingsError(
            "More than one settings file was found. Pass --settings PATH or --all:\n  " + rendered
        )
    return found
