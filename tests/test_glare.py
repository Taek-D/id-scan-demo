from __future__ import annotations

import numpy as np

from app.steps.glare import detect_glare_mask, process_glare


def test_detect_glare_mask_on_white_image_is_full() -> None:
    image = np.ones((50, 50, 3), dtype=np.uint8) * 255
    mask = detect_glare_mask(image)

    assert np.all(mask == 255)


def test_detect_glare_mask_on_black_image_is_empty() -> None:
    image = np.zeros((50, 50, 3), dtype=np.uint8)
    mask = detect_glare_mask(image)

    assert np.all(mask == 0)


def test_process_glare_preserves_shape_and_dtype(glare_image: np.ndarray) -> None:
    result, mask = process_glare(glare_image)

    assert result.shape == glare_image.shape
    assert mask.shape == glare_image.shape[:2]
    assert result.dtype == np.uint8
