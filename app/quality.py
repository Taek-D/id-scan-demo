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


@dataclass(frozen=True)
class _GlareSeverity:
    highlight_ratio: float
    largest_highlight_ratio: float
    center_band_ratio: float
    smooth_center_ratio: float
    smooth_top_ratio: float


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


def _is_frame_clipped(image: np.ndarray, contour: np.ndarray | None) -> bool:
    if contour is None:
        return False

    image_height, image_width = image.shape[:2]
    clip_margin_x = image_width * 0.04
    clip_margin_y = image_height * 0.04
    x, y, width, height = cv2.boundingRect(contour.astype(np.int32))

    return (
        x <= clip_margin_x
        or y <= clip_margin_y
        or x + width >= image_width - clip_margin_x
        or y + height >= image_height - clip_margin_y
    )


def _extract_document_roi(image: np.ndarray, contour: np.ndarray | None) -> np.ndarray | None:
    if contour is None:
        return None

    x, y, width, height = cv2.boundingRect(contour.astype(np.int32))
    crop = image[y : y + height, x : x + width]
    if crop.size == 0:
        return None

    margin_x = max(1, int(round(width * 0.08)))
    margin_y = max(1, int(round(height * 0.08)))

    if width <= margin_x * 2 or height <= margin_y * 2:
        return crop

    roi = crop[margin_y : height - margin_y, margin_x : width - margin_x]
    return roi if roi.size else crop


def _connected_component_ratios(mask: np.ndarray) -> tuple[float, float]:
    if mask.size == 0:
        return 0.0, 0.0

    num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(mask, connectivity=8)
    filtered = np.zeros_like(mask, dtype=np.uint8)
    largest_area = 0
    total_area = 0

    for index in range(1, num_labels):
        area = int(stats[index, cv2.CC_STAT_AREA])
        if area < 12:
            continue
        filtered[labels == index] = 1
        total_area += area
        largest_area = max(largest_area, area)

    area = float(mask.shape[0] * mask.shape[1])
    if area == 0:
        return 0.0, 0.0

    return total_area / area, largest_area / area


def _compute_glare_severity(image: np.ndarray, contour: np.ndarray | None) -> _GlareSeverity:
    roi = _extract_document_roi(image, contour)
    if roi is None:
        return _GlareSeverity(0.0, 0.0, 0.0, 0.0, 0.0)

    hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
    saturation = hsv[:, :, 1].astype(np.float32)
    value = hsv[:, :, 2].astype(np.float32)
    local_baseline = cv2.GaussianBlur(value, (21, 21), 0)
    local_contrast = value - local_baseline

    highlight_candidates = (
        (value >= 245)
        & (saturation <= 110)
        & (local_contrast >= 12)
    ).astype(np.uint8)
    highlight_ratio, largest_highlight_ratio = _connected_component_ratios(highlight_candidates)

    roi_height, roi_width = roi.shape[:2]
    center_top = int(roi_height * 0.225)
    center_bottom = int(roi_height * 0.775)
    center_left = int(roi_width * 0.2)
    center_right = int(roi_width * 0.8)
    center_band = highlight_candidates[center_top:center_bottom, center_left:center_right]
    center_band_ratio = float(center_band.mean()) if center_band.size else 0.0

    # Broad bloom highlights have low texture and wash out document content.
    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    laplacian = cv2.Laplacian(gray, cv2.CV_32F)
    smooth_bloom = (
        (value >= 252)
        & (saturation <= 90)
        & (np.abs(laplacian) <= 4)
    ).astype(np.uint8)

    smooth_center = smooth_bloom[center_top:center_bottom, center_left:center_right]
    smooth_top = smooth_bloom[
        int(roi_height * 0.08) : int(roi_height * 0.35),
        int(roi_width * 0.12) : int(roi_width * 0.88),
    ]

    return _GlareSeverity(
        highlight_ratio=highlight_ratio,
        largest_highlight_ratio=largest_highlight_ratio,
        center_band_ratio=center_band_ratio,
        smooth_center_ratio=float(smooth_center.mean()) if smooth_center.size else 0.0,
        smooth_top_ratio=float(smooth_top.mean()) if smooth_top.size else 0.0,
    )


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
        frame_fill_ratio = float(
            cv2.contourArea(contour.astype(np.float32)) / (image.shape[0] * image.shape[1])
        )
    tilt_angle = _compute_tilt_angle(contour)
    frame_clipped = _is_frame_clipped(image, contour)
    glare_severity = _compute_glare_severity(image, contour)

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
            messages.append("신분증이 화면에 너무 가깝습니다. 가장리가 잘리지 않도록 거리를 조금 벌려 주세요.")
        if frame_clipped:
            codes.append("FRAME_CLIPPED")
            messages.append("신분증 가장자리가 화면 경계에 너무 가깝습니다. 프레임 안으로 다시 맞춰 주세요.")
        if tilt_angle is not None and abs(tilt_angle) > 8:
            codes.append("HIGH_TILT")
            messages.append("기울기가 감지되었습니다. 수평을 맞춘 뒤 다시 촬영해 주세요.")

    if (
        glare_severity.smooth_center_ratio >= 0.15
        and glare_severity.smooth_top_ratio >= 0.103
    ):
        codes.append("HIGH_GLARE_RETRY")
        messages.append("빛반사가 본문을 가리고 있습니다. 조명 방향을 바꾸고 다시 촬영해 주세요.")
    elif (
        glare_severity.smooth_center_ratio >= 0.10
        and glare_severity.smooth_top_ratio >= 0.06
    ):
        codes.append("HIGH_GLARE")
        messages.append(
            "약한 반사광이 본문에 감지되었습니다. 제출은 가능하지만 재촬영 시 더 선명해질 수 있습니다."
        )
    elif glare_ratio > 0.10:
        codes.append("HIGH_GLARE")
        messages.append("빛반사가 강합니다. 광원 방향을 피해 각도를 조금 조정해 주세요.")
    elif glare_ratio > 0.05:
        codes.append("GLARE_NOTICE")
        messages.append("약한 빛반사가 감지되었습니다. 제출은 가능하지만 재촬영 시 더 선명해질 수 있습니다.")

    if blur_score < 60:
        codes.append("LOW_SHARPNESS")
        messages.append("초점이 흐립니다. 흔들림을 줄이고 다시 촬영해 주세요.")

    retry_codes = {
        "DOC_NOT_FOUND",
        "FRAME_TOO_SMALL",
        "FRAME_TOO_CLOSE",
        "FRAME_CLIPPED",
        "LOW_SHARPNESS",
        "HIGH_GLARE_RETRY",
    }
    review_codes = {"HIGH_GLARE", "HIGH_TILT", "GLARE_NOTICE"}

    if any(code in retry_codes for code in codes):
        status = "retry_required"
        status_label = "재촬영 필요"
        summary = "현재 상태로는 제출보다 재촬영을 권장합니다."
    elif any(code in review_codes for code in codes):
        status = "review_recommended"
        status_label = "주의 필요"
        summary = "제출은 가능하지만 일부 품질 이슈가 감지되었습니다."
    else:
        status = "ready"
        status_label = "제출 가능"
        summary = "촬영 품질이 양호합니다. 그대로 제출해도 좋습니다."
        messages.append("문서 윤곽과 텍스트 영역이 안정적으로 감지되었습니다. 제출을 진행해 주세요.")

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
