import sys
from typing import Any


SUPPORTED_YOLO_TYPES = {
    "person",
    "bicycle",
    "car",
    "motorcycle",
    "bus",
    "truck",
}


class ObjectDetector:
    """데모용 객체 검출 백엔드 인터페이스."""

    def __init__(
        self,
        backend: str = "dummy",
        model_path: str | None = None,
        confidence_threshold: float = 0.25,
    ):
        self.backend = backend
        self.model_path = model_path or "yolov8n.pt"
        self.confidence_threshold = confidence_threshold
        self.model = None

        if self.backend not in {"dummy", "yolo"}:
            raise ValueError(f"지원하지 않는 detector backend입니다: {self.backend}")

        if self.backend == "yolo":
            self.model = self._load_yolo_model()

    def detect_objects(self, frame: Any) -> list[dict[str, Any]]:
        """선택된 백엔드로 프레임에서 객체를 검출한다."""
        if frame is None:
            raise ValueError("객체 검출에 사용할 프레임이 없습니다.")

        if self.backend == "dummy":
            return self._detect_dummy(frame)
        if self.backend == "yolo":
            return self._detect_yolo(frame)

        raise ValueError(f"지원하지 않는 detector backend입니다: {self.backend}")

    def _load_yolo_model(self) -> Any:
        """Ultralytics YOLO 모델을 지연 로딩한다."""
        try:
            from ultralytics import YOLO
        except ImportError as exc:
            raise RuntimeError(
                "YOLO 백엔드를 사용하려면 ultralytics가 필요합니다. "
                f"현재 앱 실행 Python은 `{sys.executable}`입니다. "
                f"`{sys.executable} -m pip install ultralytics` 또는 "
                f"`{sys.executable} -m pip install -r requirements.txt`를 실행하세요."
            ) from exc

        try:
            return YOLO(self.model_path)
        except Exception as exc:
            raise RuntimeError(
                f"YOLO 모델을 불러오지 못했습니다: {self.model_path}. "
                "모델 파일 경로와 네트워크 연결 또는 로컬 가중치 존재 여부를 확인하세요."
            ) from exc

    def _detect_dummy(self, frame: Any) -> list[dict[str, Any]]:
        """파이프라인 검증을 위한 프레임 크기 기반 더미 detection을 생성한다."""
        frame_height, frame_width = frame.shape[:2]
        bbox_width = max(int(frame_width * 0.16), 40)
        bbox_height = max(int(frame_height * 0.13), 30)
        bbox_x = int((frame_width - bbox_width) / 2)
        bbox_y = int(frame_height * 0.55)

        # YOLO 없이도 전체 앱 흐름을 점검할 수 있도록 하나의 가상 차량을 만든다.
        return [
            {
                "track_id": 1,
                "type": "car",
                "subtype": None,
                "bbox_2d": [bbox_x, bbox_y, bbox_width, bbox_height],
                "confidence": 0.87,
                "detection_sources": ["dummy"],
                "detection_reason": "파이프라인 검증을 위한 프레임 크기 기반 가상 차량입니다.",
                "is_candidate": False,
            }
        ]

    def _detect_yolo(self, frame: Any) -> list[dict[str, Any]]:
        """Ultralytics YOLO 결과를 프로젝트 공통 detection 형식으로 변환한다."""
        if self.model is None:
            raise RuntimeError("YOLO 모델이 초기화되지 않았습니다.")

        results = self.model.predict(
            source=frame,
            conf=self.confidence_threshold,
            verbose=False,
        )
        if not results:
            return []

        result = results[0]
        names = result.names
        detections: list[dict[str, Any]] = []

        for box in result.boxes:
            class_id = int(box.cls[0])
            object_type = names.get(class_id, str(class_id))
            if object_type not in SUPPORTED_YOLO_TYPES:
                continue

            x1, y1, x2, y2 = [float(value) for value in box.xyxy[0].tolist()]
            width = max(x2 - x1, 1.0)
            height = max(y2 - y1, 1.0)
            confidence = float(box.conf[0])

            detections.append(
                {
                    "track_id": len(detections) + 1,
                    "type": object_type,
                    "subtype": None,
                    "bbox_2d": [
                        round(x1, 2),
                        round(y1, 2),
                        round(width, 2),
                        round(height, 2),
                    ],
                    "confidence": round(confidence, 4),
                    "detection_sources": ["yolo"],
                    "detection_reason": "Ultralytics YOLO 데모 백엔드가 객체 bbox를 반환했습니다.",
                    "is_candidate": False,
                }
            )

        return detections
