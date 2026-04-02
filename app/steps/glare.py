from __future__ import annotations

import cv2
import numpy as np


def _mask_statistics(mask: np.ndarray) -> tuple[float, float]:
    binary_mask = (mask > 0).astype(np.uint8)
    total_pixels = int(binary_mask.sum())
    if total_pixels == 0:
        return 0.0, 0.0

    _, _, stats, _ = cv2.connectedComponentsWithStats(binary_mask, connectivity=8)
    largest_blob_area = int(stats[1:, cv2.CC_STAT_AREA].max()) if len(stats) > 1 else 0
    image_area = float(mask.size)
    return total_pixels / image_area, largest_blob_area / image_area


def get_glare_application_decision(mask: np.ndarray) -> tuple[bool, str | None]:
    total_mask_ratio, largest_blob_ratio = _mask_statistics(mask)
    if total_mask_ratio == 0:
        return False, "empty_mask"
    if total_mask_ratio > 0.035:
        return False, "large_total_mask"
    if largest_blob_ratio > 0.015:
        return False, "large_component"
    return True, None


def detect_glare_mask(image: np.ndarray, threshold: int = 200) -> np.ndarray:
    """Create a conservative single-channel glare mask for specular highlights."""
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    saturation_channel = hsv[:, :, 1]
    value_channel = hsv[:, :, 2]

    blurred_value = cv2.GaussianBlur(value_channel, (21, 21), 0)
    local_contrast = cv2.subtract(value_channel, blurred_value)

    candidate_mask = (
        (value_channel >= threshold)
        & (saturation_channel <= 70)
        & (local_contrast >= 18)
    )
    mask = candidate_mask.astype(np.uint8) * 255

    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel, iterations=1)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=1)

    binary_mask = (mask > 0).astype(np.uint8)
    num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(binary_mask, connectivity=8)
    filtered_mask = np.zeros_like(mask)
    max_blob_area = int(image.shape[0] * image.shape[1] * 0.015)

    for label_index in range(1, num_labels):
        area = int(stats[label_index, cv2.CC_STAT_AREA])
        if 12 <= area <= max_blob_area:
            filtered_mask[labels == label_index] = 255

    return filtered_mask


def remove_glare(image: np.ndarray, mask: np.ndarray, inpaint_radius: int = 3) -> np.ndarray:
    """Restore only small, high-confidence glare regions and otherwise preserve the original."""
    should_apply, _ = get_glare_application_decision(mask)
    if not should_apply:
        return image.copy()
    return cv2.inpaint(image, mask, inpaint_radius, cv2.INPAINT_TELEA)


def process_glare(image: np.ndarray, threshold: int = 200) -> tuple[np.ndarray, np.ndarray]:
    """Run the glare detection and removal pipeline."""
    mask = detect_glare_mask(image, threshold)
    result = remove_glare(image, mask)
    return result, mask
