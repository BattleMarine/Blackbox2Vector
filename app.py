import hashlib
import io
import json
import sys
from importlib import import_module, reload
from importlib.util import find_spec
from pathlib import Path
from typing import Any

import cv2
import streamlit as st
from PIL import Image

try:
    from streamlit_drawable_canvas import st_canvas
except ImportError:
    st_canvas = None


def patch_drawable_canvas_image_to_url() -> None:
    """최신 Streamlit에서 제거된 내부 함수를 캔버스 라이브러리용으로 보강합니다."""
    if st_canvas is None:
        return

    try:
        import streamlit.elements.image as st_image
        from streamlit.runtime import get_instance
    except Exception:
        return

    if hasattr(st_image, "image_to_url"):
        return

    def image_to_url(
        image,
        width=None,
        clamp=False,
        channels="RGB",
        output_format="PNG",
        image_id="drawable-canvas-bg",
    ):
        # streamlit-drawable-canvas가 Streamlit의 비공개 API에 의존하므로,
        # 앱 내부에서 필요한 배경 이미지 URL 생성 기능만 최소 범위로 복원합니다.
        del width, clamp
        if channels == "RGB" and getattr(image, "mode", None) != "RGB":
            image = image.convert("RGB")

        buffer = io.BytesIO()
        image.save(buffer, format=output_format)
        mimetype = f"image/{output_format.lower()}"
        return get_instance().media_file_mgr.add(
            buffer.getvalue(),
            mimetype,
            str(image_id or "drawable-canvas-bg"),
        )

    st_image.image_to_url = image_to_url


patch_drawable_canvas_image_to_url()

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
LABEL_FEEDBACK_PATH = OUTPUT_DIR / "label_feedback.jsonl"
YOLO_DEFAULT_MODEL = "yolov8n.pt"
SAMPLE_FPS = 1
MAX_SAMPLE_FRAMES = 12
OBJECT_CLASSES = ["car", "truck", "bus", "motorcycle", "bicycle", "person"]
NEGATIVE_TAGS = ["false_positive", "streetlight", "sign_light", "windshield_drop", "road_reflection", "hood_reflection", "other"]
FEEDBACK_DEFINITIONS = {
    "TP": "True Positive: 맞다고 분류했고 실제로 맞음",
    "TN": "True Negative: 맞다고 분류했지만 실제로는 아님",
    "FP": "False Positive: 아니라고 분류했지만 실제로는 맞음",
    "FN": "False Negative: 아니라고 분류했고 실제로도 아님",
}


def format_file_size(byte_size: int) -> str:
    if byte_size < 1024:
        return f"{byte_size} B"
    if byte_size < 1024 * 1024:
        return f"{byte_size / 1024:.1f} KB"
    return f"{byte_size / (1024 * 1024):.1f} MB"


def clear_previous_frames(frames_dir: Path) -> None:
    frames_dir.mkdir(parents=True, exist_ok=True)
    for frame_path in frames_dir.glob("*.jpg"):
        frame_path.unlink()


def save_json_data(data: dict | list, output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return output_path


def append_jsonl(record: dict[str, Any], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("a", encoding="utf-8") as file:
        file.write(json.dumps(record, ensure_ascii=False) + "\n")


def load_frame_rgb(frame_path: Path):
    frame_bgr = cv2.imread(str(frame_path))
    if frame_bgr is None:
        raise ValueError(f"프레임 이미지를 읽을 수 없습니다: {frame_path}")
    return frame_bgr, cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)


def show_video_metadata(metadata: dict[str, float | int]) -> None:
    st.markdown("### 영상 메타데이터")
    cols = st.columns(4)
    cols[0].metric("해상도", f"{metadata['width']} x {metadata['height']}")
    cols[1].metric("FPS", f"{metadata['fps']:.2f}")
    cols[2].metric("프레임 수", f"{metadata['frame_count']}")
    cols[3].metric("길이", f"{metadata['duration_seconds']:.2f}초")


def show_detector_settings() -> tuple[str, str, float, bool, int, bool]:
    st.sidebar.header("검출 설정")
    backend_label = st.sidebar.radio("검출 백엔드", ["더미 detector", "YOLO detector"])
    backend = "yolo" if backend_label == "YOLO detector" else "dummy"
    model_path = st.sidebar.text_input("YOLO 모델 경로", value=YOLO_DEFAULT_MODEL)
    confidence_threshold = st.sidebar.slider("YOLO 추론 신뢰도 기준", 0.05, 0.90, 0.25, 0.05)
    use_light_candidates = st.sidebar.checkbox("밝은 영역 evidence 수집", value=True)
    light_brightness_threshold = st.sidebar.slider("밝은 영역 기준", 180, 255, 220, 5)
    use_motion_assist = st.sidebar.checkbox("프레임 움직임 evidence 수집", value=True)
    return backend, model_path, confidence_threshold, use_light_candidates, light_brightness_threshold, use_motion_assist


def show_runtime_status() -> None:
    st.sidebar.header("실행 환경")
    st.sidebar.code(sys.executable, language="text")
    if find_spec("ultralytics") is None:
        st.sidebar.warning("현재 Python에서 ultralytics를 찾을 수 없습니다.")
    else:
        st.sidebar.success("ultralytics 설치 확인")
    if st_canvas is None:
        st.sidebar.warning("박스 클릭/드래그에는 streamlit-drawable-canvas가 필요합니다.")
    else:
        st.sidebar.success("canvas 라벨링 설치 확인")


def create_object_detector(backend: str, model_path: str, confidence_threshold: float):
    detector_module = reload(import_module("src.detector"))
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
        motion_diagnostics: dict = {"verified_count": 0, "motion_candidate_count": 0, "rejected_count": 0, "rejected_by_reason": {}}
        if use_motion_assist and previous_frame_bgr is not None:
            model_detections, verification_diagnostics = annotate_detections_with_motion(model_detections, previous_frame_bgr, frame_bgr)
            motion_candidates, candidate_diagnostics = extract_motion_candidates(previous_frame_bgr, frame_bgr)
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
        scene_vector = build_scene_vector(
            frame_index=frame_order,
            timestamp=round((frame_order - 1) / SAMPLE_FPS, 2),
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


def build_video_analysis_result(uploaded_file, detector_settings: tuple[str, str, float, bool, int, bool]) -> dict[str, Any]:
    backend, model_path, confidence_threshold, use_light_candidates, light_threshold, use_motion_assist = detector_settings
    clear_previous_frames(FRAMES_DIR)
    video_path = save_uploaded_video(uploaded_file, INPUT_DIR)
    metadata = get_video_metadata(video_path)
    sample_frames = extract_sample_frames(video_path, FRAMES_DIR, sample_fps=SAMPLE_FPS, max_frames=MAX_SAMPLE_FRAMES)
    detector = create_object_detector(backend, model_path, confidence_threshold)
    frame_size = (int(metadata["width"]), int(metadata["height"]))
    scene_vectors, overlay_items_by_frame, light_diag, motion_diag, certainty_diag = analyze_sample_frames(
        sample_frames,
        detector,
        frame_size,
        use_light_candidates,
        light_threshold,
        use_motion_assist,
    )
    return {
        "metadata": metadata,
        "frame_paths": [str(path) for path in sample_frames],
        "scene_vectors": scene_vectors,
        "overlay_items_by_frame": overlay_items_by_frame,
        "light_diagnostics_by_frame": light_diag,
        "motion_diagnostics_by_frame": motion_diag,
        "certainty_diagnostics_by_frame": certainty_diag,
        "detector_backend": backend,
    }


def store_video_result(result: dict[str, Any]) -> None:
    save_json_data(result["scene_vectors"][0], SCENE_VECTOR_PATH)
    save_json_data(result["scene_vectors"], SCENE_VECTOR_SEQUENCE_PATH)
    st.session_state["analysis_result"] = {"mode": "video", **result}


def get_selected_frame(result: dict[str, Any], slider_key: str):
    frame_paths = [Path(path) for path in result["frame_paths"]]
    selected_frame_number = st.slider("프레임 선택", min_value=1, max_value=len(frame_paths), value=1, format="프레임 %d", key=slider_key)
    selected_index = selected_frame_number - 1
    return selected_index, frame_paths[selected_index]


def render_video_result(result: dict[str, Any]) -> None:
    show_video_metadata(result["metadata"])
    selected_index, frame_path = get_selected_frame(result, "analysis_frame_slider")
    scene_vector = result["scene_vectors"][selected_index]
    overlay_items = result["overlay_items_by_frame"][selected_index]
    frame_bgr, frame_rgb = load_frame_rgb(frame_path)
    overlay_rgb = cv2.cvtColor(draw_detection_overlay(frame_bgr, overlay_items), cv2.COLOR_BGR2RGB)

    st.write(summarize_scene(scene_vector))
    cols = st.columns(2)
    with cols[0]:
        st.image(frame_rgb, caption="원본 프레임")
    with cols[1]:
        st.image(overlay_rgb, caption="분석 박스")
    left, right = st.columns([1, 1])
    with left:
        st.markdown("### Scene Vector JSON")
        st.json(scene_vector)
    with right:
        st.markdown("### 2.5D 탑뷰")
        st.pyplot(draw_top_view(scene_vector))


def build_label_record(
    frame_index: int,
    frame_path: Path,
    feedback_type: str,
    bbox_2d: list[float],
    original_item: dict[str, Any] | None = None,
    corrected_tag: str | None = None,
    note: str = "",
) -> dict[str, Any]:
    if feedback_type not in FEEDBACK_DEFINITIONS:
        raise ValueError(f"지원하지 않는 피드백 타입입니다: {feedback_type}")
    return {
        "frame_index": frame_index,
        "frame_path": frame_path.as_posix(),
        "feedback_type": feedback_type,
        "feedback_meaning": FEEDBACK_DEFINITIONS[feedback_type],
        "bbox_2d": [round(float(value), 2) for value in bbox_2d],
        "original_item": original_item,
        "corrected_tag": corrected_tag,
        "note": note,
    }


def get_display_image(image_rgb, max_width: int = 1100):
    height, width = image_rgb.shape[:2]
    display_width = min(max_width, width)
    scale = display_width / width
    display_height = int(height * scale)
    return cv2.resize(image_rgb, (display_width, display_height)), scale, display_width, display_height


def build_canvas_key(prefix: str, selected_index: int, frame_path: Path, image_rgb) -> str:
    """프레임이 바뀌면 캔버스 컴포넌트도 새로 mount되도록 안정적인 key를 만듭니다."""
    image_hash = hashlib.md5(image_rgb.tobytes()).hexdigest()[:12]
    return f"{prefix}_{selected_index}_{frame_path.stem}_{image_hash}"


def get_last_canvas_point(canvas_result, scale: float) -> tuple[float, float] | None:
    objects = canvas_result.json_data.get("objects", []) if canvas_result and canvas_result.json_data else []
    if not objects:
        return None
    point = objects[-1]
    radius = float(point.get("radius", 0))
    x = (float(point.get("left", 0)) + radius) / scale
    y = (float(point.get("top", 0)) + radius) / scale
    return x, y


def find_item_at_point(items: list[dict[str, Any]], point: tuple[float, float] | None) -> dict[str, Any] | None:
    if point is None:
        return None
    x, y = point
    matches = []
    for item in items:
        bx, by, bw, bh = [float(value) for value in item["bbox_2d"]]
        if bx <= x <= bx + bw and by <= y <= by + bh:
            matches.append((bw * bh, item))
    if not matches:
        return None
    return sorted(matches, key=lambda pair: pair[0])[0][1]


def save_feedback_record(record: dict[str, Any], success_message: str) -> None:
    append_jsonl(record, LABEL_FEEDBACK_PATH)
    st.success(f"{success_message}: {LABEL_FEEDBACK_PATH.as_posix()}")


def render_existing_box_feedback_panel(selected_index: int, frame_path: Path, selected_item: dict[str, Any] | None) -> None:
    st.markdown("#### 피드백 패널")
    st.caption("기존 박스는 모델이 맞다고 분류한 결과입니다.")
    if selected_item is None:
        st.info("왼쪽 캔버스에서 평가할 박스를 클릭하세요.")
        return

    st.success(f"선택: {selected_item.get('visual_layer')} / {selected_item.get('type')} / {selected_item.get('confidence', 0.0):.2f}")
    feedback_type = st.radio(
        "판정",
        ["TP - 정답", "TN - 오분류/오탐"],
        horizontal=False,
        key=f"clicked_feedback_type_{selected_index}",
    )
    corrected_tag = (
        st.selectbox("확정 객체 태그", OBJECT_CLASSES, key=f"clicked_positive_tag_{selected_index}")
        if feedback_type.startswith("TP")
        else st.selectbox("오분류 사유 또는 실제 태그", NEGATIVE_TAGS + OBJECT_CLASSES, key=f"clicked_negative_tag_{selected_index}")
    )
    note = st.text_area("메모", key=f"clicked_note_{selected_index}", height=80)
    if st.button("기존 박스 평가 저장", key=f"save_clicked_feedback_{selected_index}", use_container_width=True):
        feedback_code = feedback_type.split(" - ")[0]
        save_feedback_record(
            build_label_record(
                frame_index=selected_index + 1,
                frame_path=frame_path,
                feedback_type=feedback_code,
                bbox_2d=selected_item["bbox_2d"],
                original_item=selected_item,
                corrected_tag=corrected_tag,
                note=note,
            ),
            f"{feedback_code} 피드백을 저장했습니다",
        )


def render_click_feedback(selected_index: int, frame_path: Path, overlay_items: list[dict[str, Any]]) -> None:
    st.markdown("### 기존 박스 평가")
    st.caption("왼쪽 캔버스에서 박스를 클릭하면 오른쪽 패널에서 TP/TN 판정을 저장합니다. 저장하지 않은 기존 박스는 TP로 간주합니다.")
    if st_canvas is None:
        st.warning("현재 Streamlit 실행 Python에서 canvas 라이브러리를 찾지 못했습니다. 서버를 재시작해 주세요.")
        return

    frame_bgr, _ = load_frame_rgb(frame_path)
    overlay_rgb = cv2.cvtColor(draw_detection_overlay(frame_bgr, overlay_items), cv2.COLOR_BGR2RGB)
    display_image, scale, display_width, display_height = get_display_image(overlay_rgb)
    canvas_col, panel_col = st.columns([3, 1])
    with canvas_col:
        click_canvas = st_canvas(
            fill_color="rgba(255, 0, 255, 0.35)",
            stroke_width=2,
            stroke_color="#ff00ff",
            background_image=Image.fromarray(display_image),
            update_streamlit=True,
            height=display_height,
            width=display_width,
            drawing_mode="point",
            key=build_canvas_key("select_box_canvas", selected_index, frame_path, display_image),
        )
    selected_item = find_item_at_point(overlay_items, get_last_canvas_point(click_canvas, scale))
    with panel_col:
        render_existing_box_feedback_panel(selected_index, frame_path, selected_item)


def get_last_canvas_rect(canvas_result, scale: float) -> list[float] | None:
    objects = canvas_result.json_data.get("objects", []) if canvas_result and canvas_result.json_data else []
    rects = [obj for obj in objects if obj.get("type") == "rect"]
    if not rects:
        return None
    rect = rects[-1]
    return [
        float(rect.get("left", 0)) / scale,
        float(rect.get("top", 0)) / scale,
        float(rect.get("width", 0)) * float(rect.get("scaleX", 1)) / scale,
        float(rect.get("height", 0)) * float(rect.get("scaleY", 1)) / scale,
    ]


def render_new_box_feedback_panel(selected_index: int, frame_path: Path, bbox_2d: list[float] | None) -> None:
    st.markdown("#### 피드백 패널")
    st.caption("새 박스는 모델이 아니라고 본 영역에 대한 평가입니다.")
    if bbox_2d is None:
        st.info("왼쪽 캔버스에서 새 박스를 드래그하세요.")
        return

    st.success(f"새 박스: {[round(value, 1) for value in bbox_2d]}")
    feedback_type = st.radio(
        "판정",
        ["FP - 미분류 객체", "FN - 정상 미검출/비객체"],
        horizontal=False,
        key=f"draw_feedback_type_{selected_index}",
    )
    corrected_tag = (
        st.selectbox("미분류 객체 태그", OBJECT_CLASSES, index=0, key=f"fp_tag_{selected_index}")
        if feedback_type.startswith("FP")
        else st.selectbox("비객체 사유", NEGATIVE_TAGS, key=f"fn_negative_tag_{selected_index}")
    )
    note = st.text_area("새 박스 메모", key=f"draw_note_{selected_index}", height=80)
    if st.button("새 박스 평가 저장", key=f"save_draw_feedback_{selected_index}", use_container_width=True):
        feedback_code = feedback_type.split(" - ")[0]
        save_feedback_record(
            build_label_record(
                frame_index=selected_index + 1,
                frame_path=frame_path,
                feedback_type=feedback_code,
                bbox_2d=bbox_2d,
                corrected_tag=corrected_tag,
                note=note,
            ),
            f"{feedback_code} 피드백을 저장했습니다",
        )


def render_drag_feedback(selected_index: int, frame_path: Path, overlay_rgb) -> None:
    st.markdown("### 새 박스 평가")
    st.caption("왼쪽 캔버스에서 누락 객체나 비객체 영역을 드래그하면 오른쪽 패널에서 FP/FN 판정을 저장합니다.")
    if st_canvas is None:
        return

    display_image, scale, display_width, display_height = get_display_image(overlay_rgb)
    canvas_col, panel_col = st.columns([3, 1])
    with canvas_col:
        canvas_result = st_canvas(
            fill_color="rgba(255, 165, 0, 0.20)",
            stroke_width=2,
            stroke_color="#ff9900",
            background_image=Image.fromarray(display_image),
            update_streamlit=True,
            height=display_height,
            width=display_width,
            drawing_mode="rect",
            key=build_canvas_key("drag_box_canvas", selected_index, frame_path, display_image),
        )
    with panel_col:
        render_new_box_feedback_panel(selected_index, frame_path, get_last_canvas_rect(canvas_result, scale))


def render_labeling_admin(result: dict[str, Any]) -> None:
    st.markdown("## 라벨링 관리자")
    st.caption("피드백 타입은 TP, TN, FP, FN 네 가지로 저장합니다. 기존 박스는 클릭하고, 누락 객체는 새 박스로 드래그하세요.")
    with st.expander("피드백 타입 정의", expanded=False):
        for code, meaning in FEEDBACK_DEFINITIONS.items():
            st.write(f"- `{code}`: {meaning}")
    selected_index, frame_path = get_selected_frame(result, "labeling_frame_slider")
    overlay_items = result["overlay_items_by_frame"][selected_index]
    frame_bgr, frame_rgb = load_frame_rgb(frame_path)
    overlay_rgb = cv2.cvtColor(draw_detection_overlay(frame_bgr, overlay_items), cv2.COLOR_BGR2RGB)

    cols = st.columns(2)
    with cols[0]:
        st.image(frame_rgb, caption="원본 프레임")
    with cols[1]:
        st.image(overlay_rgb, caption="분석 박스")

    feedback_mode = st.radio(
        "평가 작업",
        ["기존 박스 평가", "새 박스 평가"],
        horizontal=True,
        key=f"feedback_mode_{selected_index}_{frame_path.stem}",
        help="캔버스 배경 이미지 로딩 충돌을 줄이기 위해 한 번에 하나의 평가 캔버스만 표시합니다.",
    )
    if feedback_mode == "기존 박스 평가":
        render_click_feedback(selected_index, frame_path, overlay_items)
    else:
        render_drag_feedback(selected_index, frame_path, overlay_rgb)

    if LABEL_FEEDBACK_PATH.exists():
        st.download_button(
            "누적 피드백 JSONL 다운로드",
            data=LABEL_FEEDBACK_PATH.read_text(encoding="utf-8"),
            file_name="label_feedback.jsonl",
            mime="application/jsonl",
        )


def render_analysis_result() -> None:
    result = st.session_state.get("analysis_result")
    if result and result["mode"] == "video":
        render_video_result(result)
    elif result and result["mode"] == "sample":
        render_video_result(result["scene_vector"])


def render_analysis_page(uploaded_file, detector_settings) -> None:
    if st.button("분석 시작", type="primary"):
        try:
            if uploaded_file is None:
                scene_vector = build_sample_scene_vector()
                save_json_data(scene_vector, SCENE_VECTOR_PATH)
                st.session_state["analysis_result"] = {"mode": "sample", "scene_vector": scene_vector}
                st.json(scene_vector)
            else:
                result = build_video_analysis_result(uploaded_file, detector_settings)
                store_video_result(result)
        except Exception as exc:
            st.error(f"분석 중 오류가 발생했습니다: {exc}")
    result = st.session_state.get("analysis_result")
    if result and result["mode"] == "video":
        render_video_result(result)


def render_labeling_page(uploaded_file, detector_settings) -> None:
    if st.button("라벨링용 분석 시작", type="primary"):
        if uploaded_file is None:
            st.warning("라벨링 관리자 페이지에서는 영상을 업로드해야 합니다.")
            return
        try:
            st.session_state["labeling_result"] = build_video_analysis_result(uploaded_file, detector_settings)
        except Exception as exc:
            st.error(f"라벨링용 분석 중 오류가 발생했습니다: {exc}")
    result = st.session_state.get("labeling_result")
    if result is not None:
        render_labeling_admin(result)


def main() -> None:
    st.set_page_config(page_title="BlackBox2Vector", layout="wide")
    st.title("BlackBox2Vector")
    st.subheader("2D 블랙박스 영상에서 Scene Vector JSON과 학습 피드백으로")
    st.write("v1.5 라벨링 관리자는 박스 클릭 피드백과 드래그 박스 피드백을 지원합니다.")

    page_mode = st.sidebar.radio("화면 선택", ["분석 데모", "라벨링 관리자"])
    detector_settings = show_detector_settings()
    show_runtime_status()
    uploaded_file = st.file_uploader("블랙박스 영상 업로드", type=["mp4", "avi", "mov", "mkv"], accept_multiple_files=False)
    if uploaded_file:
        st.info(f"업로드 파일: {uploaded_file.name}")
        st.info(f"파일 크기: {format_file_size(uploaded_file.size)}")

    if page_mode == "분석 데모":
        render_analysis_page(uploaded_file, detector_settings)
    else:
        render_labeling_page(uploaded_file, detector_settings)


if __name__ == "__main__":
    main()
