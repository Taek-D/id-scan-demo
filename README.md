# ID-Scan Demo

통신 서비스 가입 과정에서 발생하는 신분증 촬영 문제를 가정하고, `촬영 가이드 -> 품질 판정 -> 이미지 보정 -> 제출 -> 관리자 확인` 흐름을 한 번에 보여주는 Python/OpenCV 기반 데모입니다.

## 프로젝트 배경

현장 가입이나 외부 작성 환경에서는 신분증 촬영본이 빛반사, 기울기, 초점 불량, 프레임 이탈 문제로 반려되는 경우가 자주 발생합니다. 이 저장소는 그런 문제를 줄이기 위한 서비스형 시연용 프로토타입으로, 사용자 촬영 화면과 관리자 확인 화면을 함께 제공합니다.

## 현재 구현된 데모 범위

- 모바일 웹 스타일 촬영 화면
  - 신분증 종류 선택
  - 문서별 프레임 오버레이
  - 촬영 단계 안내
  - 카메라 권한 상태 및 입력 소스 상태 표시
  - 재촬영 유도 메시지
- 품질 판정 레이어
  - 빛반사 비율
  - 선명도 점수
  - 프레임 점유율
  - 기울기 감지
  - `제출 가능 / 주의 필요 / 재촬영 필요` 상태 분류
- OpenCV 기반 이미지 처리
  - 글레어 감지 및 제거
  - 신분증 영역 감지 및 crop
  - CLAHE + unsharp mask 기반 선명도 보정
- 관리자 콘솔
  - 제출 목록 조회
  - 품질 상태 확인
  - 처리 결과 다운로드
- 저장/보안 설계 가시화
  - 로컬 SQLite + 파일 저장 기반 데모 저장소
  - 전송 구간, 저장 암호화, 보관 정책, 접근 범위 문구 제공
- PWA 보강
  - manifest 제공
  - service worker 기반 정적 자산 캐시
  - 홈 화면 추가 시연용 설치 감각 제공

## 사용자 흐름

1. 사용자가 `/` 화면에서 신분증 종류를 선택합니다.
2. 카메라를 시작하거나 파일을 업로드합니다.
3. 문서별 프레임과 가이드를 따라 촬영합니다.
4. 서버가 품질 판정과 보정 파이프라인을 실행합니다.
5. 결과 화면에서 재촬영 필요 여부와 단계별 처리 이미지를 확인합니다.
6. `/admin` 화면에서 운영자 관점의 저장 결과와 다운로드 링크를 확인합니다.

## 지원 문서 유형

- `resident_id`: 주민등록증
- `alien_registration`: 외국인등록증
- `passport`: 여권

각 문서 유형은 프레임 비율, 오버레이 라벨, 촬영 팁이 분리되어 있습니다.

## 기술 스택

- Python 3.13
- FastAPI
- OpenCV
- NumPy
- SQLite
- Streamlit
- pytest
- ruff
- uv

## 주요 페이지

- Capture UI: `GET /`
- Admin UI: `GET /admin`
- Swagger UI: `GET /docs`
- Health Check: `GET /api/health`
- Legacy Streamlit Demo: `demo/streamlit_app.py`

## API 요약

### `GET /api/document-types`

문서 유형, 프레임 비율, 촬영 팁을 반환합니다.

### `POST /api/process`

`multipart/form-data`

- `file`: `image/jpeg` or `image/png`
- `document_type`: `resident_id` | `alien_registration` | `passport`
- query `glare_threshold`: `100..254`, default `245`

응답에는 아래가 포함됩니다.

- 품질 판정 정보
- 제출 ID와 관리자 상태
- 원본, 글레어 제거, 크롭, 최종 보정 이미지의 base64 데이터
- 보안/보관 정책 문구

기본 웹 UI에서는 이 값을 노출하지 않고 자동 기본값 `245`를 사용합니다. 기존 실험용 호환 엔드포인트로 `POST /process`도 유지합니다.

## 로컬 실행

```bash
uv sync
uv run uvicorn app.main:app --reload
```

별도 터미널에서 Streamlit 실험 화면을 실행하려면:

```bash
uv run streamlit run demo/streamlit_app.py
```

브라우저 진입 주소:

- Capture UI: `http://127.0.0.1:8000/`
- Admin UI: `http://127.0.0.1:8000/admin`
- Swagger: `http://127.0.0.1:8000/docs`
- Streamlit: `http://127.0.0.1:8501`

## 테스트

```bash
uv run pytest -v
uv run ruff check app tests
```

## 저장 및 보안 관련 메모

- 제출 이미지와 처리 결과는 기본적으로 로컬 `data/` 디렉터리에 저장됩니다.
- 현재 구현은 데모용 저장 구조이며, 운영 환경에서는 암호화된 오브젝트 스토리지와 접근 제어, 만료 정책 자동화가 필요합니다.
- `data/`는 `.gitignore`에 포함되어 저장소에 커밋되지 않습니다.

## 현재 한계

- 실서비스 수준의 인증, HTTPS 종료, KMS, 접근 로그 적재는 포함하지 않습니다.
- OCR, 실명인증 연동, 홀로그램 제거 고도화는 아직 범위 밖입니다.
- PWA는 설치감과 캐시 경험을 위한 수준이며, 오프라인 이미지 처리까지 지원하지 않습니다.

## 샘플 사용 주의

- 실제 신분증 이미지는 저장소에 포함하지 않습니다.
- 테스트와 데모에는 합성 또는 마스킹된 샘플만 사용하세요.
