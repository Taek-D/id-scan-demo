from __future__ import annotations

import numpy as np

from app.steps.detect import crop_and_warp, find_id_card_contour, order_points, process_detect


def test_find_id_card_contour_on_synthetic_image(synthetic_id_card: np.ndarray) -> None:
    contour = find_id_card_contour(synthetic_id_card)

    assert contour is not None
    assert contour.shape == (4, 2)


def test_order_points_returns_expected_order() -> None:
    pts = np.array([[300, 100], [100, 300], [100, 100], [300, 300]], dtype=np.float32)
    ordered = order_points(pts)

    expected = np.array([[100, 100], [300, 100], [300, 300], [100, 300]], dtype=np.float32)
    np.testing.assert_allclose(ordered, expected)


def test_process_detect_falls_back_on_blank_image() -> None:
    image = np.zeros((100, 100, 3), dtype=np.uint8)

    result, detected = process_detect(image)

    assert detected is False
    np.testing.assert_array_equal(result, image)


def test_crop_and_warp_returns_non_empty_image(synthetic_id_card: np.ndarray) -> None:
    contour = find_id_card_contour(synthetic_id_card)
    assert contour is not None

    warped = crop_and_warp(synthetic_id_card, contour)

    assert warped.shape[0] > 0
    assert warped.shape[1] > 0
