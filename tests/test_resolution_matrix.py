"""Math checks for the documented, centered 16:9 resolution matrix.

These are pure display-geometry checks; actual bar rendering remains a manual,
in-game verification because it is controlled by the TTR client and GPU pipeline.
"""

from __future__ import annotations

import pytest

from ttr_aspect_lock.constants import TARGET_ASPECT_RATIO


def frame_for_display(width: int, height: int) -> tuple[float, float, float, float]:
    """Return centered 16:9 frame dimensions and each horizontal/vertical bar."""
    if width / height > TARGET_ASPECT_RATIO:
        frame_width = height * TARGET_ASPECT_RATIO
        return frame_width, float(height), (width - frame_width) / 2, 0.0
    frame_height = width / TARGET_ASPECT_RATIO
    return float(width), frame_height, 0.0, (height - frame_height) / 2


@pytest.mark.parametrize(
    ("width", "height", "frame", "side_bar", "top_bar"),
    [
        (1920, 1080, (1920, 1080), 0, 0),
        (1920, 1200, (1920, 1080), 0, 60),
        (3440, 1440, (2560, 1440), 440, 0),
        (5120, 1440, (2560, 1440), 1280, 0),
        (1600, 1200, (1600, 900), 0, 150),
    ],
)
def test_resolution_matrix_math(
    width: int, height: int, frame: tuple[int, int], side_bar: int, top_bar: int
) -> None:
    frame_width, frame_height, actual_side_bar, actual_top_bar = frame_for_display(width, height)

    assert (frame_width, frame_height) == pytest.approx(frame)
    assert actual_side_bar == pytest.approx(side_bar)
    assert actual_top_bar == pytest.approx(top_bar)
    assert frame_width / frame_height == pytest.approx(TARGET_ASPECT_RATIO)


def test_target_aspect_ratio_is_the_exact_python_sixteen_ninths_value() -> None:
    assert TARGET_ASPECT_RATIO == 16 / 9
