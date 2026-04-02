from __future__ import annotations

import base64

from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from app.pipeline import ndarray_to_jpeg_bytes, run_pipeline
from app.schemas import ProcessResponse

MAX_UPLOAD_SIZE = 10 * 1024 * 1024
ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png"}

app = FastAPI(title="ID Scan Demo", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _to_base64(image_bytes: bytes) -> str:
    return base64.b64encode(image_bytes).decode("utf-8")


@app.get("/")
async def healthcheck() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/process", response_model=ProcessResponse)
async def process_image(
    file: UploadFile = File(...),
    glare_threshold: int = Query(default=200, ge=100, le=254),
) -> ProcessResponse:
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(status_code=400, detail="Only JPEG and PNG images are supported.")

    image_bytes = await file.read()
    if not image_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")
    if len(image_bytes) > MAX_UPLOAD_SIZE:
        raise HTTPException(status_code=400, detail="Uploaded file exceeds 10MB.")

    try:
        result = run_pipeline(image_bytes, glare_threshold=glare_threshold)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    glare_pixel_ratio = float(result.glare_mask.astype(bool).sum() / result.glare_mask.size)

    return ProcessResponse(
        card_detected=result.card_detected,
        glare_pixel_ratio=glare_pixel_ratio,
        original_b64=_to_base64(ndarray_to_jpeg_bytes(result.original)),
        after_glare_b64=_to_base64(ndarray_to_jpeg_bytes(result.after_glare)),
        after_detect_b64=_to_base64(ndarray_to_jpeg_bytes(result.after_detect)),
        final_b64=_to_base64(ndarray_to_jpeg_bytes(result.after_enhance)),
    )
