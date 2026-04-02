from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import UTC, datetime
from pathlib import Path


class SubmissionStore:
    """Persist processed submissions and notice data for the demo admin flow."""

    def __init__(self, data_dir: Path) -> None:
        self.data_dir = data_dir
        self.upload_dir = self.data_dir / "uploads"
        self.variant_dir = self.data_dir / "variants"
        self.db_path = self.data_dir / "id_scan_demo.sqlite3"

    def initialize(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        self.variant_dir.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS notices (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    title TEXT NOT NULL,
                    body TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS submissions (
                    id TEXT PRIMARY KEY,
                    created_at TEXT NOT NULL,
                    document_type TEXT NOT NULL,
                    original_filename TEXT NOT NULL,
                    capture_status TEXT NOT NULL,
                    capture_status_label TEXT NOT NULL,
                    capture_summary TEXT NOT NULL,
                    user_messages TEXT NOT NULL,
                    admin_codes TEXT NOT NULL,
                    admin_status TEXT NOT NULL,
                    card_detected INTEGER NOT NULL,
                    blur_score REAL NOT NULL,
                    glare_ratio REAL NOT NULL,
                    frame_fill_ratio REAL NOT NULL,
                    tilt_angle REAL,
                    original_path TEXT NOT NULL,
                    glare_path TEXT NOT NULL,
                    detect_path TEXT NOT NULL,
                    final_path TEXT NOT NULL,
                    transmission_mode TEXT NOT NULL,
                    encryption_policy TEXT NOT NULL,
                    retention_policy TEXT NOT NULL
                )
                """
            )
            now = self._now()
            connection.execute(
                """
                INSERT OR IGNORE INTO notices (id, title, body, updated_at)
                VALUES (1, ?, ?, ?)
                """,
                (
                    "시범 운영 안내",
                    "본 화면은 수주형 데모를 위한 운영 콘솔입니다. 업로드 이미지는 로컬 데모 저장소에만 저장되며, 30일 보관 정책을 가정합니다.",
                    now,
                ),
            )
            connection.commit()

    def create_submission(
        self,
        *,
        document_type: str,
        original_filename: str,
        quality: dict[str, object],
        card_detected: bool,
        original_bytes: bytes,
        glare_bytes: bytes,
        detect_bytes: bytes,
        final_bytes: bytes,
    ) -> dict[str, object]:
        submission_id = uuid.uuid4().hex
        created_at = self._now()
        suffix = Path(original_filename).suffix.lower() or ".bin"

        original_path = self.upload_dir / f"{submission_id}{suffix}"
        glare_path = self.variant_dir / f"{submission_id}-glare.jpg"
        detect_path = self.variant_dir / f"{submission_id}-detect.jpg"
        final_path = self.variant_dir / f"{submission_id}-final.jpg"

        original_path.write_bytes(original_bytes)
        glare_path.write_bytes(glare_bytes)
        detect_path.write_bytes(detect_bytes)
        final_path.write_bytes(final_bytes)

        record = {
            "id": submission_id,
            "created_at": created_at,
            "document_type": document_type,
            "original_filename": original_filename,
            "capture_status": quality["status"],
            "capture_status_label": quality["status_label"],
            "capture_summary": quality["summary"],
            "user_messages": list(quality["user_messages"]),
            "admin_codes": list(quality["admin_codes"]),
            "admin_status": "REVIEW_PENDING",
            "card_detected": bool(card_detected),
            "blur_score": float(quality["blur_score"]),
            "glare_ratio": float(quality["glare_ratio"]),
            "frame_fill_ratio": float(quality["frame_fill_ratio"]),
            "tilt_angle": quality["tilt_angle"],
            "original_path": str(original_path),
            "glare_path": str(glare_path),
            "detect_path": str(detect_path),
            "final_path": str(final_path),
            "transmission_mode": "TLS_REQUIRED",
            "encryption_policy": "AES256_AT_REST",
            "retention_policy": "30_DAY_DEMO_POLICY",
        }

        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO submissions (
                    id, created_at, document_type, original_filename, capture_status,
                    capture_status_label, capture_summary, user_messages, admin_codes, admin_status,
                    card_detected, blur_score, glare_ratio, frame_fill_ratio, tilt_angle,
                    original_path, glare_path, detect_path, final_path,
                    transmission_mode, encryption_policy, retention_policy
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record["id"],
                    record["created_at"],
                    record["document_type"],
                    record["original_filename"],
                    record["capture_status"],
                    record["capture_status_label"],
                    record["capture_summary"],
                    json.dumps(record["user_messages"], ensure_ascii=False),
                    json.dumps(record["admin_codes"], ensure_ascii=False),
                    record["admin_status"],
                    int(record["card_detected"]),
                    record["blur_score"],
                    record["glare_ratio"],
                    record["frame_fill_ratio"],
                    record["tilt_angle"],
                    record["original_path"],
                    record["glare_path"],
                    record["detect_path"],
                    record["final_path"],
                    record["transmission_mode"],
                    record["encryption_policy"],
                    record["retention_policy"],
                ),
            )
            connection.commit()

        return record

    def list_submissions(self) -> list[dict[str, object]]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT id, created_at, document_type, original_filename, capture_status,
                       capture_status_label, capture_summary, admin_codes, admin_status,
                       card_detected, blur_score, glare_ratio, frame_fill_ratio, tilt_angle
                FROM submissions
                ORDER BY datetime(created_at) DESC
                """
            ).fetchall()
        return [self._row_to_submission(row) for row in rows]

    def get_submission(self, submission_id: str) -> dict[str, object] | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT *
                FROM submissions
                WHERE id = ?
                """,
                (submission_id,),
            ).fetchone()
        if row is None:
            return None
        record = self._row_to_full_submission(row)
        record["downloads"] = {
            "original": f"/api/submissions/{submission_id}/download?variant=original",
            "glare": f"/api/submissions/{submission_id}/download?variant=glare",
            "detect": f"/api/submissions/{submission_id}/download?variant=detect",
            "final": f"/api/submissions/{submission_id}/download?variant=final",
        }
        return record

    def get_notice(self) -> dict[str, str]:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT title, body, updated_at FROM notices WHERE id = 1"
            ).fetchone()
        assert row is not None
        return {
            "title": row["title"],
            "body": row["body"],
            "updated_at": row["updated_at"],
        }

    def get_file_path(self, submission_id: str, variant: str) -> Path | None:
        record = self.get_submission(submission_id)
        if record is None:
            return None
        path_key = f"{variant}_path"
        if path_key not in record:
            return None
        return Path(str(record[path_key]))

    def _row_to_submission(self, row: sqlite3.Row) -> dict[str, object]:
        return {
            "id": row["id"],
            "created_at": row["created_at"],
            "document_type": row["document_type"],
            "original_filename": row["original_filename"],
            "capture_status": row["capture_status"],
            "capture_status_label": row["capture_status_label"],
            "capture_summary": row["capture_summary"],
            "admin_codes": json.loads(row["admin_codes"]),
            "admin_status": row["admin_status"],
            "card_detected": bool(row["card_detected"]),
            "blur_score": row["blur_score"],
            "glare_ratio": row["glare_ratio"],
            "frame_fill_ratio": row["frame_fill_ratio"],
            "tilt_angle": row["tilt_angle"],
        }

    def _row_to_full_submission(self, row: sqlite3.Row) -> dict[str, object]:
        return {
            "id": row["id"],
            "created_at": row["created_at"],
            "document_type": row["document_type"],
            "original_filename": row["original_filename"],
            "capture_status": row["capture_status"],
            "capture_status_label": row["capture_status_label"],
            "capture_summary": row["capture_summary"],
            "user_messages": json.loads(row["user_messages"]),
            "admin_codes": json.loads(row["admin_codes"]),
            "admin_status": row["admin_status"],
            "card_detected": bool(row["card_detected"]),
            "blur_score": row["blur_score"],
            "glare_ratio": row["glare_ratio"],
            "frame_fill_ratio": row["frame_fill_ratio"],
            "tilt_angle": row["tilt_angle"],
            "original_path": row["original_path"],
            "glare_path": row["glare_path"],
            "detect_path": row["detect_path"],
            "final_path": row["final_path"],
            "transmission_mode": row["transmission_mode"],
            "encryption_policy": row["encryption_policy"],
            "retention_policy": row["retention_policy"],
        }

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _now(self) -> str:
        return datetime.now(UTC).isoformat()
