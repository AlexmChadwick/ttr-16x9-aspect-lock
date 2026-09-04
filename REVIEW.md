# Final confidence review — TTR Aspect Lock

**Date:** 2026-09-04 UTC (user local: 2026-09-03 evening, America/New_York)  
**Reviewer role:** Codex/Sol-equivalent final confidence pass (Cloud Agent Sol was unavailable on plan; review executed in-workspace against the same checklist).  
**Scope:** `LICENSE`, `pyproject.toml`, `src/`, `scripts/`, `tests/`, player docs.

## Verdict

| Item | Result |
| --- | --- |
| MIT ok? | **Yes** |
| Bugs fixed | **1** (install/status float consistency) |
| pytest | **142 passed** (was 141; +1 regression for the fix) |
| Official plugin path for aspect lock? | **No** |

## 1. MIT license

- `LICENSE` is the full MIT text (Copyright (c) 2026 TTR Aspect Lock contributors).
- `pyproject.toml`: `license = { text = "MIT" }` and classifier
  `License :: OSI Approved :: MIT License`.
- README / FAQ / STATUS now state MIT explicitly.

## 2. Code review findings

### Correctness

- Target ratio is exactly Python `16 / 9` (`1.7777777777777777`).
- Install only mutates `video.forced-aspect-ratio`; unrelated JSON keys preserved.
- Atomic write via temp file + `os.replace`; restore validates backup JSON first.
- Discovery is limited to known user-data candidates (plus optional config paths); no disk-wide scan.
- Mutation commands refuse ambiguous multi-file discovery unless `--all` or explicit `--settings`.
- Relative `--backup-dir` anchors beside each settings file; restore also searches the settings directory.
- PowerShell wrappers only set `PYTHONPATH` for the child process; no global install.
- Release packaging rejects proprietary-client-style assets (`.mf`, phase files, etc.).

### Safety

- Timestamped whole-file backups before real writes; dry-run writes nothing.
- No client injection, DLL/hooks, memory access, or binary patching anywhere in `src/` / `scripts/`.
- No secrets, credentials, or token handling found.
- Tests sandbox `HOME` / platform env vars and never touch a real TTR install.

### Edge cases checked

- Missing / invalid JSON, non-object `video`, dry-run, idempotent reinstall, backup collision naming, multi-path ambiguity, Wine/Proton candidate roots, doctor best-effort process check.

### Bug fixed

**Install vs status float mismatch.**  
`status` treated near-target floats as locked via `math.isclose`, but `apply_aspect_ratio` used exact `==`, so a near-16/9 value could report locked and still create a new backup on install.  
**Fix:** shared `ratios_match()` used by both apply and `is_locked`. Regression test added.

No other real bugs found. Architecture intentionally remains settings.json-based.

## 3. Content Pack / plugin path

Research remains closed:

- Official Content Packs (`.mf` in `resources/`) may change **textures, audio, fonts, cursor only**.
- They **cannot** change aspect ratio, UI layout, or models.
- There is **no official TTR plugin/API** that locks aspect ratio.
- Classic Pack documents `video.forced-aspect-ratio` ≈ `1.333` for 4:3; this project uses `16/9` analogously and labels it experimental.

Docs updated to say this bluntly (`README.md`, `docs/FAQ.md`, `STATUS.md`).

## 4. Changes made in this review

- `src/ttr_aspect_lock/settings.py` — `ratios_match`; install idempotency uses it
- `src/ttr_aspect_lock/cli.py` — `is_locked` delegates to `ratios_match`
- `tests/test_settings.py` — near-float idempotency test
- `README.md`, `docs/FAQ.md`, `STATUS.md` — blunt Content Pack / experimental / MIT wording
- `REVIEW.md` — this file

## 5. Test run

```text
142 passed
```

Command: `.venv/bin/pytest -q` after editable install in a local venv.
