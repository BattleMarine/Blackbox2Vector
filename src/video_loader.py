from pathlib import Path
from typing import Any

import cv2


def save_uploaded_video(uploaded_file: Any, save_dir: str | Path) -> Path:
    """Streamlit 업로드 파일을 지정한 폴더에 저장한다."""
    if uploaded_file is None:
        raise ValueError("저장할 업로드 파일이 없습니다.")

    target_dir = Path(save_dir)
    target_dir.mkdir(parents=True, exist_ok=True)

    filename = Path(uploaded_file.name).name
    if not filename:
        raise ValueError("업로드 파일 이름을 확인할 수 없습니다.")

    video_path = target_dir / filename
    try:
        video_path.write_bytes(uploaded_file.getbuffer())
    except Exception as exc:
        raise RuntimeError(f"업로드 영상을 저장하지 못했습니다: {video_path}") from exc

    return video_path


def get_video_metadata(video_path: str | Path) -> dict[str, float | int]:
    """OpenCV로 영상 메타데이터를 읽는다."""
    path = Path(video_path)
    if not path.exists():
        raise FileNotFoundError(f"영상 파일이 존재하지 않습니다: {path}")

    capture = cv2.VideoCapture(str(path))
    if not capture.isOpened():
        capture.release()
        raise ValueError(f"OpenCV가 영상 파일을 열 수 없습니다: {path}")

    try:
        frame_count = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = float(capture.get(cv2.CAP_PROP_FPS))
        width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
    finally:
        capture.release()

    duration = frame_count / fps if fps > 0 else 0.0
    return {
        "frame_count": frame_count,
        "fps": fps,
        "width": width,
        "height": height,
        "duration_seconds": duration,
    }


def extract_sample_frames(
    video_path: str | Path,
    output_dir: str | Path,
    sample_fps: int = 1,
    max_frames: int | None = None,
) -> list[Path]:
    """지정한 초당 샘플 수에 맞춰 프레임 이미지를 추출한다."""
    if sample_fps <= 0:
        raise ValueError("sample_fps는 1 이상의 값이어야 합니다.")
    if max_frames is not None and max_frames <= 0:
        raise ValueError("max_frames는 1 이상의 값이거나 None이어야 합니다.")

    path = Path(video_path)
    if not path.exists():
        raise FileNotFoundError(f"영상 파일이 존재하지 않습니다: {path}")

    target_dir = Path(output_dir)
    target_dir.mkdir(parents=True, exist_ok=True)

    capture = cv2.VideoCapture(str(path))
    if not capture.isOpened():
        capture.release()
        raise ValueError(f"OpenCV가 영상 파일을 열 수 없습니다: {path}")

    fps = float(capture.get(cv2.CAP_PROP_FPS))
    if fps <= 0:
        capture.release()
        raise ValueError(f"영상 FPS를 확인할 수 없어 프레임을 추출할 수 없습니다: {path}")

    frame_interval = max(int(round(fps / sample_fps)), 1)
    saved_frames: list[Path] = []
    frame_index = 0

    try:
        while True:
            success, frame = capture.read()
            if not success:
                break

            if frame_index % frame_interval == 0:
                frame_path = target_dir / f"{path.stem}_frame_{frame_index:06d}.jpg"
                write_success = cv2.imwrite(str(frame_path), frame)
                if not write_success:
                    raise RuntimeError(f"프레임 이미지를 저장하지 못했습니다: {frame_path}")
                saved_frames.append(frame_path)
                if max_frames is not None and len(saved_frames) >= max_frames:
                    break

            frame_index += 1
    finally:
        capture.release()

    if not saved_frames:
        raise RuntimeError(f"추출된 프레임이 없습니다. 영상 내용을 확인해야 합니다: {path}")

    return saved_frames
