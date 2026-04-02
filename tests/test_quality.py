from __future__ import annotations

import cv2
import numpy as np

from app.quality import assess_capture_quality
from app.steps.detect import find_id_card_contour
from app.steps.glare import detect_glare_mask


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
