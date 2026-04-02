from __future__ import annotations

import base64
import io

import requests
import streamlit as st
from PIL import Image

API_URL = "http://localhost:8000"


def base64_to_image(encoded: str) -> Image.Image:
    return Image.open(io.BytesIO(base64.b64decode(encoded)))


st.set_page_config(page_title="ID Scan Demo", layout="wide")
st.title("신분증 이미지 처리 데모")
st.warning("실제 신분증 이미지를 업로드하지 마세요. 합성 또는 모자이크 처리된 샘플만 사용하세요.")

with st.sidebar:
    st.header("설정")
    glare_threshold = st.slider("글레어 감지 임계값", min_value=100, max_value=254, value=200)
    run_processing = st.button("처리 시작", type="primary")

uploaded_file = st.file_uploader("이미지 업로드", type=["jpg", "jpeg", "png"])

if run_processing:
    if uploaded_file is None:
        st.error("먼저 이미지를 업로드해 주세요.")
    else:
        files = {
            "file": (
                uploaded_file.name,
                uploaded_file.getvalue(),
                uploaded_file.type or "image/png",
            )
        }
        try:
            response = requests.post(
                f"{API_URL}/process",
                params={"glare_threshold": glare_threshold},
                files=files,
                timeout=60,
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            st.error(f"API 호출에 실패했습니다: {exc}")
        else:
            payload = response.json()

            detected_label = "성공" if payload["card_detected"] else "실패"
            st.metric("신분증 감지", detected_label)
            st.metric("글레어 픽셀 비율", f"{payload['glare_pixel_ratio']:.2%}")

            col1, col2 = st.columns(2)
            with col1:
                st.image(base64_to_image(payload["original_b64"]), caption="원본", use_container_width=True)
                st.caption("업로드한 원본 이미지입니다.")
                st.image(
                    base64_to_image(payload["after_detect_b64"]),
                    caption="신분증 크롭",
                    use_container_width=True,
                )
                st.caption("윤곽선 감지와 perspective transform 결과입니다.")

            with col2:
                st.image(
                    base64_to_image(payload["after_glare_b64"]),
                    caption="글레어 제거",
                    use_container_width=True,
                )
                st.caption("밝은 반사 영역을 감지하고 inpainting으로 복원한 결과입니다.")
                st.image(base64_to_image(payload["final_b64"]), caption="최종 보정", use_container_width=True)
                st.caption("CLAHE와 unsharp mask 적용 후 최종 결과입니다.")
