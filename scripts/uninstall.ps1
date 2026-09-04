[CmdletBinding()]
param(
    # One or more existing settings.json files. Omit to use discovery.
    [Alias("SettingsPath")]
    [string[]]$Settings,

    # Optional portable TOML configuration file.
    [string]$Config,

    # Restore an explicit backup. Omit to restore the newest matching backup.
    [string]$Backup,

    # Directory containing backups when using the latest matching backup.
    [string]$BackupDir,

    # Restore every discovered/configured settings file.
    [switch]$All,

    # Show the intended restore without changing settings.json.
    [switch]$DryRun,

    # Include selection and backup details in the tool output.
    [switch]$VerboseOutput,

    # Emit the tool's machine-readable JSON output.
    [switch]$Json
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

function Resolve-Python {
    $launchers = @(
        [pscustomobject]@{ Name = 'py'; Arguments = @('-3') },
        [pscustomobject]@{ Name = 'python'; Arguments = @() },
        [pscustomobject]@{ Name = 'python3'; Arguments = @() }
    )

    foreach ($launcher in $launchers) {
        $command = Get-Command $launcher.Name -CommandType Application -ErrorAction SilentlyContinue
        if ($null -eq $command) {
            continue
        }

        & $command.Source @($launcher.Arguments) -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)'
        if ($LASTEXITCODE -eq 0) {
            return [pscustomobject]@{ Path = $command.Source; Arguments = @($launcher.Arguments) }
        }
    }

    throw 'Python 3.11 or newer was not found. Install it, then rerun this script.'
}

$repositoryRoot = Split-Path -Parent $PSScriptRoot
$sourceDirectory = Join-Path $repositoryRoot 'src'
if (-not (Test-Path -LiteralPath (Join-Path $sourceDirectory 'ttr_aspect_lock'))) {
    throw "The local package was not found under $sourceDirectory. Extract the complete release ZIP and run this script from it."
}
if ($Backup -and $All) {
    throw 'Use either -Backup for one settings file or -All with the latest matching backup, not both.'
}

$python = Resolve-Python
$arguments = @('-m', 'ttr_aspect_lock')
if ($Config) {
    $arguments += @('--config', $Config)
}
foreach ($path in $Settings) {
    $arguments += @('--settings', $path)
}
if ($VerboseOutput) {
    $arguments += '--verbose'
}
if ($Json) {
    $arguments += '--json'
}
$arguments += 'restore'
if ($Backup) {
    $arguments += @('--backup', $Backup)
}
else {
    $arguments += '--latest'
}
if ($All) {
    $arguments += '--all'
}
if ($BackupDir) {
    $arguments += @('--backup-dir', $BackupDir)
}
if ($DryRun) {
    $arguments += '--dry-run'
}

# The source path is scoped to this child process; nothing is installed globally.
$priorPythonPath = $env:PYTHONPATH
try {
    $env:PYTHONPATH = if ($priorPythonPath) { "$sourceDirectory$([IO.Path]::PathSeparator)$priorPythonPath" } else { $sourceDirectory }
    & $python.Path @($python.Arguments) @arguments
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }
}
finally {
    $env:PYTHONPATH = $priorPythonPath
}
