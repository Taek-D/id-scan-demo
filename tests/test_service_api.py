from __future__ import annotations

import cv2
import numpy as np
from fastapi.testclient import TestClient

from app.main import create_app


def test_service_pages_and_process_flow(tmp_path, synthetic_id_card) -> None:
    app = create_app(tmp_path / "service-data")
    client = TestClient(app)

    capture_page = client.get("/")
    admin_page = client.get("/admin")
    manifest = client.get("/manifest.webmanifest")
    service_worker = client.get("/sw.js")
    document_types = client.get("/api/document-types")

    success, encoded = cv2.imencode(".png", synthetic_id_card)
    assert success

    process_response = client.post(
        "/api/process?glare_threshold=245",
        data={"document_type": "resident_id"},
        files={"file": ("synthetic.png", encoded.tobytes(), "image/png")},
    )
    assert process_response.status_code == 200
    payload = process_response.json()

    submissions_response = client.get("/api/submissions")
    assert submissions_response.status_code == 200
    submissions = submissions_response.json()

    download_response = client.get(f"/api/submissions/{payload['submission_id']}/download?variant=final")

    assert capture_page.status_code == 200
    assert admin_page.status_code == 200
    assert 'rel="manifest"' in capture_page.text
    assert manifest.status_code == 200
    assert manifest.headers["content-type"].startswith("application/manifest+json")
    assert service_worker.status_code == 200
    assert "CACHE_NAME" in service_worker.text
    assert document_types.status_code == 200
    assert payload["document_type"] == "resident_id"
    assert "quality" in payload
    assert payload["quality"]["status"] in {"ready", "review_recommended", "retry_required"}
    assert submissions
    assert submissions[0]["id"] == payload["submission_id"]
    assert download_response.status_code == 200
    assert download_response.headers["content-type"].startswith("image/jpeg")


def test_service_process_keeps_safe_original_when_glare_removal_is_uncertain(tmp_path) -> None:
    app = create_app(tmp_path / "service-data")
    client = TestClient(app)

    wide_bright = np.full((240, 360, 3), 245, dtype=np.uint8)
    success, encoded = cv2.imencode(".png", wide_bright)
    assert success

    response = client.post(
        "/api/process?glare_threshold=200",
        data={"document_type": "resident_id"},
        files={"file": ("bright.png", encoded.tobytes(), "image/png")},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["after_glare_b64"] == payload["original_b64"]
