from __future__ import annotations

import cv2
import numpy as np
import pytest


@pytest.fixture
def synthetic_id_card() -> np.ndarray:
    """Synthetic ID-card image on a brighter background."""
    img = np.ones((540, 856, 3), dtype=np.uint8) * 220
    cv2.rectangle(img, (50, 50), (806, 490), (100, 100, 100), -1)
    cv2.putText(
        img,
        "SAMPLE ID CARD",
        (100, 200),
        cv2.FONT_HERSHEY_SIMPLEX,
        2,
        (255, 255, 255),
        3,
    )
    return img


@pytest.fixture
def glare_image() -> np.ndarray:
    """Synthetic image with a bright glare spot in the center."""
    img = np.ones((540, 856, 3), dtype=np.uint8) * 100
    cv2.circle(img, (428, 270), 80, (255, 255, 255), -1)
    return img
