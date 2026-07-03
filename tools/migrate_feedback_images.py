from __future__ import annotations

import argparse
import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

import cv2


VIDEO_EXTENSIONS = [".mp4", ".MP4", ".avi", ".AVI", ".mov", ".MOV", ".mkv", ".MKV"]


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(f"피드백 파일을 찾을 수 없습니다: {path}")

    records: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError as exc:
            raise ValueError(f"피드백 JSONL {line_number}번째 줄을 읽을 수 없습니다.") from exc
    return records


def parse_frame_name(frame_path: Path) -> tuple[str, int] | None:
    marker = "_frame_"
    stem = frame_path.stem
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


def build_snapshot_path(frame_path: Path, image_dir: Path) -> Path:
    parsed = parse_frame_name(frame_path)
    if parsed is None:
        safe_stem = frame_path.stem
    else:
        video_stem, frame_index = parsed
        safe_stem = f"{video_stem}_frame_{frame_index:06d}"
    return image_dir / f"{safe_stem}.jpg"


def ensure_feedback_image(frame_path_text: str, input_dir: Path, image_dir: Path) -> Path | None:
    frame_path = Path(frame_path_text)
    snapshot_path = build_snapshot_path(frame_path, image_dir)
    if snapshot_path.exists():
        return snapshot_path

    if frame_path.exists():
        image_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(frame_path, snapshot_path)
        return snapshot_path

    parsed = parse_frame_name(frame_path)
    if parsed is None:
        return None

    video_stem, frame_index = parsed
    source_video = find_source_video(video_stem, input_dir)
    if source_video is None:
        return None

    if recover_frame_from_video(source_video, frame_index, snapshot_path):
        return snapshot_path
    return None


def write_jsonl(records: list[dict[str, Any]], path: Path) -> None:
    path.write_text(
        "\n".join(json.dumps(record, ensure_ascii=False) for record in records) + "\n",
        encoding="utf-8",
    )


def migrate_feedback_images(feedback_path: Path, input_dir: Path, image_dir: Path, dry_run: bool = False) -> dict[str, Any]:
    records = load_jsonl(feedback_path)
    backup_path = feedback_path.with_suffix(f".jsonl.bak_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
    stats = {
        "total_records": len(records),
        "already_has_image_path": 0,
        "migrated_records": 0,
        "failed_records": 0,
        "backup_path": backup_path.as_posix(),
        "dry_run": dry_run,
    }

    changed_records: list[dict[str, Any]] = []
    for record in records:
        updated = dict(record)
        image_path = updated.get("image_path")
        if image_path and Path(str(image_path)).exists():
            stats["already_has_image_path"] += 1
            changed_records.append(updated)
            continue

        frame_path = updated.get("frame_path") or updated.get("source_frame_path")
        if not frame_path:
            stats["failed_records"] += 1
            changed_records.append(updated)
            continue

        snapshot_path = ensure_feedback_image(str(frame_path), input_dir, image_dir)
        if snapshot_path is None:
            stats["failed_records"] += 1
            changed_records.append(updated)
            continue

        updated.setdefault("source_frame_path", str(frame_path))
        updated["image_path"] = snapshot_path.as_posix()
        stats["migrated_records"] += 1
        changed_records.append(updated)

    if not dry_run:
        shutil.copy2(feedback_path, backup_path)
        write_jsonl(changed_records, feedback_path)

    return stats


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="구버전 피드백 record에 프레임 이미지 스냅샷 경로를 채웁니다.")
    parser.add_argument("--feedback", default="data/output/label_feedback.jsonl", help="피드백 JSONL 경로")
    parser.add_argument("--input-dir", default="data/input", help="원본 영상 폴더")
    parser.add_argument("--image-dir", default="data/feedback/images", help="피드백 이미지 스냅샷 폴더")
    parser.add_argument("--dry-run", action="store_true", help="파일을 수정하지 않고 통계만 확인합니다.")
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()
    stats = migrate_feedback_images(
        feedback_path=Path(args.feedback),
        input_dir=Path(args.input_dir),
        image_dir=Path(args.image_dir),
        dry_run=args.dry_run,
    )
    print(json.dumps(stats, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
