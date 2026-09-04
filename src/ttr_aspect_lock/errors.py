"""Domain-specific errors for concise, user-actionable CLI failures."""


class AspectLockError(Exception):
    """Base error raised for an expected operation failure."""


class SettingsNotFoundError(AspectLockError):
    """No usable TTR settings file was found."""


class AmbiguousSettingsError(AspectLockError):
    """More than one settings file needs an explicit selection."""


class InvalidSettingsError(AspectLockError):
    """The selected settings file is not a JSON object."""


class BackupNotFoundError(AspectLockError):
    """A requested backup does not exist or cannot be identified."""
