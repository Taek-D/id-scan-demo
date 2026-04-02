from __future__ import annotations

import cv2
import numpy as np

from app.steps.enhance import apply_clahe, apply_unsharp_mask


def test_apply_clahe_preserves_shape_and_dtype(synthetic_id_card: np.ndarray) -> None:
    result = apply_clahe(synthetic_id_card)

    assert result.shape == synthetic_id_card.shape
    assert result.dtype == np.uint8


def test_apply_unsharp_mask_stays_in_valid_uint8_range(synthetic_id_card: np.ndarray) -> None:
    result = apply_unsharp_mask(synthetic_id_card)

    assert result.dtype == np.uint8
    assert int(result.min()) >= 0
    assert int(result.max()) <= 255


def test_apply_clahe_increases_variance_on_low_contrast_image() -> None:
    base = np.tile(np.linspace(120, 136, 128, dtype=np.uint8), (128, 1))
    low_contrast = cv2.merge((base, base, base))

    result = apply_clahe(low_contrast)

    assert float(result.var()) > float(low_contrast.var())
