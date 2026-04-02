from __future__ import annotations

import cv2
import numpy as np


def find_id_card_contour(image: np.ndarray) -> np.ndarray | None:
    """Find the first large quadrilateral contour that resembles an ID card."""
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    edged = cv2.Canny(blurred, 50, 200)

    contours_info = cv2.findContours(edged, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    contours = contours_info[0] if len(contours_info) == 2 else contours_info[1]
    contours = sorted(contours, key=cv2.contourArea, reverse=True)[:10]

    for contour in contours:
        perimeter = cv2.arcLength(contour, True)
        approximation = cv2.approxPolyDP(contour, 0.02 * perimeter, True)
        if len(approximation) == 4:
            return approximation.reshape(4, 2).astype(np.float32)

    return None


def order_points(pts: np.ndarray) -> np.ndarray:
    """Order four points as top-left, top-right, bottom-right, bottom-left."""
    rect = np.zeros((4, 2), dtype=np.float32)

    sums = pts.sum(axis=1)
    rect[0] = pts[np.argmin(sums)]
    rect[2] = pts[np.argmax(sums)]

    diffs = pts[:, 1] - pts[:, 0]
    rect[1] = pts[np.argmin(diffs)]
    rect[3] = pts[np.argmax(diffs)]
    return rect


def crop_and_warp(image: np.ndarray, contour: np.ndarray) -> np.ndarray:
    """Apply a perspective transform based on a 4-point contour."""
    rect = order_points(contour.astype(np.float32))
    top_left, top_right, bottom_right, bottom_left = rect

    width_top = np.linalg.norm(top_right - top_left)
    width_bottom = np.linalg.norm(bottom_right - bottom_left)
    max_width = max(int(round((width_top + width_bottom) / 2.0)), 1)

    height_left = np.linalg.norm(bottom_left - top_left)
    height_right = np.linalg.norm(bottom_right - top_right)
    max_height = max(int(round((height_left + height_right) / 2.0)), 1)

    destination = np.array(
        [
            [0, 0],
            [max_width - 1, 0],
            [max_width - 1, max_height - 1],
            [0, max_height - 1],
        ],
        dtype=np.float32,
    )

    matrix = cv2.getPerspectiveTransform(rect, destination)
    return cv2.warpPerspective(image, matrix, (max_width, max_height))


def process_detect(image: np.ndarray) -> tuple[np.ndarray, bool]:
    """Detect and crop the ID-card region, or fall back to the original image."""
    contour = find_id_card_contour(image)
    if contour is None:
        return image, False

    cropped = crop_and_warp(image, contour)
    return cropped, True
