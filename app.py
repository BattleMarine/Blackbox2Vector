import json
from pathlib import Path

import cv2
import streamlit as st

from src.detector import ObjectDetector
from src.scene_vector import build_scene_vector, build_sample_scene_vector
from src.summarizer import summarize_scene
from src.video_loader import extract_sample_frames, get_video_metadata, save_uploaded_video
from src.visualizer import draw_detection_overlay, draw_top_view


INPUT_DIR = Path("data/input")
FRAMES_DIR = Path("data/frames")
OUTPUT_DIR = Path("data/output")
SCENE_VECTOR_PATH = OUTPUT_DIR / "scene_vector.json"


def format_file_size(byte_size: int) -> str:
    """업로드 파일 크기를 사람이 읽기 쉬운 단위로 바꾼다."""
    if byte_size < 1024:
        return f"{byte_size} B"
    if byte_size < 1024 * 1024:
        return f"{byte_size / 1024:.1f} KB"
    return f"{byte_size / (1024 * 1024):.1f} MB"


def clear_previous_frames(frames_dir: Path) -> None:
    """이전 실행 결과가 섞이지 않도록 앱이 생성한 샘플 프레임만 정리한다."""
    frames_dir.mkdir(parents=True, exist_ok=True)
    for frame_path in frames_dir.glob("*.jpg"):
        frame_path.unlink()


def save_scene_vector(scene_vector: dict, output_path: Path) -> Path:
    """분석 결과를 사람이 읽을 수 있는 JSON 파일로 저장한다."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(scene_vector, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return output_path


def load_frame_rgb(frame_path: Path):
    """OpenCV가 읽은 BGR 프레임을 Streamlit 표시용 RGB로 변환한다."""
    frame_bgr = cv2.imread(str(frame_path))
    if frame_bgr is None:
        raise ValueError(f"프레임 이미지를 읽을 수 없습니다: {frame_path}")
    frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
    return frame_bgr, frame_rgb


def show_video_metadata(metadata: dict[str, float | int]) -> None:
    """영상 메타데이터를 앱 화면에 요약 표시한다."""
    st.markdown("### 영상 메타데이터")
    metric_columns = st.columns(4)
    metric_columns[0].metric("해상도", f"{metadata['width']} x {metadata['height']}")
    metric_columns[1].metric("FPS", f"{metadata['fps']:.2f}")
    metric_columns[2].metric("프레임 수", f"{metadata['frame_count']}")
    metric_columns[3].metric("길이", f"{metadata['duration_seconds']:.2f}초")


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
        st.caption("아직 업로드된 영상이 없습니다. 업로드 없이 실행하면 샘플 결과를 확인합니다.")

    if st.button("분석 시작", type="primary"):
        try:
            if uploaded_file is None:
                scene_vector = build_sample_scene_vector()
                save_scene_vector(scene_vector, SCENE_VECTOR_PATH)
                summary = summarize_scene(scene_vector)

                st.success("업로드 영상이 없어 샘플 Scene Vector JSON을 생성했습니다.")
                st.write(summary)

                left_column, right_column = st.columns([1, 1])
                with left_column:
                    st.markdown("### Scene Vector JSON")
                    st.json(scene_vector)
                with right_column:
                    st.markdown("### 2.5D 탑뷰")
                    st.pyplot(draw_top_view(scene_vector))
            else:
                clear_previous_frames(FRAMES_DIR)
                video_path = save_uploaded_video(uploaded_file, INPUT_DIR)
                metadata = get_video_metadata(video_path)
                sample_frames = extract_sample_frames(video_path, FRAMES_DIR, sample_fps=1, max_frames=5)

                detector = ObjectDetector()
                first_frame_path = sample_frames[0]
                first_frame_bgr, first_frame_rgb = load_frame_rgb(first_frame_path)
                detections = detector.detect_objects(first_frame_bgr)
                overlay_bgr = draw_detection_overlay(first_frame_bgr, detections)
                overlay_rgb = cv2.cvtColor(overlay_bgr, cv2.COLOR_BGR2RGB)

                timestamp = 0.0
                frame_size = (int(metadata["width"]), int(metadata["height"]))
                scene_vector = build_scene_vector(
                    frame_index=1,
                    timestamp=timestamp,
                    detections=detections,
                    frame_size=frame_size,
                )
                save_scene_vector(scene_vector, SCENE_VECTOR_PATH)
                summary = summarize_scene(scene_vector)

                st.success("업로드 영상 기반 v1.1 더미 분석을 완료했습니다.")
                st.write(summary)
                st.caption(
                    "현재 객체 검출은 실제 YOLO가 아니라 추출 프레임에 적용한 더미 detection입니다."
                )

                show_video_metadata(metadata)

                st.markdown("### 샘플 프레임")
                frame_columns = st.columns(2)
                with frame_columns[0]:
                    st.image(first_frame_rgb, caption=f"원본 프레임: {first_frame_path.name}")
                with frame_columns[1]:
                    st.image(overlay_rgb, caption="더미 detection 오버레이")

                if len(sample_frames) > 1:
                    st.caption(
                        f"총 {len(sample_frames)}개의 샘플 프레임을 추출했습니다. "
                        "화면에는 첫 번째 프레임 분석 결과를 표시합니다."
                    )

                left_column, right_column = st.columns([1, 1])
                with left_column:
                    st.markdown("### Scene Vector JSON")
                    st.json(scene_vector)
                with right_column:
                    st.markdown("### 2.5D 탑뷰")
                    st.pyplot(draw_top_view(scene_vector))

            json_text = SCENE_VECTOR_PATH.read_text(encoding="utf-8")
            st.download_button(
                "scene_vector.json 다운로드",
                data=json_text,
                file_name="scene_vector.json",
                mime="application/json",
            )
            st.caption(f"분석 결과를 `{SCENE_VECTOR_PATH.as_posix()}`에 저장했습니다.")
        except Exception as exc:
            st.error(f"분석 중 오류가 발생했습니다: {exc}")


if __name__ == "__main__":
    main()
