from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class DocumentTypeConfig:
    key: str
    label: str
    aspect_ratio: float
    overlay_label: str
    capture_tips: tuple[str, ...]


DOCUMENT_TYPES: dict[str, DocumentTypeConfig] = {
    "resident_id": DocumentTypeConfig(
        key="resident_id",
        label="주민등록증",
        aspect_ratio=85.6 / 54.0,
        overlay_label="주민등록증 프레임",
        capture_tips=(
            "신분증 전체가 프레임 안에 들어오도록 맞춰 주세요.",
            "광원이 정면으로 비치지 않도록 휴대폰 각도를 조금만 조정해 주세요.",
            "문자 영역이 흐리지 않도록 손 떨림 없이 1초 정도 유지해 주세요.",
        ),
    ),
    "alien_registration": DocumentTypeConfig(
        key="alien_registration",
        label="외국인등록증",
        aspect_ratio=85.6 / 54.0,
        overlay_label="외국인등록증 프레임",
        capture_tips=(
            "카드의 모서리가 모두 보이도록 배경과 구분해 주세요.",
            "홀로그램이 강하게 반사되면 좌우 각도를 조금씩 바꿔 주세요.",
            "카드가 프레임보다 너무 작게 보이면 기기를 더 가까이 가져와 주세요.",
        ),
    ),
    "passport": DocumentTypeConfig(
        key="passport",
        label="여권",
        aspect_ratio=125.0 / 88.0,
        overlay_label="여권 프레임",
        capture_tips=(
            "펼친 여권의 사진면이 프레임 중앙에 오도록 맞춰 주세요.",
            "책등이 휘지 않도록 바닥에 평평하게 놓고 촬영해 주세요.",
            "MRZ와 얼굴 사진이 동시에 선명하게 보이도록 초점을 확인해 주세요.",
        ),
    ),
}


def get_document_type_config(document_type: str) -> DocumentTypeConfig:
    if document_type not in DOCUMENT_TYPES:
        raise KeyError(document_type)
    return DOCUMENT_TYPES[document_type]


def list_document_type_payloads() -> list[dict[str, object]]:
    return [asdict(config) for config in DOCUMENT_TYPES.values()]
