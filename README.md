# TTR Aspect Lock

TTR Aspect Lock is a small, reversible command-line tool for setting Toontown
Rewritten's experimental `video.forced-aspect-ratio` preference to 16:9. It
only reads and updates a player-owned `settings.json`; before a real change it
creates a timestamped copy of the complete file.

It does not modify, inject into, inspect, or redistribute the TTR client. The
setting is experimental, so the client—not this tool—controls the eventual
presentation. Verify the result in game and restore the backup if it is not
right for your client build or display.

## What changes

The installed value is Python's exact `16 / 9` float:

```json
"video": { "forced-aspect-ratio": 1.7777777777777777 }
```

Existing JSON settings are preserved apart from this one key. `restore` and
`uninstall` restore a complete, validated pre-change backup; they do not guess
at a previous value.

On a wider display a centered 16:9 frame may produce side pillars. On a taller
or narrower display it may produce top/bottom bars. These are expected geometry
examples, not a guarantee of any particular in-game UI result; see the
[resolution matrix](docs/RESOLUTION_MATRIX.md) and [manual checklist](docs/MANUAL_TEST.md).

## Why not a Content Pack?

Official TTR Content Packs (`.mf` files in `resources/`) **cannot** lock aspect
ratio, change UI layout, or replace models. They may only alter textures, audio,
fonts, and the cursor. There is **no official plugin API** for aspect locking.

Editing player-owned `settings.json` (`video.forced-aspect-ratio`) is therefore
the intentional approach. The setting is **experimental**: the client—not this
tool—decides how it renders. This project is **MIT** licensed.

## Quick start

Requirements: Python 3.9+ and a fully closed TTR launcher/client. From an
extracted release folder:

```bash
python -m pip install .
ttr-aspect-lock discover --verbose
ttr-aspect-lock doctor
ttr-aspect-lock install --dry-run
ttr-aspect-lock install
```

Use `python -m ttr_aspect_lock` in place of `ttr-aspect-lock` if preferred.
Run `--help` on the main command or any subcommand for the installed version's
authoritative option list.

Windows users may instead run the local wrapper (it requires Python 3.11+ and
does not install a global command):

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\scripts\install.ps1 -DryRun
.\scripts\install.ps1
```

If discovery finds more than one file, select one explicitly or deliberately
apply to all discovered files:

```bash
ttr-aspect-lock --settings "C:\path\to\settings.json" install
ttr-aspect-lock install --all
```

## Commands and common options

```text
ttr-aspect-lock discover
ttr-aspect-lock status [--backup-dir PATH]
ttr-aspect-lock doctor [--backup-dir PATH]
ttr-aspect-lock install [--all] [--backup-dir PATH]
ttr-aspect-lock restore [--all] [--backup PATH | --latest] [--backup-dir PATH]
ttr-aspect-lock uninstall [--all] [--backup PATH | --latest] [--backup-dir PATH]
```

`--settings PATH` (or `--path PATH`) is repeatable and can be placed before or
after the command. `--config PATH`, `--dry-run`, `--verbose`/`-v`, and `--json`
also work on either side of a command. `--dry-run` is useful before `install` or
`restore`: it does not write a settings file or create a backup.

A relative `--backup-dir` resolves beside each settings file rather than in the
current directory, and `restore`/`uninstall` fall back to the settings file's own
directory when the selected backup directory holds no backup.

`status` reports every selected/discovered existing file. `install`, `restore`,
and `uninstall` refuse an ambiguous implicit selection unless `--all` is given.
`doctor` checks discovery, JSON readability, write access, backups, and makes a
best-effort process check; close TTR even if that check says no client was found.

Copy [config.example.toml](config.example.toml) if you want persistent paths or
a backup directory. Command-line `--settings` takes precedence over configured
paths.

## Undo

Quit TTR first, then restore the newest matching backup:

```bash
ttr-aspect-lock restore --latest
# `uninstall` is an alias of `restore`
ttr-aspect-lock uninstall --latest
```

For Windows wrapper users:

```powershell
.\scripts\uninstall.ps1 -DryRun
.\scripts\uninstall.ps1
```

Keep the backup until you have verified the game. You may delete the extracted
tool folder after restoring if you no longer need it.

## Safety and troubleshooting

- Close TTR before `install`, `restore`, `uninstall`, or manual editing. A
  client write can overwrite a simultaneous external change.
- `discover --verbose` shows every conventional candidate considered. For a
  nonstandard location, pass the exact `--settings` path.
- If the game looks unchanged, fully quit/relaunch it and run `status`. A video
  setting change inside TTR may rewrite its configuration.
- If the UI or client behaves unexpectedly, quit it and run `restore --latest`.
  Do not assume a client update will retain experimental-setting behavior.

See [installation and discovery](docs/INSTALL.md), the [FAQ](docs/FAQ.md), and
the [manual in-game verification](docs/MANUAL_TEST.md).

## Development and release

```bash
python -m pip install -e ".[dev]"
pytest
./scripts/package_release.sh --dry-run
./scripts/package_release.sh
```

The release script writes a deterministic ZIP and SHA-256 files under `dist/`
and rejects included proprietary-client-style assets. Maintainers can follow
the release/push checklist in [INSTALL.md](docs/INSTALL.md#maintainer-release-and-push-checklist).

## License

MIT — see [LICENSE](LICENSE).
