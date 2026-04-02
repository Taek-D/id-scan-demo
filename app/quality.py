from __future__ import annotations

from dataclasses import asdict, dataclass

import cv2
import numpy as np

from app.steps.detect import order_points


@dataclass(frozen=True)
class CaptureQualityAssessment:
    status: str
    status_label: str
    summary: str
    user_messages: tuple[str, ...]
    admin_codes: tuple[str, ...]
    blur_score: float
    glare_ratio: float
    frame_fill_ratio: float
    tilt_angle: float | None

    def to_payload(self) -> dict[str, object]:
        return asdict(self)


def _compute_blur_score(image: np.ndarray) -> float:
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    return float(cv2.Laplacian(gray, cv2.CV_64F).var())


def _compute_tilt_angle(contour: np.ndarray | None) -> float | None:
    if contour is None:
        return None
    rect = order_points(contour.astype(np.float32))
    top_left, top_right = rect[0], rect[1]
    delta_x = float(top_right[0] - top_left[0])
    delta_y = float(top_right[1] - top_left[1])
    if delta_x == 0:
        return 90.0
    return float(np.degrees(np.arctan2(delta_y, delta_x)))


def assess_capture_quality(
    image: np.ndarray,
    glare_mask: np.ndarray,
    contour: np.ndarray | None,
) -> CaptureQualityAssessment:
    """Evaluate whether a capture is submission-ready or should be retaken."""
    blur_score = _compute_blur_score(image)
    glare_ratio = float(glare_mask.astype(bool).sum() / glare_mask.size)
    frame_fill_ratio = 0.0
    if contour is not None:
        frame_fill_ratio = float(cv2.contourArea(contour.astype(np.float32)) / (image.shape[0] * image.shape[1]))
    tilt_angle = _compute_tilt_angle(contour)

    codes: list[str] = []
    messages: list[str] = []

    if contour is None:
        codes.append("DOC_NOT_FOUND")
        messages.append("신분증 윤곽을 찾지 못했습니다. 프레임 중앙에 다시 맞춰 주세요.")
    else:
        if frame_fill_ratio < 0.18:
            codes.append("FRAME_TOO_SMALL")
            messages.append("신분증이 프레임 안에서 너무 작게 보입니다. 조금 더 가까이 촬영해 주세요.")
        if frame_fill_ratio > 0.92:
            codes.append("FRAME_TOO_CLOSE")
            messages.append("신분증이 화면에 너무 가깝습니다. 잘리지 않도록 거리를 조금 벌려 주세요.")
        if tilt_angle is not None and abs(tilt_angle) > 8:
            codes.append("HIGH_TILT")
            messages.append("기울기가 감지되었습니다. 수평 가이드에 맞춰 다시 촬영해 주세요.")

    if glare_ratio > 0.10:
        codes.append("HIGH_GLARE")
        messages.append("빛반사가 강합니다. 광원 방향을 피해서 각도를 조금 조정해 주세요.")
    elif glare_ratio > 0.05:
        codes.append("GLARE_NOTICE")
        messages.append("빛반사가 일부 감지되었습니다. 제출은 가능하지만 재촬영 시 더 선명해질 수 있습니다.")

    if blur_score < 60:
        codes.append("LOW_SHARPNESS")
        messages.append("초점이 흐립니다. 손 떨림을 줄이고 다시 촬영해 주세요.")

    retry_codes = {"DOC_NOT_FOUND", "FRAME_TOO_SMALL", "FRAME_TOO_CLOSE", "LOW_SHARPNESS"}
    review_codes = {"HIGH_GLARE", "HIGH_TILT", "GLARE_NOTICE"}

    if any(code in retry_codes for code in codes):
        status = "retry_required"
        status_label = "재촬영 필요"
        summary = "현재 품질로는 제출보다 재촬영을 권장합니다."
    elif any(code in review_codes for code in codes):
        status = "review_recommended"
        status_label = "주의 필요"
        summary = "제출은 가능하지만 일부 품질 이슈가 감지되었습니다."
    else:
        status = "ready"
        status_label = "제출 가능"
        summary = "촬영 품질이 양호합니다. 그대로 제출해도 됩니다."
        messages.append("신분증이 선명하게 감지되었습니다. 제출을 진행해 주세요.")

    return CaptureQualityAssessment(
        status=status,
        status_label=status_label,
        summary=summary,
        user_messages=tuple(messages),
        admin_codes=tuple(codes),
        blur_score=round(blur_score, 2),
        glare_ratio=round(glare_ratio, 4),
        frame_fill_ratio=round(frame_fill_ratio, 4),
        tilt_angle=round(float(tilt_angle), 2) if tilt_angle is not None else None,
    )
