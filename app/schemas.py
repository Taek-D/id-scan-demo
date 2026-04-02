from __future__ import annotations

from pydantic import BaseModel, Field


class ProcessResponse(BaseModel):
    card_detected: bool = Field(description="Whether an ID-card-like contour was detected.")
    glare_pixel_ratio: float = Field(description="Ratio of glare pixels in the detected mask.")
    original_b64: str
    after_glare_b64: str
    after_detect_b64: str
    final_b64: str
