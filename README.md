# ID-Scan Demo

Python OpenCV 기반 신분증 이미지 처리 데모입니다.

## Overview

이 프로젝트는 합성 신분증 이미지를 입력받아 다음 파이프라인을 수행합니다.

1. 빛반사(글레어) 감지 및 제거
2. 신분증 영역 자동 감지 및 perspective crop
3. CLAHE와 Unsharp Mask를 통한 선명도 보정

FastAPI API와 Streamlit 데모 UI를 함께 제공합니다.

## Tech Stack

- Python 3.13
- OpenCV
- NumPy
- FastAPI
- Streamlit
- pytest
- ruff
- uv

## Screenshot

배포 후 전/후 비교 스크린샷을 여기에 추가합니다.

## Install And Run

```bash
uv sync
uv run uvicorn app.main:app --reload
uv run streamlit run demo/streamlit_app.py
```

## Tests

```bash
uv run pytest -v
```

## Processing Steps

### Step 1. 빛반사 감지 및 제거

- HSV 색공간의 V 채널에서 밝은 영역을 threshold로 검출합니다.
- dilation으로 마스크를 약간 확장한 뒤 `cv2.inpaint`로 복원합니다.

### Step 2. 신분증 영역 감지

- grayscale, Gaussian blur, Canny edge를 적용합니다.
- contour 후보 중 4각형을 찾아 perspective transform으로 정면 crop 합니다.

### Step 3. 선명도 보정

- LAB 색공간의 L 채널에 CLAHE를 적용해 지역 대비를 높입니다.
- Gaussian blur 기반 unsharp mask로 텍스트와 엣지를 강조합니다.

## API

### `GET /`

```json
{"status": "ok"}
```

### `POST /process`

`multipart/form-data`

- `file`: jpg 또는 png 이미지
- `glare_threshold`: optional query parameter, default `200`

응답 예시:

```json
{
  "card_detected": true,
  "glare_pixel_ratio": 0.0312,
  "original_b64": "...",
  "after_glare_b64": "...",
  "after_detect_b64": "...",
  "final_b64": "..."
}
```

## Streamlit Demo

로컬 Streamlit 앱은 FastAPI 서버 `http://localhost:8000`를 호출합니다.

```bash
uv run streamlit run demo/streamlit_app.py
```

Streamlit Cloud 배포 시에는 standalone 구성으로 단순화하는 방식을 권장합니다.

## Demo Link

배포 후 링크를 여기에 추가합니다.

## Warning

실제 신분증 이미지는 저장소나 데모에 포함하지 않습니다.
데모와 테스트에는 합성 이미지 또는 모자이크 처리된 샘플만 사용하세요.
