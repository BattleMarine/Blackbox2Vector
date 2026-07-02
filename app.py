import json
import sys
from importlib import import_module, reload
from importlib.util import find_spec
from pathlib import Path

import cv2
import streamlit as st

from src.evidence_pipeline import build_overlay_items, split_detections_by_certainty
from src.light_candidate_detector import detect_light_candidates_with_diagnostics
from src.motion_candidate_detector import annotate_detections_with_motion, extract_motion_candidates
from src.scene_vector import build_scene_vector, build_sample_scene_vector
from src.summarizer import summarize_scene
from src.video_loader import extract_sample_frames, get_video_metadata, save_uploaded_video
from src.visualizer import draw_detection_overlay, draw_top_view


INPUT_DIR = Path("data/input")
FRAMES_DIR = Path("data/frames")
OUTPUT_DIR = Path("data/output")
SCENE_VECTOR_PATH = OUTPUT_DIR / "scene_vector.json"
SCENE_VECTOR_SEQUENCE_PATH = OUTPUT_DIR / "scene_vectors.json"
YOLO_DEFAULT_MODEL = "yolov8n.pt"
SAMPLE_FPS = 1
MAX_SAMPLE_FRAMES = 12


def format_file_size(byte_size: int) -> str:
    """업로드 파일 크기를 사람이 읽기 쉬운 단위로 바꾼다."""
    if byte_size < 1024:
        return f"{byte_size} B"
    if byte_size < 1024 * 1024:
        return f"{byte_size / 1024:.1f} KB"
    return f"{byte_size / (1024 * 1024):.1f} MB"


def clear_previous_frames(frames_dir: Path) -> None:
    """이전 실행 결과가 섞이지 않도록 샘플 프레임만 정리한다."""
    frames_dir.mkdir(parents=True, exist_ok=True)
    for frame_path in frames_dir.glob("*.jpg"):
        frame_path.unlink()


def save_json_data(data: dict | list, output_path: Path) -> Path:
    """분석 결과를 사람이 읽을 수 있는 UTF-8 JSON 파일로 저장한다."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return output_path


def save_scene_vector(scene_vector: dict, output_path: Path) -> Path:
    return save_json_data(scene_vector, output_path)


def save_scene_vectors(scene_vectors: list[dict], output_path: Path) -> Path:
    return save_json_data(scene_vectors, output_path)


def load_frame_rgb(frame_path: Path):
    """OpenCV가 읽은 BGR 프레임을 Streamlit 표시용 RGB로 변환한다."""
    frame_bgr = cv2.imread(str(frame_path))
    if frame_bgr is None:
        raise ValueError(f"프레임 이미지를 읽을 수 없습니다: {frame_path}")
    frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
    return frame_bgr, frame_rgb


def show_video_metadata(metadata: dict[str, float | int]) -> None:
    st.markdown("### 영상 메타데이터")
    metric_columns = st.columns(4)
    metric_columns[0].metric("해상도", f"{metadata['width']} x {metadata['height']}")
    metric_columns[1].metric("FPS", f"{metadata['fps']:.2f}")
    metric_columns[2].metric("프레임 수", f"{metadata['frame_count']}")
    metric_columns[3].metric("길이", f"{metadata['duration_seconds']:.2f}초")


def show_detector_settings() -> tuple[str, str, float, bool, int, bool]:
    """YOLO 결과는 v1.4.4에서 확정 객체와 후보로 다시 분리한다."""
    st.sidebar.header("검출 설정")
    backend_label = st.sidebar.radio(
        "검출 백엔드",
        ["더미 detector", "YOLO detector"],
        help="YOLO는 데모용 객체 검출 백엔드입니다. v1.4.4에서는 낮은 신뢰도와 ROI 밖 결과를 후보로 내립니다.",
    )
    backend = "yolo" if backend_label == "YOLO detector" else "dummy"
    model_path = st.sidebar.text_input("YOLO 모델 경로", value=YOLO_DEFAULT_MODEL)
    confidence_threshold = st.sidebar.slider("YOLO 추론 신뢰도 기준", 0.05, 0.90, 0.25, 0.05)
    use_light_candidates = st.sidebar.checkbox("밝은 영역 evidence 수집", value=True)
    light_brightness_threshold = st.sidebar.slider("밝은 영역 기준", 180, 255, 220, 5)
    use_motion_assist = st.sidebar.checkbox("프레임 움직임 evidence 수집", value=True)

    st.sidebar.caption("v1.4.4: raw evidence, object candidate, confirmed object를 분리합니다.")
    return backend, model_path, confidence_threshold, use_light_candidates, light_brightness_threshold, use_motion_assist


def show_runtime_status() -> None:
    st.sidebar.header("실행 환경")
    st.sidebar.code(sys.executable, language="text")
    if find_spec("ultralytics") is None:
        st.sidebar.warning("현재 Python에서 ultralytics를 찾을 수 없습니다.")
        st.sidebar.code(f"{sys.executable} -m pip install ultralytics", language="bash")
    else:
        st.sidebar.success("ultralytics 설치 확인")


def create_object_detector(backend: str, model_path: str, confidence_threshold: float):
    """Streamlit 재실행 중 남은 이전 detector 모듈 캐시를 피한다."""
    detector_module = import_module("src.detector")
    detector_module = reload(detector_module)
    return detector_module.ObjectDetector(
        backend=backend,
        model_path=model_path,
        confidence_threshold=confidence_threshold,
    )


def analyze_sample_frames(
    sample_frames: list[Path],
    detector,
    frame_size: tuple[int, int],
    use_light_candidates: bool,
    light_brightness_threshold: int,
    use_motion_assist: bool,
) -> tuple[list[dict], list[list[dict]], list[dict], list[dict], list[dict]]:
    """모든 검출 결과를 바로 objects에 넣지 않고 세 단계로 분리한다."""
    scene_vectors: list[dict] = []
    overlay_items_by_frame: list[list[dict]] = []
    light_diagnostics_by_frame: list[dict] = []
    motion_diagnostics_by_frame: list[dict] = []
    certainty_diagnostics_by_frame: list[dict] = []
    previous_light_candidates: list[dict] = []
    previous_frame_bgr = None
    progress = st.progress(0, text="샘플 프레임 분석 준비 중")

    for frame_order, frame_path in enumerate(sample_frames, start=1):
        frame_bgr, _ = load_frame_rgb(frame_path)
        model_detections = detector.detect_objects(frame_bgr)
        light_candidates: list[dict] = []
        light_diagnostics: dict = {"rejected_count": 0, "rejected_by_reason": {}, "rejected_samples": []}

        if use_light_candidates:
            light_candidates, light_diagnostics = detect_light_candidates_with_diagnostics(
                frame_bgr,
                previous_candidates=previous_light_candidates,
                brightness_threshold=light_brightness_threshold,
            )

        motion_candidates: list[dict] = []
        motion_diagnostics: dict = {
            "verified_count": 0,
            "motion_candidate_count": 0,
            "rejected_count": 0,
            "rejected_by_reason": {},
        }
        if use_motion_assist and previous_frame_bgr is not None:
            model_detections, verification_diagnostics = annotate_detections_with_motion(
                model_detections,
                previous_frame=previous_frame_bgr,
                current_frame=frame_bgr,
            )
            motion_candidates, candidate_diagnostics = extract_motion_candidates(
                previous_frame=previous_frame_bgr,
                current_frame=frame_bgr,
            )
            motion_diagnostics = {
                "verified_count": verification_diagnostics.get("verified_count", 0),
                "motion_candidate_count": len(motion_candidates),
                "rejected_count": candidate_diagnostics.get("rejected_count", 0),
                "rejected_by_reason": candidate_diagnostics.get("rejected_by_reason", {}),
            }

        raw_evidence, object_candidates, confirmed_objects, certainty_diagnostics = split_detections_by_certainty(
            model_detections=model_detections,
            light_detections=light_candidates,
            motion_detections=motion_candidates,
            frame_size=frame_size,
        )

        previous_light_candidates = light_candidates
        previous_frame_bgr = frame_bgr
        timestamp = round((frame_order - 1) / SAMPLE_FPS, 2)
        scene_vector = build_scene_vector(
            frame_index=frame_order,
            timestamp=timestamp,
            detections=confirmed_objects,
            frame_size=frame_size,
            raw_evidence=raw_evidence,
            object_candidates=object_candidates,
        )

        scene_vectors.append(scene_vector)
        overlay_items_by_frame.append(build_overlay_items(scene_vector))
        light_diagnostics_by_frame.append(light_diagnostics)
        motion_diagnostics_by_frame.append(motion_diagnostics)
        certainty_diagnostics_by_frame.append(certainty_diagnostics)
        progress.progress(frame_order / len(sample_frames), text=f"샘플 프레임 분석 중: {frame_order}/{len(sample_frames)}")

    progress.empty()
    return scene_vectors, overlay_items_by_frame, light_diagnostics_by_frame, motion_diagnostics_by_frame, certainty_diagnostics_by_frame


def store_sample_result(scene_vector: dict) -> None:
    save_scene_vector(scene_vector, SCENE_VECTOR_PATH)
    st.session_state["analysis_result"] = {"mode": "sample", "scene_vector": scene_vector}


def store_video_result(
    metadata: dict[str, float | int],
    sample_frames: list[Path],
    scene_vectors: list[dict],
    overlay_items_by_frame: list[list[dict]],
    light_diagnostics_by_frame: list[dict],
    motion_diagnostics_by_frame: list[dict],
    certainty_diagnostics_by_frame: list[dict],
    detector_backend: str,
) -> None:
    save_scene_vector(scene_vectors[0], SCENE_VECTOR_PATH)
    save_scene_vectors(scene_vectors, SCENE_VECTOR_SEQUENCE_PATH)
    st.session_state["analysis_result"] = {
        "mode": "video",
        "metadata": metadata,
        "frame_paths": [str(frame_path) for frame_path in sample_frames],
        "scene_vectors": scene_vectors,
        "overlay_items_by_frame": overlay_items_by_frame,
        "light_diagnostics_by_frame": light_diagnostics_by_frame,
        "motion_diagnostics_by_frame": motion_diagnostics_by_frame,
        "certainty_diagnostics_by_frame": certainty_diagnostics_by_frame,
        "detector_backend": detector_backend,
    }


def render_sample_result(scene_vector: dict) -> None:
    summary = summarize_scene(scene_vector)
    st.success("업로드 영상 없이 샘플 Scene Vector JSON을 생성했습니다.")
    st.write(summary)

    left_column, right_column = st.columns([1, 1])
    with left_column:
        st.markdown("### Scene Vector JSON")
        st.json(scene_vector)
    with right_column:
        st.markdown("### 2.5D 탑뷰")
        st.pyplot(draw_top_view(scene_vector))

    json_text = SCENE_VECTOR_PATH.read_text(encoding="utf-8")
    st.download_button("scene_vector.json 다운로드", data=json_text, file_name="scene_vector.json", mime="application/json")


def render_rejection_caption(prefix: str, diagnostics: dict) -> None:
    rejected_count = diagnostics.get("rejected_count", 0)
    if not rejected_count:
        return
    reason_text = ", ".join(f"{reason} {count}개" for reason, count in diagnostics.get("rejected_by_reason", {}).items())
    st.caption(f"{prefix} {rejected_count}개: {reason_text}")


def render_video_result(result: dict) -> None:
    metadata = result["metadata"]
    frame_paths = [Path(path) for path in result["frame_paths"]]
    scene_vectors = result["scene_vectors"]
    overlay_items_by_frame = result["overlay_items_by_frame"]
    light_diagnostics_by_frame = result.get("light_diagnostics_by_frame", [])
    motion_diagnostics_by_frame = result.get("motion_diagnostics_by_frame", [])
    certainty_diagnostics_by_frame = result.get("certainty_diagnostics_by_frame", [])
    detector_backend = result["detector_backend"]

    show_video_metadata(metadata)
    st.markdown("### 샘플 프레임 시퀀스")
    selected_frame_number = st.slider(
        "프레임 선택",
        min_value=1,
        max_value=len(frame_paths),
        value=1,
        format="프레임 %d",
        help="슬라이더를 옆으로 움직이면 추출된 샘플 프레임을 영상처럼 넘겨볼 수 있습니다.",
    )
    selected_index = selected_frame_number - 1

    selected_frame_path = frame_paths[selected_index]
    selected_scene_vector = scene_vectors[selected_index]
    selected_overlay_items = overlay_items_by_frame[selected_index]
    selected_light_diagnostics = light_diagnostics_by_frame[selected_index] if selected_index < len(light_diagnostics_by_frame) else {}
    selected_motion_diagnostics = motion_diagnostics_by_frame[selected_index] if selected_index < len(motion_diagnostics_by_frame) else {}
    selected_certainty_diagnostics = (
        certainty_diagnostics_by_frame[selected_index] if selected_index < len(certainty_diagnostics_by_frame) else {}
    )

    frame_bgr, frame_rgb = load_frame_rgb(selected_frame_path)
    overlay_bgr = draw_detection_overlay(frame_bgr, selected_overlay_items)
    overlay_rgb = cv2.cvtColor(overlay_bgr, cv2.COLOR_BGR2RGB)

    summary = summarize_scene(selected_scene_vector)
    object_count = len(selected_scene_vector.get("objects", []))
    candidate_count = len(selected_scene_vector.get("object_candidates", []))
    evidence_count = len(selected_scene_vector.get("raw_evidence", []))

    st.success(f"프레임 {selected_index + 1}/{len(frame_paths)} 분석 결과를 표시합니다. 검출 백엔드: {detector_backend}")
    st.write(summary)
    st.info(f"확정 객체 {object_count}개, 객체 후보 {candidate_count}개, raw evidence {evidence_count}개")
    if selected_certainty_diagnostics:
        st.caption(f"승격 진단: {selected_certainty_diagnostics}")

    render_rejection_caption("Scene Vector에서 제외된 광원/반사", selected_light_diagnostics)
    render_rejection_caption("움직임 후보에서 제외된 영역", selected_motion_diagnostics)

    frame_columns = st.columns(2)
    with frame_columns[0]:
        st.image(frame_rgb, caption=f"원본 프레임: {selected_frame_path.name}")
    with frame_columns[1]:
        st.image(overlay_rgb, caption="레이어 오버레이: confirmed/object candidate/raw evidence")

    left_column, right_column = st.columns([1, 1])
    with left_column:
        st.markdown("### 선택 프레임 Scene Vector JSON")
        st.json(selected_scene_vector)
    with right_column:
        st.markdown("### 선택 프레임 2.5D 탑뷰")
        st.pyplot(draw_top_view(selected_scene_vector))

    selected_json = json.dumps(selected_scene_vector, ensure_ascii=False, indent=2)
    sequence_json = SCENE_VECTOR_SEQUENCE_PATH.read_text(encoding="utf-8")
    download_columns = st.columns(2)
    with download_columns[0]:
        st.download_button(
            "선택 프레임 scene_vector.json 다운로드",
            data=selected_json,
            file_name=f"scene_vector_frame_{selected_index + 1:04d}.json",
            mime="application/json",
        )
    with download_columns[1]:
        st.download_button("전체 scene_vectors.json 다운로드", data=sequence_json, file_name="scene_vectors.json", mime="application/json")


def render_analysis_result() -> None:
    result = st.session_state.get("analysis_result")
    if result is None:
        return
    if result["mode"] == "sample":
        render_sample_result(result["scene_vector"])
    elif result["mode"] == "video":
        render_video_result(result)


def main() -> None:
    st.set_page_config(page_title="BlackBox2Vector", layout="wide")

    st.title("BlackBox2Vector")
    st.subheader("2D 블랙박스 영상에서 Scene Vector JSON으로")
    st.write(
        "데모 v1.4.4는 YOLO 기반 결과를 더 보수적으로 다룹니다. "
        "밝은 점과 움직임 영역은 최종 객체가 아니라 raw evidence 또는 object candidate로 분리합니다."
    )

    (
        detector_backend,
        yolo_model_path,
        confidence_threshold,
        use_light_candidates,
        light_brightness_threshold,
        use_motion_assist,
    ) = show_detector_settings()
    show_runtime_status()

    uploaded_file = st.file_uploader("블랙박스 영상 업로드", type=["mp4", "avi", "mov", "mkv"], accept_multiple_files=False)

    if uploaded_file is not None:
        st.info(f"업로드 파일: {uploaded_file.name}")
        st.info(f"파일 크기: {format_file_size(uploaded_file.size)}")
    else:
        st.caption("아직 업로드된 영상이 없습니다. 업로드 없이 실행하면 샘플 결과를 확인합니다.")

    if st.button("분석 시작", type="primary"):
        try:
            if uploaded_file is None:
                store_sample_result(build_sample_scene_vector())
            else:
                clear_previous_frames(FRAMES_DIR)
                video_path = save_uploaded_video(uploaded_file, INPUT_DIR)
                metadata = get_video_metadata(video_path)
                sample_frames = extract_sample_frames(video_path, FRAMES_DIR, sample_fps=SAMPLE_FPS, max_frames=MAX_SAMPLE_FRAMES)
                detector = create_object_detector(
                    backend=detector_backend,
                    model_path=yolo_model_path,
                    confidence_threshold=confidence_threshold,
                )
                frame_size = (int(metadata["width"]), int(metadata["height"]))
                (
                    scene_vectors,
                    overlay_items_by_frame,
                    light_diagnostics_by_frame,
                    motion_diagnostics_by_frame,
                    certainty_diagnostics_by_frame,
                ) = analyze_sample_frames(
                    sample_frames=sample_frames,
                    detector=detector,
                    frame_size=frame_size,
                    use_light_candidates=use_light_candidates,
                    light_brightness_threshold=light_brightness_threshold,
                    use_motion_assist=use_motion_assist,
                )
                store_video_result(
                    metadata=metadata,
                    sample_frames=sample_frames,
                    scene_vectors=scene_vectors,
                    overlay_items_by_frame=overlay_items_by_frame,
                    light_diagnostics_by_frame=light_diagnostics_by_frame,
                    motion_diagnostics_by_frame=motion_diagnostics_by_frame,
                    certainty_diagnostics_by_frame=certainty_diagnostics_by_frame,
                    detector_backend=detector_backend,
                )
        except Exception as exc:
            st.error(f"분석 중 오류가 발생했습니다: {exc}")

    render_analysis_result()


if __name__ == "__main__":
    main()
