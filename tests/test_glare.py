from __future__ import annotations

import numpy as np

from app.steps.glare import detect_glare_mask
from app.steps.glare import get_glare_application_decision
from app.steps.glare import process_glare
from app.steps.glare import remove_glare


def _gaussian_glare_image(height: int = 180, width: int = 240) -> np.ndarray:
    y_grid, x_grid = np.mgrid[0:height, 0:width]
    distance_sq = (x_grid - width // 2) ** 2 + (y_grid - height // 2) ** 2
    hotspot = 180.0 * np.exp(-distance_sq / (2 * 5.0**2))
    base = np.full((height, width, 3), 95, dtype=np.float32)
    image = np.clip(base + hotspot[..., None], 0, 255)
    return image.astype(np.uint8)


def test_detect_glare_mask_on_uniform_white_image_is_empty() -> None:
    image = np.ones((60, 60, 3), dtype=np.uint8) * 255
    mask = detect_glare_mask(image)

    assert np.count_nonzero(mask) == 0


def test_detect_glare_mask_limits_to_localized_hotspot() -> None:
    image = _gaussian_glare_image()
    mask = detect_glare_mask(image, threshold=200)
    ratio = float(np.count_nonzero(mask) / mask.size)

    assert np.count_nonzero(mask) > 0
    assert ratio < 0.02


def test_remove_glare_skips_large_mask_to_preserve_original() -> None:
    image = np.full((80, 120, 3), 127, dtype=np.uint8)
    mask = np.ones((80, 120), dtype=np.uint8) * 255

    should_apply, reason = get_glare_application_decision(mask)
    result = remove_glare(image, mask)

    assert not should_apply
    assert reason == "large_total_mask"
    assert np.array_equal(result, image)


def test_process_glare_preserves_shape_dtype_and_non_masked_pixels() -> None:
    image = _gaussian_glare_image()
    result, mask = process_glare(image, threshold=200)

    assert result.shape == image.shape
    assert mask.shape == image.shape[:2]
    assert result.dtype == np.uint8
    assert np.array_equal(result[mask == 0], image[mask == 0])
    assert not np.array_equal(result, image)


def test_process_glare_keeps_uniform_bright_frame_unchanged() -> None:
    image = np.ones((100, 140, 3), dtype=np.uint8) * 245
    result, mask = process_glare(image, threshold=200)

    assert np.count_nonzero(mask) == 0
    assert np.array_equal(result, image)
