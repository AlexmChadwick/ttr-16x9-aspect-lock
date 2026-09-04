"""Project constants kept separate to make the supported setting explicit."""

from __future__ import annotations

APP_NAME = "ttr-aspect-lock"
SETTINGS_FILENAME = "settings.json"
VIDEO_KEY = "video"
ASPECT_RATIO_KEY = "forced-aspect-ratio"
# Retain the exact 16:9 decimal used by the project instead of rounding it to 1.78.
TARGET_ASPECT_RATIO = 1.7777777777777777
BACKUP_MARKER = ".ttr-aspect-lock."
