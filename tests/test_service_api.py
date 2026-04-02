from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
from fastapi.testclient import TestClient

from app.main import create_app


def test_service_pages_and_process_flow(tmp_path, synthetic_id_card) -> None:
    app = create_app(tmp_path / "service-data")
    client = TestClient(app)

    capture_page = client.get("/")
    admin_page = client.get("/admin")
    qa_page = client.get("/qa")
    manifest = client.get("/manifest.webmanifest")
    service_worker = client.get("/sw.js")
    document_types = client.get("/api/document-types")
    qa_samples = client.get("/api/qa/samples")

    success, encoded = cv2.imencode(".png", synthetic_id_card)
    assert success

    process_response = client.post(
        "/api/process",
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
    assert qa_page.status_code == 200
    assert 'id="status-filter"' in admin_page.text
    assert 'id="document-filter"' in admin_page.text
    assert 'id="qa-gallery"' in qa_page.text
    assert 'rel="manifest"' in capture_page.text
    assert manifest.status_code == 200
    assert manifest.headers["content-type"].startswith("application/manifest+json")
    assert manifest.headers["cache-control"] == "no-cache"
    assert service_worker.status_code == 200
    assert service_worker.headers["cache-control"] == "no-cache"
    assert "CACHE_NAME" in service_worker.text
    assert document_types.status_code == 200
    assert qa_samples.status_code == 200
    qa_payload = qa_samples.json()
    assert len(qa_payload) == 10
    assert qa_payload[0]["original_b64"]
    assert qa_payload[0]["after_glare_b64"]
    assert qa_payload[0]["after_detect_b64"]
    assert qa_payload[0]["final_b64"]
    assert qa_payload[0]["quality"]["status"] in {"ready", "review_recommended", "retry_required"}
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


def test_service_process_accepts_glare_threshold_override(tmp_path, synthetic_id_card) -> None:
    app = create_app(tmp_path / "service-data")
    client = TestClient(app)

    success, encoded = cv2.imencode(".png", synthetic_id_card)
    assert success

    response = client.post(
        "/api/process?glare_threshold=200",
        data={"document_type": "resident_id"},
        files={"file": ("synthetic.png", encoded.tobytes(), "image/png")},
    )

    assert response.status_code == 200
    payload = response.json()
    assert "quality" in payload


def test_service_process_detects_passport_mock_and_marks_ready(tmp_path) -> None:
    app = create_app(tmp_path / "service-data")
    client = TestClient(app)

    sample_path = Path(__file__).resolve().parents[1] / "samples" / "passport_mock_clean.png"
    with sample_path.open("rb") as sample_file:
        response = client.post(
            "/api/process",
            data={"document_type": "passport"},
            files={"file": (sample_path.name, sample_file.read(), "image/png")},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["card_detected"] is True
    assert payload["quality"]["status"] == "ready"


def test_service_process_marks_frame_cut_sample_for_retry(tmp_path) -> None:
    app = create_app(tmp_path / "service-data")
    client = TestClient(app)

    sample_path = Path(__file__).resolve().parents[1] / "samples" / "failure_frame_cut.png"
    with sample_path.open("rb") as sample_file:
        response = client.post(
            "/api/process",
            data={"document_type": "passport"},
            files={"file": (sample_path.name, sample_file.read(), "image/png")},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["card_detected"] is True
    assert payload["quality"]["status"] == "retry_required"
    assert "FRAME_CLIPPED" in payload["quality"]["admin_codes"]


def test_service_process_marks_heavy_glare_sample_for_retry(tmp_path) -> None:
    app = create_app(tmp_path / "service-data")
    client = TestClient(app)

    sample_path = Path(__file__).resolve().parents[1] / "samples" / "failure_glare_heavy.png"
    with sample_path.open("rb") as sample_file:
        response = client.post(
            "/api/process",
            data={"document_type": "resident_id"},
            files={"file": (sample_path.name, sample_file.read(), "image/png")},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["card_detected"] is True
    assert payload["quality"]["status"] == "retry_required"
    assert "HIGH_GLARE_RETRY" in payload["quality"]["admin_codes"]


def test_service_qa_samples_include_expected_regressions(tmp_path) -> None:
    app = create_app(tmp_path / "service-data")
    client = TestClient(app)

    response = client.get("/api/qa/samples")

    assert response.status_code == 200
    payload = response.json()
    by_name = {item["filename"]: item for item in payload}

    assert by_name["resident_mock_clean.png"]["quality"]["status"] == "ready"
    assert by_name["passport_mock_clean.png"]["quality"]["status"] == "ready"
    assert by_name["failure_frame_cut.png"]["quality"]["status"] == "retry_required"
    assert "FRAME_CLIPPED" in by_name["failure_frame_cut.png"]["quality"]["admin_codes"]
    assert by_name["failure_glare_heavy.png"]["quality"]["status"] == "retry_required"
    assert "HIGH_GLARE_RETRY" in by_name["failure_glare_heavy.png"]["quality"]["admin_codes"]
