"""Safe installer and restorer for TTR's experimental aspect-ratio setting."""

from .constants import TARGET_ASPECT_RATIO
from .settings import apply_aspect_ratio, read_settings, restore_settings

__all__ = [
    "TARGET_ASPECT_RATIO",
    "apply_aspect_ratio",
    "read_settings",
    "restore_settings",
]

__version__ = "1.0.0"
