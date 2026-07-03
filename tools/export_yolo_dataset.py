from __future__ import annotations

import argparse
import json
import random
import shutil
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import cv2


CLASS_NAMES = ["car", "truck", "bus", "motorcycle", "bicycle", "person"]
POSITIVE_FEEDBACK_TYPES = {"TP", "FP"}
NEGATIVE_FEEDBACK_TYPES = {"TN", "FN"}
VIDEO_EXTENSIONS = [".mp4", ".MP4", ".avi", ".AVI", ".mov", ".MOV", ".mkv", ".MKV"]


@dataclass
class ExportStats:
    total_records: int = 0
    positive_records: int = 0
    negative_records: int = 0
    skipped_records: int = 0
    exported_images: int = 0
    train_images: int = 0
    val_images: int = 0
    labels_written: int = 0
    recovered_frames: int = 0
    missing_frames: int = 0
    invalid_boxes: int = 0
    snapshot_image_records: int = 0
    missing_snapshot_records: int = 0
    legacy_frame_records: int = 0


def load_feedback_records(feedback_path: Path) -> list[dict[str, Any]]:
    if not feedback_path.exists():
        raise FileNotFoundError(f"피드백 파일을 찾을 수 없습니다: {feedback_path}")

    records: list[dict[str, Any]] = []
    for line_number, line in enumerate(feedback_path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError as exc:
            raise ValueError(f"피드백 JSONL {line_number}번째 줄을 읽을 수 없습니다.") from exc
    return records


def parse_frame_name(frame_path: Path) -> tuple[str, int] | None:
    stem = frame_path.stem
    marker = "_frame_"
    if marker not in stem:
        return None
    video_stem, frame_index_text = stem.rsplit(marker, 1)
    try:
        return video_stem, int(frame_index_text)
    except ValueError:
        return None


def find_source_video(video_stem: str, input_dir: Path) -> Path | None:
    for extension in VIDEO_EXTENSIONS:
        candidate = input_dir / f"{video_stem}{extension}"
        if candidate.exists():
            return candidate
    return None


def recover_frame_from_video(video_path: Path, frame_index: int, target_path: Path) -> bool:
    capture = cv2.VideoCapture(str(video_path))
    if not capture.isOpened():
        capture.release()
        return False

    try:
        capture.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
        success, frame = capture.read()
        if not success:
            return False
        target_path.parent.mkdir(parents=True, exist_ok=True)
        return bool(cv2.imwrite(str(target_path), frame))
    finally:
        capture.release()


def normalize_bbox(bbox_2d: list[float], image_width: int, image_height: int) -> tuple[float, float, float, float] | None:
    x, y, width, height = [float(value) for value in bbox_2d]
    x1 = max(0.0, min(x, image_width - 1.0))
    y1 = max(0.0, min(y, image_height - 1.0))
    x2 = max(0.0, min(x + width, float(image_width)))
    y2 = max(0.0, min(y + height, float(image_height)))

    clipped_width = x2 - x1
    clipped_height = y2 - y1
    if clipped_width <= 1.0 or clipped_height <= 1.0:
        return None

    x_center = (x1 + clipped_width / 2.0) / image_width
    y_center = (y1 + clipped_height / 2.0) / image_height
    normalized_width = clipped_width / image_width
    normalized_height = clipped_height / image_height
    return x_center, y_center, normalized_width, normalized_height


def choose_split(frame_key: str, val_ratio: float, seed: int) -> str:
    randomizer = random.Random(f"{seed}:{frame_key}")
    return "val" if randomizer.random() < val_ratio else "train"


def get_record_image_path_text(record: dict[str, Any], stats: ExportStats | None = None) -> str | None:
    image_path = record.get("image_path")
    if image_path:
        if Path(str(image_path)).exists():
            if stats is not None:
                stats.snapshot_image_records += 1
            return str(image_path)
        if stats is not None:
            stats.missing_snapshot_records += 1

    frame_path = record.get("frame_path") or record.get("source_frame_path")
    if frame_path and stats is not None:
        stats.legacy_frame_records += 1
    return str(frame_path) if frame_path else None


def collect_records_by_frame(
    records: list[dict[str, Any]],
    include_negative_images: bool,
    stats: ExportStats | None = None,
) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        feedback_type = record.get("feedback_type")
        image_path = get_record_image_path_text(record, stats)
        if not image_path:
            continue
        if feedback_type in POSITIVE_FEEDBACK_TYPES:
            grouped[image_path].append(record)
        elif include_negative_images and feedback_type in NEGATIVE_FEEDBACK_TYPES:
            grouped[image_path].append(record)
    return dict(grouped)


def resolve_or_recover_frame(
    frame_path_text: str,
    input_dir: Path,
    recovered_dir: Path,
    stats: ExportStats,
) -> Path | None:
    frame_path = Path(frame_path_text)
    if frame_path.exists():
        return frame_path

    parsed = parse_frame_name(frame_path)
    if parsed is None:
        stats.missing_frames += 1
        return None

    video_stem, frame_index = parsed
    source_video = find_source_video(video_stem, input_dir)
    if source_video is None:
        stats.missing_frames += 1
        return None

    recovered_path = recovered_dir / frame_path.name
    if recovered_path.exists():
        return recovered_path

    if recover_frame_from_video(source_video, frame_index, recovered_path):
        stats.recovered_frames += 1
        return recovered_path

    stats.missing_frames += 1
    return None


def write_data_yaml(dataset_dir: Path, class_names: list[str]) -> Path:
    data_yaml = dataset_dir / "data.yaml"
    names = "\n".join(f"  {index}: {name}" for index, name in enumerate(class_names))
    data_yaml.write_text(
        "\n".join(
            [
                f"path: {dataset_dir.resolve().as_posix()}",
                "train: images/train",
                "val: images/val",
                f"nc: {len(class_names)}",
                "names:",
                names,
                "",
            ]
        ),
        encoding="utf-8",
    )
    return data_yaml


def export_yolo_dataset(
    feedback_path: Path,
    output_dir: Path,
    input_dir: Path,
    val_ratio: float = 0.2,
    seed: int = 42,
    include_negative_images: bool = True,
) -> dict[str, Any]:
    if not (0.0 <= val_ratio < 1.0):
        raise ValueError("val_ratio는 0.0 이상 1.0 미만이어야 합니다.")

    records = load_feedback_records(feedback_path)
    stats = ExportStats(total_records=len(records))
    grouped = collect_records_by_frame(records, include_negative_images, stats)
    class_to_id = {class_name: index for index, class_name in enumerate(CLASS_NAMES)}

    recovered_dir = output_dir / "_recovered_frames"
    for split in ["train", "val"]:
        (output_dir / "images" / split).mkdir(parents=True, exist_ok=True)
        (output_dir / "labels" / split).mkdir(parents=True, exist_ok=True)

    for frame_path_text, frame_records in sorted(grouped.items()):
        source_frame = resolve_or_recover_frame(frame_path_text, input_dir, recovered_dir, stats)
        if source_frame is None:
            stats.skipped_records += len(frame_records)
            continue

        image = cv2.imread(str(source_frame))
        if image is None:
            stats.missing_frames += 1
            stats.skipped_records += len(frame_records)
            continue

        image_height, image_width = image.shape[:2]
        split = choose_split(frame_path_text, val_ratio, seed)
        target_image = output_dir / "images" / split / source_frame.name
        target_label = output_dir / "labels" / split / f"{source_frame.stem}.txt"

        if not target_image.exists():
            shutil.copy2(source_frame, target_image)
            stats.exported_images += 1
            if split == "train":
                stats.train_images += 1
            else:
                stats.val_images += 1

        label_lines: list[str] = []
        seen_labels: set[tuple[int, str]] = set()
        for record in frame_records:
            feedback_type = record.get("feedback_type")
            if feedback_type in NEGATIVE_FEEDBACK_TYPES:
                stats.negative_records += 1
                continue
            if feedback_type not in POSITIVE_FEEDBACK_TYPES:
                stats.skipped_records += 1
                continue

            class_name = str(record.get("corrected_tag") or "").strip()
            if class_name not in class_to_id:
                stats.skipped_records += 1
                continue

            bbox_2d = record.get("bbox_2d")
            if not isinstance(bbox_2d, list) or len(bbox_2d) != 4:
                stats.invalid_boxes += 1
                stats.skipped_records += 1
                continue

            normalized_bbox = normalize_bbox(bbox_2d, image_width, image_height)
            if normalized_bbox is None:
                stats.invalid_boxes += 1
                stats.skipped_records += 1
                continue

            class_id = class_to_id[class_name]
            bbox_text = " ".join(f"{value:.6f}" for value in normalized_bbox)
            label_key = (class_id, bbox_text)
            if label_key in seen_labels:
                continue

            seen_labels.add(label_key)
            label_lines.append(f"{class_id} {bbox_text}")
            stats.positive_records += 1
            stats.labels_written += 1

        target_label.write_text("\n".join(label_lines) + ("\n" if label_lines else ""), encoding="utf-8")

    data_yaml = write_data_yaml(output_dir, CLASS_NAMES)
    summary = {
        "feedback_path": feedback_path.as_posix(),
        "output_dir": output_dir.as_posix(),
        "data_yaml": data_yaml.as_posix(),
        "classes": CLASS_NAMES,
        "stats": stats.__dict__,
        "positive_feedback_types": sorted(POSITIVE_FEEDBACK_TYPES),
        "negative_feedback_types": sorted(NEGATIVE_FEEDBACK_TYPES),
        "include_negative_images": include_negative_images,
        "image_source_priority": ["image_path", "frame_path", "source_frame_path", "data/input video recovery"],
    }
    (output_dir / "export_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return summary


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="라벨링 피드백 JSONL을 YOLO 학습 데이터셋으로 변환합니다.")
    parser.add_argument("--feedback", default="data/output/label_feedback.jsonl", help="라벨링 피드백 JSONL 경로")
    parser.add_argument("--output", default="data/yolo_dataset/blackbox_feedback_v1", help="YOLO 데이터셋 출력 폴더")
    parser.add_argument("--input-dir", default="data/input", help="누락 프레임 복구에 사용할 원본 영상 폴더")
    parser.add_argument("--val-ratio", type=float, default=0.2, help="검증 데이터 비율")
    parser.add_argument("--seed", type=int, default=42, help="train/val 분할 seed")
    parser.add_argument("--no-negative-images", action="store_true", help="TN/FN만 있는 이미지를 빈 라벨 이미지로 내보내지 않습니다.")
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()
    summary = export_yolo_dataset(
        feedback_path=Path(args.feedback),
        output_dir=Path(args.output),
        input_dir=Path(args.input_dir),
        val_ratio=args.val_ratio,
        seed=args.seed,
        include_negative_images=not args.no_negative_images,
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
