# TTR 16:9 UI Aspect Lock — Release status

Status: release-ready local source tree (2026-09-04 UTC).

**Approach (blunt):** Official Content Packs cannot lock aspect ratio / UI layout
/ models (textures, audio, fonts, cursor only). There is no official plugin API.
This tool intentionally edits player-owned `settings.json`
(`video.forced-aspect-ratio` = `16/9`). That setting is experimental. Licensed
**MIT**.

This standalone package edits only player-owned `settings.json` files. It does
not bundle, patch, inspect, inject into, or redistribute the TTR client. Its
16:9 setting is experimental client behavior; the manual verification guide is
the final in-game acceptance check.

## Completed scope

- Reversible `install`, `restore`/`uninstall`, `status`, `discover`, and
  `doctor` commands, plus Windows wrappers.
- Timestamped whole-file JSON backup and validated, atomic restore.
- Explicit-path, platform, Wine/Proton, and configuration-file discovery with
  an ambiguity guard for mutations.
- Player documentation, FAQ, resolution diagrams, a deterministic source ZIP,
  SHA-256 verification files, and a packaging scan that rejects
  proprietary-client-style assets.
- Source-cited compatibility research in `docs/research/`.

## Release checks

Run the following from a clean checkout before publishing:

```bash
python -m pip install -e ".[dev]"
pytest -q
python -m compileall -q src
python -m ttr_aspect_lock --help
./scripts/package_release.sh --dry-run
./scripts/package_release.sh
(cd dist && sha256sum -c "ttr-aspect-lock-$(tr -d '\n' < ../VERSION).zip.sha256")
```

`PUSH_INSTRUCTIONS.md` records the manual public-publish steps for
`AlexmChadwick/ttr-16x9-aspect-lock`. Authentication and any network publish
are intentionally outside this workspace.

## Final local verification

- `141 passed` with Python 3.13.5.
- CLI help and bytecode compilation passed.
- The 34-file release ZIP was built twice with identical bytes and passed
  `unzip -t` plus SHA-256 verification.
- Final artifact: `dist/ttr-aspect-lock-1.0.0.zip`
  (`39553f353e51e994643647066bbf7725df03676312e8e6268428cd55f26cfed8`).
- The source and archive scans found no credential signatures, caches,
  backups, VCS metadata, or proprietary-client-style assets.

## Implementation complete — 2026-09-04 UTC

- `src/ttr_aspect_lock/cli.py` implements `discover`, `status`, `install`,
  `restore`, `uninstall` (a `restore` alias), and `doctor` on top of the existing
  `config`/`paths`/`settings` modules. Common options (`--settings`, `--config`,
  `--dry-run`, `--verbose`, `--json`) are accepted on either side of a command,
  and `python -m ttr_aspect_lock` works straight from `src/` so the PowerShell
  wrappers install nothing globally.
- Discovery now also covers the `resources/settings.json` layout and Wine/Proton
  `drive_c` AppData roots, matching `docs/INSTALL.md`.
- Relative backup directories resolve beside each settings file instead of the
  caller's working directory; `restore`/`uninstall` fall back to the settings
  directory so an undo still works if the install used a different
  `--backup-dir`.
- pytest suite: **141 passed** (`tests/test_settings.py`, `test_paths.py`,
  `test_config.py`, `test_config_and_paths.py`, `test_cli.py`,
  `test_resolution_matrix.py`, `test_package_release.py`). Tests sandbox `HOME`
  and the platform environment variables, so they never read or write a real TTR
  installation.
- `scripts/install.ps1`, `scripts/uninstall.ps1`, and
  `scripts/package_release.sh` are in place; the release ZIP and SHA256 files in
  `dist/` were rebuilt from the final tree and verified by extracting them and
  running both the test suite and an install/uninstall round trip.
- Scope unchanged: settings-only, no client injection, no proprietary assets.
  16:9 rendering behaviour still requires the manual pass in
  `docs/MANUAL_TEST.md`.

## Confidence review — 2026-09-04 (UTC-4: 2026-09-03 evening)

- MIT confirmed in `LICENSE` and `pyproject.toml` classifiers.
- Code review of `src/`, `scripts/`, `tests/`: settings-only, backup/restore safe,
  no client injection, no secrets.
- One consistency fix: install idempotency now matches `status` float comparison
  (`ratios_match`) so near-16/9 values do not create needless backups.
- Docs updated to state Content Packs cannot lock AR; settings edit is intentional.
- Official plugin path for aspect lock: **does not exist**.
- See [REVIEW.md](REVIEW.md).
