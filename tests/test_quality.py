from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np

from app.quality import assess_capture_quality
from app.steps.detect import find_id_card_contour
from app.steps.glare import detect_glare_mask


def _load_sample_image(name: str) -> np.ndarray:
    path = Path(__file__).resolve().parents[1] / "samples" / name
    image = cv2.imdecode(np.frombuffer(path.read_bytes(), dtype=np.uint8), cv2.IMREAD_COLOR)
    assert image is not None
    return image


def test_quality_assessment_marks_good_capture_ready(synthetic_id_card: np.ndarray) -> None:
    mask = detect_glare_mask(synthetic_id_card, threshold=245)
    contour = find_id_card_contour(synthetic_id_card)

    assessment = assess_capture_quality(synthetic_id_card, mask, contour)

    assert assessment.status == "ready"
    assert assessment.glare_ratio < 0.05


def test_quality_assessment_marks_blurry_capture_for_retry(synthetic_id_card: np.ndarray) -> None:
    blurry = cv2.GaussianBlur(synthetic_id_card, (31, 31), 0)
    mask = np.zeros(blurry.shape[:2], dtype=np.uint8)
    contour = find_id_card_contour(blurry)

    assessment = assess_capture_quality(blurry, mask, contour)

    assert assessment.status == "retry_required"
    assert "LOW_SHARPNESS" in assessment.admin_codes


def test_quality_assessment_marks_mock_resident_ready() -> None:
    image = _load_sample_image("resident_mock_clean.png")
    mask = detect_glare_mask(image, threshold=245)
    contour = find_id_card_contour(image, target_aspect_ratio=85.6 / 54.0)

    assessment = assess_capture_quality(image, mask, contour)

    assert assessment.status == "ready"
    assert "FRAME_TOO_SMALL" not in assessment.admin_codes


def test_quality_assessment_marks_frame_cut_for_retry() -> None:
    image = _load_sample_image("failure_frame_cut.png")
    mask = detect_glare_mask(image, threshold=245)
    contour = find_id_card_contour(image, target_aspect_ratio=125.0 / 88.0)

    assessment = assess_capture_quality(image, mask, contour)

    assert assessment.status == "retry_required"
    assert "FRAME_CLIPPED" in assessment.admin_codes


def test_quality_assessment_marks_heavy_glare_for_retry() -> None:
    image = _load_sample_image("failure_glare_heavy.png")
    mask = detect_glare_mask(image, threshold=245)
    contour = find_id_card_contour(image, target_aspect_ratio=85.6 / 54.0)

    assessment = assess_capture_quality(image, mask, contour)

    assert assessment.status == "retry_required"
    assert "HIGH_GLARE_RETRY" in assessment.admin_codes


def test_quality_assessment_keeps_resident_glare_out_of_retry() -> None:
    image = _load_sample_image("resident_mock_glare.png")
    mask = detect_glare_mask(image, threshold=245)
    contour = find_id_card_contour(image, target_aspect_ratio=85.6 / 54.0)

    assessment = assess_capture_quality(image, mask, contour)

    assert assessment.status in {"ready", "review_recommended"}
    assert "HIGH_GLARE_RETRY" not in assessment.admin_codes
