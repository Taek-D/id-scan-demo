from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np

from app.document_types import get_document_type_config
from app.steps.detect import find_id_card_contour
from app.steps.detect import process_detect
from app.steps.enhance import process_enhance
from app.steps.glare import process_glare


@dataclass
class PipelineResult:
    original: np.ndarray
    after_glare: np.ndarray
    after_detect: np.ndarray
    after_enhance: np.ndarray
    glare_mask: np.ndarray
    card_detected: bool
    card_contour: np.ndarray | None


def run_pipeline(
    image_bytes: bytes,
    glare_threshold: int = 200,
    document_type: str = "resident_id",
) -> PipelineResult:
    """Decode an image and run the full processing pipeline."""
    buffer = np.frombuffer(image_bytes, dtype=np.uint8)
    original = cv2.imdecode(buffer, cv2.IMREAD_COLOR)
    if original is None:
        raise ValueError("Unable to decode the uploaded image.")

    document_config = get_document_type_config(document_type)
    after_glare, glare_mask = process_glare(original, threshold=glare_threshold)
    card_contour = find_id_card_contour(after_glare)
    after_detect, card_detected = process_detect(
        after_glare,
        target_aspect_ratio=document_config.aspect_ratio,
    )
    after_enhance = process_enhance(after_detect)

    return PipelineResult(
        original=original,
        after_glare=after_glare,
        after_detect=after_detect,
        after_enhance=after_enhance,
        glare_mask=glare_mask,
        card_detected=card_detected,
        card_contour=card_contour,
    )


def ndarray_to_jpeg_bytes(image: np.ndarray, quality: int = 90) -> bytes:
    """Encode a BGR image to JPEG bytes."""
    success, encoded = cv2.imencode(
        ".jpg",
        image,
        [int(cv2.IMWRITE_JPEG_QUALITY), quality],
    )
    if not success:
        raise ValueError("Unable to encode image as JPEG.")

    return encoded.tobytes()
