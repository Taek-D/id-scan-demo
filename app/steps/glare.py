from __future__ import annotations

import cv2
import numpy as np


def detect_glare_mask(image: np.ndarray, threshold: int = 200) -> np.ndarray:
    """Create a single-channel glare mask from the HSV V channel."""
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    value_channel = hsv[:, :, 2]
    _, mask = cv2.threshold(value_channel, threshold, 255, cv2.THRESH_BINARY)

    kernel = np.ones((5, 5), dtype=np.uint8)
    mask = cv2.dilate(mask, kernel, iterations=2)
    return mask


def remove_glare(image: np.ndarray, mask: np.ndarray, inpaint_radius: int = 7) -> np.ndarray:
    """Restore glare regions with Navier-Stokes inpainting."""
    return cv2.inpaint(image, mask, inpaint_radius, cv2.INPAINT_NS)


def process_glare(image: np.ndarray, threshold: int = 200) -> tuple[np.ndarray, np.ndarray]:
    """Run the glare detection and removal pipeline."""
    mask = detect_glare_mask(image, threshold)
    result = remove_glare(image, mask)
    return result, mask
