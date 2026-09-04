#!/usr/bin/env bash
# Build a portable, deterministic source release. Requires Python 3.11+.
set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
project_dir="$(cd -- "$script_dir/.." && pwd)"
cd "$project_dir"

if [[ ! -f VERSION || ! -f pyproject.toml || ! -d src/ttr_aspect_lock ]]; then
  printf '%s\n' 'Run this script from a complete ttr-aspect-lock source/release directory.' >&2
  exit 2
fi

python_cmd=""
for candidate in python3 python; do
  if command -v "$candidate" >/dev/null 2>&1 && "$candidate" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)'; then
    python_cmd="$candidate"
    break
  fi
done
if [[ -z "$python_cmd" ]]; then
  printf '%s\n' 'Python 3.11 or newer is required to package a release.' >&2
  exit 2
fi

"$python_cmd" - "$@" <<'PY'
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
from pathlib import Path, PurePosixPath
import os
import re
import sys
import tempfile
import zipfile

parser = argparse.ArgumentParser(
    description="Build a portable, deterministic, reproducible source release ZIP for TTR Aspect Lock."
)
parser.add_argument(
    "root",
    nargs="?",
    default=Path.cwd(),
    type=Path,
    help="Project root directory (defaults to current directory)",
)
parser.add_argument(
    "-o", "--output-dir",
    type=Path,
    default=None,
    help="Output directory for distribution archives (default: <root>/dist)",
)
parser.add_argument(
    "--dry-run",
    action="store_true",
    help="Perform validation and file selection without writing release archive or checksums",
)
parser.add_argument(
    "--verbose", "-v",
    action="store_true",
    help="Show verbose details during packaging",
)

args = parser.parse_args()

root = args.root.resolve()

version_file = root / "VERSION"
if not version_file.is_file():
    sys.stderr.write(f"VERSION file not found in {root}\n")
    sys.exit(2)

version = version_file.read_text(encoding="utf-8").strip()
if not re.fullmatch(r"[0-9]+(?:\.[0-9]+){1,3}(?:[A-Za-z0-9.+-]+)?", version):
    sys.stderr.write(f"VERSION is not a safe release version: {version!r}\n")
    sys.exit(2)

pyproject_file = root / "pyproject.toml"
if not pyproject_file.is_file():
    sys.stderr.write(f"pyproject.toml not found in {root}\n")
    sys.exit(2)

pyproject = pyproject_file.read_text(encoding="utf-8")
match = re.search(r'^version\s*=\s*"([^"]+)"\s*$', pyproject, re.MULTILINE)
if not match or match.group(1) != version:
    sys.stderr.write("VERSION and [project].version in pyproject.toml must match before packaging\n")
    sys.exit(2)

epoch = int(os.environ.get("SOURCE_DATE_EPOCH", "315532800"))  # 1980-01-01, ZIP's earliest date
if epoch < 315532800:
    epoch = 315532800
timestamp = datetime.fromtimestamp(epoch, timezone.utc).replace(microsecond=0)
date_time = timestamp.timetuple()[:6]

include_roots = ("README.md", "LICENSE", "VERSION", "pyproject.toml", "config.example.toml", "scripts", "src", "tests", "docs", "assets")
excluded_parts = {".git", ".venv", "__pycache__", "dist", ".codex", ".pytest_cache"}
excluded_suffixes = {".pyc", ".pyo", "~", ".tmp", ".bak"}
files: list[Path] = []
for item in include_roots:
    candidate = root / item
    if candidate.is_file():
        files.append(candidate)
    elif candidate.is_dir():
        for path in candidate.rglob("*"):
            relative = path.relative_to(root)
            if path.is_file() and not any(part in excluded_parts for part in relative.parts) and path.suffix not in excluded_suffixes:
                files.append(path)

files.sort(key=lambda path: path.relative_to(root).as_posix())
if not files:
    sys.stderr.write("No release files were selected\n")
    sys.exit(2)

# Enforce strict 'No Proprietary Client' policy
PROPRIETARY_PATTERNS = [
    re.compile(r"\.mf$", re.IGNORECASE),
    re.compile(r"^phase_.*", re.IGNORECASE),
    re.compile(r"^TTROptions.*", re.IGNORECASE),
    re.compile(r"^Toontown.*\.exe$", re.IGNORECASE),
    re.compile(r"^ttr_engine.*", re.IGNORECASE),
    re.compile(r"\.(bam|dna|p3d)$", re.IGNORECASE),
]
proprietary_detected = []
for path in files:
    for pattern in PROPRIETARY_PATTERNS:
        if pattern.search(path.name):
            proprietary_detected.append(str(path.relative_to(root)))
            break

if proprietary_detected:
    sys.stderr.write(
        "PROPRIETARY CLIENT ERROR: Release packaging rejected because proprietary game files were detected:\n"
        + "\n".join(f"  - {f}" for f in proprietary_detected)
        + "\nTTR Aspect Lock enforces a strict 'No Proprietary Client' policy.\n"
    )
    sys.exit(1)

release_name = f"ttr-aspect-lock-{version}"
dist = (args.output_dir or (root / "dist")).resolve()
dist.mkdir(exist_ok=True, parents=True)
destination = dist / f"{release_name}.zip"

if args.dry_run:
    print(f"DRY RUN: Verified {len(files)} files for {release_name}.zip (no archive created).")
    print(f"Proprietary client scan: 0 proprietary assets detected (PASS).")
    sys.exit(0)

with tempfile.NamedTemporaryFile(prefix=f".{release_name}.", suffix=".zip", dir=dist, delete=False) as handle:
    temporary = Path(handle.name)

try:
    with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9, strict_timestamps=True) as archive:
        for path in files:
            relative = PurePosixPath(path.relative_to(root).as_posix())
            info = zipfile.ZipInfo(f"{release_name}/{relative.as_posix()}", date_time=date_time)
            info.create_system = 3
            is_executable = relative.suffix in {".sh", ".py"} or relative.name == "package_release.sh"
            info.external_attr = ((0o755 if is_executable else 0o644) & 0xFFFF) << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, path.read_bytes(), compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
        if archive.testzip() is not None:
            sys.stderr.write("Internal ZIP integrity check failed\n")
            sys.exit(1)
    os.replace(temporary, destination)
except BaseException:
    temporary.unlink(missing_ok=True)
    raise

# Calculate SHA256 checksum and write verification files
sha256_hash = hashlib.sha256(destination.read_bytes()).hexdigest()
checksum_file = dist / f"{release_name}.zip.sha256"
checksum_file.write_text(f"{sha256_hash}  {destination.name}\n", encoding="utf-8")

sums_file = dist / "SHA256SUMS"
sums_file.write_text(f"{sha256_hash}  {destination.name}\n", encoding="utf-8")

print(destination)
print(f"files: {len(files)}")
if args.verbose:
    print(f"size: {destination.stat().st_size} bytes")
    print(f"sha256: {sha256_hash}")
    print(f"checksum: {checksum_file}")
    print("compliance: No proprietary client assets detected (100% clean)")
PY
