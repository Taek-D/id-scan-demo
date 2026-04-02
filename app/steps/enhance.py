from __future__ import annotations

import cv2
import numpy as np


def apply_clahe(
    image: np.ndarray,
    clip_limit: float = 2.0,
    tile_grid: tuple[int, int] = (8, 8),
) -> np.ndarray:
    """Improve local contrast on the LAB L channel only."""
    lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
    l_channel, a_channel, b_channel = cv2.split(lab)

    clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=tile_grid)
    enhanced_l = clahe.apply(l_channel)

    merged = cv2.merge((enhanced_l, a_channel, b_channel))
    return cv2.cvtColor(merged, cv2.COLOR_LAB2BGR)


def apply_unsharp_mask(
    image: np.ndarray,
    kernel_size: int = 5,
    sigma: float = 1.0,
    amount: float = 1.5,
) -> np.ndarray:
    """Sharpen edges with a weighted subtraction from a blurred image."""
    blurred = cv2.GaussianBlur(image, (kernel_size, kernel_size), sigma)
    return cv2.addWeighted(image, 1.0 + amount, blurred, -amount, 0)


def process_enhance(image: np.ndarray) -> np.ndarray:
    """Run CLAHE followed by unsharp masking."""
    result = apply_clahe(image)
    return apply_unsharp_mask(result)
