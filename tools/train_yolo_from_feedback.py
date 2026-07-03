from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tools.export_yolo_dataset import export_yolo_dataset


def build_unique_archive_path(archive_root: Path, run_name: str) -> Path:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    archive_path = archive_root / f"{run_name}_{timestamp}"
    counter = 1
    while archive_path.exists():
        archive_path = archive_root / f"{run_name}_{timestamp}_{counter:02d}"
        counter += 1
    return archive_path


def archive_existing_run(project_dir: Path, run_name: str, enabled: bool = True) -> Path | None:
    run_dir = project_dir / run_name
    if not enabled or not run_dir.exists():
        return None

    archive_root = project_dir / "_archive"
    archive_root.mkdir(parents=True, exist_ok=True)
    archive_path = build_unique_archive_path(archive_root, run_name)
    shutil.move(str(run_dir), str(archive_path))
    return archive_path


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="라벨링 피드백으로 YOLO 모델을 fine-tuning합니다.")
    parser.add_argument("--feedback", default="data/output/label_feedback.jsonl", help="라벨링 피드백 JSONL 경로")
    parser.add_argument("--dataset-dir", default="data/yolo_dataset/blackbox_feedback_v1", help="YOLO 데이터셋 출력 폴더")
    parser.add_argument("--input-dir", default="data/input", help="누락 프레임 복구에 사용할 원본 영상 폴더")
    parser.add_argument("--model", default="yolov8n.pt", help="학습 시작점으로 사용할 YOLO 가중치")
    parser.add_argument("--epochs", type=int, default=30, help="학습 epoch 수")
    parser.add_argument("--imgsz", type=int, default=640, help="학습 이미지 크기")
    parser.add_argument("--batch", type=int, default=8, help="학습 batch 크기")
    parser.add_argument("--device", default=None, help="학습 장치. 예: 0, cpu")
    parser.add_argument("--project", default="data/models", help="YOLO 학습 모델 저장 폴더")
    parser.add_argument("--name", default="blackbox2vector_feedback_yolo_v1_5", help="YOLO 튜닝 모델 이름")
    parser.add_argument("--val-ratio", type=float, default=0.2, help="검증 데이터 비율")
    parser.add_argument("--seed", type=int, default=42, help="train/val 분할 seed")
    parser.add_argument("--export-only", action="store_true", help="데이터셋만 만들고 학습은 실행하지 않습니다.")
    parser.add_argument("--no-archive", action="store_true", help="기존 학습 결과 폴더를 아카이브하지 않고 덮어씁니다.")
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()
    summary = export_yolo_dataset(
        feedback_path=Path(args.feedback),
        output_dir=Path(args.dataset_dir),
        input_dir=Path(args.input_dir),
        val_ratio=args.val_ratio,
        seed=args.seed,
        include_negative_images=True,
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))

    if args.export_only:
        return

    try:
        from ultralytics import YOLO
    except ImportError as exc:
        raise ImportError("YOLO 학습을 실행하려면 ultralytics가 필요합니다. pip install -r requirements.txt를 실행하세요.") from exc

    project_dir = Path(args.project).resolve()
    archived_path = archive_existing_run(project_dir, args.name, enabled=not args.no_archive)
    if archived_path is not None:
        print(f"기존 학습 결과를 아카이브했습니다: {archived_path.as_posix()}")

    model = YOLO(args.model)
    train_kwargs = {
        "data": summary["data_yaml"],
        "epochs": args.epochs,
        "imgsz": args.imgsz,
        "batch": args.batch,
        "project": project_dir.as_posix(),
        "name": args.name,
        "exist_ok": True,
    }
    if args.device is not None:
        train_kwargs["device"] = args.device

    model.train(**train_kwargs)


if __name__ == "__main__":
    main()
