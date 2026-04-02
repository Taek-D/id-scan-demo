from __future__ import annotations

import base64
import mimetypes
import os
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, Query, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.document_types import get_document_type_config, list_document_type_payloads
from app.pipeline import ndarray_to_jpeg_bytes, run_pipeline
from app.quality import assess_capture_quality
from app.schemas import (
    DocumentTypeOption,
    NoticeResponse,
    ProcessResponse,
    QASampleResult,
    QualityReport,
    SecurityPolicy,
    SubmissionDetail,
    SubmissionSummary,
)
from app.storage import SubmissionStore

MAX_UPLOAD_SIZE = 10 * 1024 * 1024
ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png"}
BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
SAMPLES_DIR = BASE_DIR.parent / "samples"
QA_SAMPLE_SET = (
    {
        "filename": "resident_mock_clean.png",
        "document_type": "resident_id",
        "expected_status": "ready",
        "group_label": "정상 샘플",
    },
    {
        "filename": "resident_mock_glare.png",
        "document_type": "resident_id",
        "expected_status": "review_recommended",
        "group_label": "경계 샘플",
    },
    {
        "filename": "resident_mock_shadow.png",
        "document_type": "resident_id",
        "expected_status": "ready",
        "group_label": "정상 샘플",
    },
    {
        "filename": "passport_mock_clean.png",
        "document_type": "passport",
        "expected_status": "ready",
        "group_label": "정상 샘플",
    },
    {
        "filename": "passport_mock_glare.png",
        "document_type": "passport",
        "expected_status": "review_recommended",
        "group_label": "경계 샘플",
    },
    {
        "filename": "passport_mock_motion.png",
        "document_type": "passport",
        "expected_status": "retry_required",
        "group_label": "실패 샘플",
    },
    {
        "filename": "failure_blur.png",
        "document_type": "resident_id",
        "expected_status": "retry_required",
        "group_label": "실패 샘플",
    },
    {
        "filename": "failure_frame_cut.png",
        "document_type": "passport",
        "expected_status": "retry_required",
        "group_label": "실패 샘플",
    },
    {
        "filename": "failure_glare_heavy.png",
        "document_type": "resident_id",
        "expected_status": "retry_required",
        "group_label": "실패 샘플",
    },
    {
        "filename": "failure_tilted.png",
        "document_type": "resident_id",
        "expected_status": "review_recommended",
        "group_label": "경계 샘플",
    },
)


def _to_base64(image_bytes: bytes) -> str:
    return base64.b64encode(image_bytes).decode("utf-8")


def _security_policy() -> SecurityPolicy:
    return SecurityPolicy(
        transport_encryption="TLS 1.2+ required on deployment",
        at_rest_encryption="AES-256 encrypted object storage policy",
        retention_policy="30-day demo retention with scheduled purge assumption",
        access_scope="Admin-only access to stored images and download actions",
    )


def _build_qa_sample(sample: dict[str, str]) -> QASampleResult:
    image_path = SAMPLES_DIR / sample["filename"]
    image_bytes = image_path.read_bytes()
    result = run_pipeline(
        image_bytes,
        glare_threshold=245,
        document_type=sample["document_type"],
    )
    quality = assess_capture_quality(result.original, result.glare_mask, result.card_contour)
    quality_payload = quality.to_payload()

    return QASampleResult(
        filename=sample["filename"],
        document_type=sample["document_type"],
        group_label=sample["group_label"],
        expected_status=sample["expected_status"],
        card_detected=result.card_detected,
        original_b64=_to_base64(ndarray_to_jpeg_bytes(result.original)),
        after_glare_b64=_to_base64(ndarray_to_jpeg_bytes(result.after_glare)),
        after_detect_b64=_to_base64(ndarray_to_jpeg_bytes(result.after_detect)),
        final_b64=_to_base64(ndarray_to_jpeg_bytes(result.after_enhance)),
        quality=QualityReport(**quality_payload),
    )


def _process_upload(
    app: FastAPI,
    *,
    original_filename: str,
    image_bytes: bytes,
    document_type: str,
    glare_threshold: int,
) -> ProcessResponse:
    try:
        get_document_type_config(document_type)
    except KeyError as exc:
        raise HTTPException(status_code=400, detail="Unsupported document type.") from exc

    try:
        result = run_pipeline(
            image_bytes,
            glare_threshold=glare_threshold,
            document_type=document_type,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    quality = assess_capture_quality(result.original, result.glare_mask, result.card_contour)
    quality_payload = quality.to_payload()

    original_jpeg_bytes = ndarray_to_jpeg_bytes(result.original)
    glare_jpeg_bytes = ndarray_to_jpeg_bytes(result.after_glare)
    detect_jpeg_bytes = ndarray_to_jpeg_bytes(result.after_detect)
    final_jpeg_bytes = ndarray_to_jpeg_bytes(result.after_enhance)

    record = app.state.submission_store.create_submission(
        document_type=document_type,
        original_filename=original_filename,
        quality=quality_payload,
        card_detected=result.card_detected,
        original_bytes=image_bytes,
        glare_bytes=glare_jpeg_bytes,
        detect_bytes=detect_jpeg_bytes,
        final_bytes=final_jpeg_bytes,
    )

    return ProcessResponse(
        submission_id=str(record["id"]),
        document_type=document_type,
        admin_status=str(record["admin_status"]),
        card_detected=result.card_detected,
        glare_pixel_ratio=float(quality_payload["glare_ratio"]),
        original_b64=_to_base64(original_jpeg_bytes),
        after_glare_b64=_to_base64(glare_jpeg_bytes),
        after_detect_b64=_to_base64(detect_jpeg_bytes),
        final_b64=_to_base64(final_jpeg_bytes),
        quality=QualityReport(**quality_payload),
        security=_security_policy(),
    )


def create_app(data_dir: Path | None = None) -> FastAPI:
    app = FastAPI(title="ID Scan Demo Service", version="2.0.0")
    templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
    store = SubmissionStore(data_dir or Path(os.environ.get("ID_SCAN_DATA_DIR", "data")))
    store.initialize()

    app.state.templates = templates
    app.state.submission_store = store
    app.state.streamlit_url = "http://127.0.0.1:8501"

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

    @app.get("/manifest.webmanifest")
    async def manifest() -> FileResponse:
        return FileResponse(
            STATIC_DIR / "manifest.webmanifest",
            media_type="application/manifest+json",
            filename="manifest.webmanifest",
            headers={"Cache-Control": "no-cache"},
        )

    @app.get("/sw.js")
    async def service_worker() -> FileResponse:
        return FileResponse(
            STATIC_DIR / "sw.js",
            media_type="application/javascript",
            filename="sw.js",
            headers={"Cache-Control": "no-cache"},
        )

    @app.get("/", response_class=HTMLResponse)
    async def capture_page(request: Request) -> HTMLResponse:
        return templates.TemplateResponse(
            request=request,
            name="capture.html",
            context={
                "streamlit_url": app.state.streamlit_url,
            },
        )

    @app.get("/admin", response_class=HTMLResponse)
    async def admin_page(request: Request) -> HTMLResponse:
        return templates.TemplateResponse(
            request=request,
            name="admin.html",
            context={
                "streamlit_url": app.state.streamlit_url,
            },
        )

    @app.get("/qa", response_class=HTMLResponse)
    async def qa_page(request: Request) -> HTMLResponse:
        return templates.TemplateResponse(
            request=request,
            name="qa.html",
            context={
                "streamlit_url": app.state.streamlit_url,
            },
        )

    @app.get("/api/health")
    async def healthcheck() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/api/document-types", response_model=list[DocumentTypeOption])
    async def document_types() -> list[DocumentTypeOption]:
        return [DocumentTypeOption(**payload) for payload in list_document_type_payloads()]

    @app.get("/api/security", response_model=SecurityPolicy)
    async def security_policy() -> SecurityPolicy:
        return _security_policy()

    @app.get("/api/notices", response_model=NoticeResponse)
    async def notices() -> NoticeResponse:
        return NoticeResponse(**app.state.submission_store.get_notice())

    @app.get("/api/submissions", response_model=list[SubmissionSummary])
    async def submissions() -> list[SubmissionSummary]:
        return [SubmissionSummary(**record) for record in app.state.submission_store.list_submissions()]

    @app.get("/api/qa/samples", response_model=list[QASampleResult])
    async def qa_samples() -> list[QASampleResult]:
        return [_build_qa_sample(sample) for sample in QA_SAMPLE_SET]

    @app.get("/api/submissions/{submission_id}", response_model=SubmissionDetail)
    async def submission_detail(submission_id: str) -> SubmissionDetail:
        record = app.state.submission_store.get_submission(submission_id)
        if record is None:
            raise HTTPException(status_code=404, detail="Submission not found.")
        return SubmissionDetail(**record)

    @app.get("/api/submissions/{submission_id}/download")
    async def submission_download(
        submission_id: str,
        variant: str = Query(default="final"),
    ) -> FileResponse:
        variant_mapping = {"original", "glare", "detect", "final"}
        if variant not in variant_mapping:
            raise HTTPException(status_code=400, detail="Unsupported download variant.")

        file_path = app.state.submission_store.get_file_path(submission_id, variant)
        if file_path is None or not file_path.exists():
            raise HTTPException(status_code=404, detail="File not found.")

        media_type = mimetypes.guess_type(file_path.name)[0] or "application/octet-stream"
        return FileResponse(
            path=file_path,
            media_type=media_type,
            filename=file_path.name,
        )

    @app.post("/process", response_model=ProcessResponse)
    @app.post("/api/process", response_model=ProcessResponse)
    async def process_image(
        file: UploadFile = File(...),
        glare_threshold: int = Query(default=245, ge=100, le=254),
        document_type: str = Form(default="resident_id"),
    ) -> ProcessResponse:
        if file.content_type not in ALLOWED_CONTENT_TYPES:
            raise HTTPException(status_code=400, detail="Only JPEG and PNG images are supported.")

        image_bytes = await file.read()
        if not image_bytes:
            raise HTTPException(status_code=400, detail="Uploaded file is empty.")
        if len(image_bytes) > MAX_UPLOAD_SIZE:
            raise HTTPException(status_code=400, detail="Uploaded file exceeds 10MB.")

        return _process_upload(
            app,
            original_filename=file.filename or "capture.jpg",
            image_bytes=image_bytes,
            document_type=document_type,
            glare_threshold=glare_threshold,
        )

    return app


app = create_app()
