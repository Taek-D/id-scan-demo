from __future__ import annotations

from pydantic import BaseModel, Field


class QualityReport(BaseModel):
    status: str
    status_label: str
    summary: str
    user_messages: list[str]
    admin_codes: list[str]
    blur_score: float
    glare_ratio: float
    frame_fill_ratio: float
    tilt_angle: float | None


class SecurityPolicy(BaseModel):
    transport_encryption: str
    at_rest_encryption: str
    retention_policy: str
    access_scope: str


class DocumentTypeOption(BaseModel):
    key: str
    label: str
    aspect_ratio: float
    overlay_label: str
    capture_tips: list[str]


class NoticeResponse(BaseModel):
    title: str
    body: str
    updated_at: str


class SubmissionSummary(BaseModel):
    id: str
    created_at: str
    document_type: str
    original_filename: str
    capture_status: str
    capture_status_label: str
    capture_summary: str
    admin_codes: list[str]
    admin_status: str
    card_detected: bool
    blur_score: float
    glare_ratio: float
    frame_fill_ratio: float
    tilt_angle: float | None


class SubmissionDetail(SubmissionSummary):
    user_messages: list[str]
    downloads: dict[str, str]
    transmission_mode: str
    encryption_policy: str
    retention_policy: str


class ProcessResponse(BaseModel):
    submission_id: str
    document_type: str
    admin_status: str
    card_detected: bool = Field(description="Whether an ID-card-like contour was detected.")
    glare_pixel_ratio: float = Field(description="Ratio of glare pixels in the detected mask.")
    original_b64: str
    after_glare_b64: str
    after_detect_b64: str
    final_b64: str
    quality: QualityReport
    security: SecurityPolicy


class QASampleResult(BaseModel):
    filename: str
    document_type: str
    group_label: str
    expected_status: str
    card_detected: bool
    original_b64: str
    after_glare_b64: str
    after_detect_b64: str
    final_b64: str
    quality: QualityReport
