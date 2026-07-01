from pathlib import Path

import streamlit as st

from src.scene_vector import build_sample_scene_vector
from src.summarizer import summarize_scene
from src.visualizer import draw_top_view


def format_file_size(byte_size: int) -> str:
    """업로드 파일 크기를 사람이 읽기 쉬운 단위로 바꾼다."""
    if byte_size < 1024:
        return f"{byte_size} B"
    if byte_size < 1024 * 1024:
        return f"{byte_size / 1024:.1f} KB"
    return f"{byte_size / (1024 * 1024):.1f} MB"


def main() -> None:
    st.set_page_config(page_title="BlackBox2Vector", layout="wide")

    st.title("BlackBox2Vector")
    st.subheader("2D 블랙박스 영상에서 Scene Vector JSON으로")

    st.write(
        "데모 v1은 정밀한 3D 복원 시스템이 아니라, 영상 기반 추정값을 "
        "자차 기준 Scene Vector JSON으로 표현하는 초기 구조 확인용 앱입니다."
    )

    uploaded_file = st.file_uploader(
        "블랙박스 영상 업로드",
        type=["mp4", "avi", "mov", "mkv"],
        accept_multiple_files=False,
    )

    if uploaded_file is not None:
        st.info(f"업로드 파일: {uploaded_file.name}")
        st.info(f"파일 크기: {format_file_size(uploaded_file.size)}")
    else:
        st.caption("아직 업로드된 영상이 없습니다. 샘플 결과는 업로드 없이도 확인할 수 있습니다.")

    if st.button("분석 시작", type="primary"):
        scene_vector = build_sample_scene_vector()
        summary = summarize_scene(scene_vector)

        st.success("샘플 Scene Vector JSON을 생성했습니다.")
        st.write(summary)

        left_column, right_column = st.columns([1, 1])

        with left_column:
            st.markdown("### Scene Vector JSON")
            st.json(scene_vector)

        with right_column:
            st.markdown("### 2.5D 탑뷰")
            top_view_figure = draw_top_view(scene_vector)
            st.pyplot(top_view_figure)

        output_hint = Path("data/output/scene_vector.json")
        st.caption(f"추후 실제 분석 결과는 `{output_hint.as_posix()}` 경로에 저장할 예정입니다.")


if __name__ == "__main__":
    main()
