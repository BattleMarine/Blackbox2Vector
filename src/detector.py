from typing import Any


class ObjectDetector:
    """추후 Ultralytics YOLO 연결을 감싸기 위한 객체 검출 인터페이스."""

    def __init__(self, model_path: str | None = None):
        self.model_path = model_path
        self.model = None
        # 현재는 초기 UI와 JSON 구조 검증을 위한 더미 상태이다.
        # TODO: 추후 Ultralytics YOLO 모델 로딩으로 교체한다.

    def detect_objects(self, frame: Any) -> list[dict[str, Any]]:
        """프레임에서 객체를 검출한다."""
        if frame is None:
            raise ValueError("객체 검출에 사용할 프레임이 없습니다.")

        frame_height, frame_width = frame.shape[:2]
        bbox_width = max(int(frame_width * 0.16), 40)
        bbox_height = max(int(frame_height * 0.13), 30)
        bbox_x = int((frame_width - bbox_width) / 2)
        bbox_y = int(frame_height * 0.55)

        # 실제 YOLO가 연결되기 전까지 프레임 크기에 맞춘 더미 detection을 반환한다.
        return [
            {
                "track_id": 1,
                "type": "car",
                "bbox_2d": [bbox_x, bbox_y, bbox_width, bbox_height],
                "confidence": 0.87,
            }
        ]
