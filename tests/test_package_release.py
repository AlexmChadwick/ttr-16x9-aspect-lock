from __future__ import annotations

from pathlib import Path
import subprocess
import pytest


def test_package_release_help() -> None:
    repo_root = Path(__file__).resolve().parent.parent
    script_path = repo_root / "scripts" / "package_release.sh"
    result = subprocess.run(
        ["bash", str(script_path), "--help"],
        cwd=str(repo_root),
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "Build a portable, deterministic, reproducible source release ZIP" in result.stdout


def test_package_release_dry_run() -> None:
    repo_root = Path(__file__).resolve().parent.parent
    script_path = repo_root / "scripts" / "package_release.sh"
    result = subprocess.run(
        ["bash", str(script_path), "--dry-run"],
        cwd=str(repo_root),
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "DRY RUN" in result.stdout
    assert "Proprietary client scan: 0 proprietary assets detected (PASS)" in result.stdout


def test_package_release_rejects_proprietary_client_files(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parent.parent
    script_path = repo_root / "scripts" / "package_release.sh"

    # Create a minimal release tree containing a forbidden proprietary file in assets
    (tmp_path / "src" / "ttr_aspect_lock").mkdir(parents=True)
    (tmp_path / "src" / "ttr_aspect_lock" / "__init__.py").write_text("", encoding="utf-8")
    (tmp_path / "VERSION").write_text("1.0.0\n", encoding="utf-8")
    (tmp_path / "pyproject.toml").write_text('version = "1.0.0"\n', encoding="utf-8")
    (tmp_path / "assets").mkdir(parents=True)
    (tmp_path / "assets" / "phase_3.mf").write_bytes(b"mock multifile")

    result = subprocess.run(
        ["bash", str(script_path), "--dry-run", str(tmp_path)],
        cwd=str(tmp_path),
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    assert "PROPRIETARY CLIENT ERROR" in result.stderr
