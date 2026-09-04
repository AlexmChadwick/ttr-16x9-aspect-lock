# Installation and path discovery

## Install the CLI

1. Download and extract a release ZIP to a folder you control.
2. Ensure Python 3.9 or newer is available (`python --version`; on Windows,
   `py --version` also works).
3. Completely quit the TTR launcher and game.
4. From the extracted folder, install the local package:

```bash
python -m pip install .
ttr-aspect-lock discover --verbose
ttr-aspect-lock doctor
```

The tool does not create a TTR folder or scan disks. `discover` lists only
existing files among its conventional candidates. If you prefer not to use the
installed script name, run `python -m ttr_aspect_lock` with the same arguments.

## Automatic locations

TTR storage layouts can change. These are candidates, not promises, and each
root is checked for both `settings.json` and `resources/settings.json`:

| System | Candidate roots |
| --- | --- |
| Windows | `%LOCALAPPDATA%\Toontown Rewritten` and `%APPDATA%\Toontown Rewritten` |
| macOS | `~/Library/Application Support/Toontown Rewritten` |
| Linux | `$XDG_DATA_HOME/Toontown Rewritten` (normally `~/.local/share`) and `~/.config/Toontown Rewritten` |
| Wine / Proton | `$WINEPREFIX` when set, plus `~/.wine`, under common `drive_c/users/<user>/AppData/{Local,Roaming}/Toontown Rewritten` paths |

For a nonstandard installation, use the exact file path:

```bash
ttr-aspect-lock --settings "/absolute/path/to/settings.json" status
ttr-aspect-lock --settings "/absolute/path/to/settings.json" install --dry-run
ttr-aspect-lock --settings "/absolute/path/to/settings.json" install
```

Repeat `--settings` for multiple explicit files. Mutation commands refuse an
ambiguous discovered selection unless you add `--all` intentionally.

## Windows PowerShell wrappers

`scripts/install.ps1` and `scripts/uninstall.ps1` run the package directly from
the extracted folder. They require Python 3.11+ and do not install anything
globally. Their PowerShell parameters are not the CLI's `--option` spelling:

```powershell
# Install/apply
.\scripts\install.ps1 [-Settings <string[]>] [-Config <string>] `
  [-BackupDir <string>] [-All] [-DryRun] [-VerboseOutput] [-Json]

# Restore/uninstall
.\scripts\uninstall.ps1 [-Settings <string[]>] [-Config <string>] `
  [-Backup <string>] [-BackupDir <string>] [-All] [-DryRun] [-VerboseOutput] [-Json]
```

Examples:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\scripts\install.ps1 -Settings "C:\path\to\settings.json" -DryRun -VerboseOutput
.\scripts\install.ps1 -Settings "C:\path\to\settings.json" -BackupDir "backups"
.\scripts\uninstall.ps1 -Settings "C:\path\to\settings.json" -DryRun
.\scripts\uninstall.ps1 -Settings "C:\path\to\settings.json"
```

Omit `-Settings` to use discovery. `-Backup` selects one explicit backup and
cannot be combined with `-All`; otherwise the uninstall wrapper restores the
newest matching backup.

## Optional configuration

Copy [config.example.toml](../config.example.toml) and pass it explicitly:

```bash
ttr-aspect-lock --config config.toml status
```

`settings_path` chooses one file; `settings_paths` chooses several. An explicit
`--settings` overrides configured paths. A relative `backup_directory` is
anchored beside each selected settings file, not the current working directory.

## Backup and restore

Every actual `install` first writes a timestamped `.bak` copy of the entire
selected `settings.json`. By default it is stored beside that file; use
`--backup-dir PATH` to choose another directory. A relative backup directory is
also anchored beside each selected settings file.

```bash
ttr-aspect-lock restore --latest
ttr-aspect-lock restore --backup "/path/to/settings.json.ttr-aspect-lock.<timestamp>.bak"
ttr-aspect-lock uninstall --all --latest
```

Use `--dry-run` to preview. Always close TTR before restoring.

## Maintainer release and push checklist

For maintainers of `AlexmChadwick/ttr-16x9-aspect-lock`, work from a reviewed
clone with the intended `origin`; do not use these commands to change an
unknown remote. Confirm the version is consistent, run tests, and build the
release:

```bash
git remote -v
git status
python -m pip install -e ".[dev]"
pytest
./scripts/package_release.sh --dry-run
./scripts/package_release.sh
(cd dist && sha256sum -c "ttr-aspect-lock-$(tr -d '\n' < ../VERSION).zip.sha256")
```

After reviewing the archive and working tree, commit and push the intended
changes, then tag the same version and publish a GitHub release with both the
ZIP and its `.sha256` file:

```bash
git add README.md docs config.example.toml scripts src tests pyproject.toml VERSION
git commit -m "Release v$(tr -d '\n' < VERSION)"
git push origin main
git tag -a "v$(tr -d '\n' < VERSION)" -m "v$(tr -d '\n' < VERSION)"
git push origin "v$(tr -d '\n' < VERSION)"
```

Use the repository's actual default branch if it is not `main`, and verify the
release upload/checksum before announcing it.
