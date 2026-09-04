"""Shared fixtures. Tests never touch a real TTR installation or the real HOME."""

from __future__ import annotations

import json
from pathlib import Path
import sys

import pytest

SRC = Path(__file__).resolve().parents[1] / "src"
if str(SRC) not in sys.path:  # keep tests runnable without an editable install
    sys.path.insert(0, str(SRC))

SAMPLE_SETTINGS = {
    "audio": {"music-volume": 0.7},
    "video": {"fullscreen": True, "forced-aspect-ratio": 0.0},
    "toon": {"last-used": "Flippy"},
}


def write_settings(path: Path, data: dict | None = None, *, indent: int = 4) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = SAMPLE_SETTINGS if data is None else data
    path.write_text(json.dumps(payload, indent=indent) + "\n", encoding="utf-8")
    return path


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.fixture
def settings_file(tmp_path: Path) -> Path:
    return write_settings(tmp_path / "ttr" / "settings.json")


@pytest.fixture(autouse=True)
def isolated_home(tmp_path, monkeypatch):
    """Point HOME and platform env vars at a scratch directory for every test."""
    home = tmp_path / "home"
    home.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("USERPROFILE", str(home))
    monkeypatch.setenv("XDG_DATA_HOME", str(home / ".local" / "share"))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(home / ".config"))
    monkeypatch.setenv("LOCALAPPDATA", str(home / "AppData" / "Local"))
    monkeypatch.setenv("APPDATA", str(home / "AppData" / "Roaming"))
    monkeypatch.delenv("WINEPREFIX", raising=False)
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: home))
    return home
