from typing import Any

from src.position_estimator import estimate_position_3d


def classify_distance_zone(distance_y: float) -> str:
    """전방 거리 추정값을 가까움, 중간, 멂으로 단순 분류한다."""
    if distance_y < 10:
        return "near"
    if distance_y < 30:
        return "mid"
    return "far"


def classify_lane_position(position_x: float) -> str:
    """x 위치 추정값으로 객체의 대략적인 차로 위치를 분류한다."""
    if position_x < -1.5:
        return "left_front"
    if position_x > 1.5:
        return "right_front"
    return "center_front"


def build_scene_vector(
    frame_index: int,
    timestamp: float,
    detections: list[dict[str, Any]],
    frame_size: tuple[int, int],
) -> dict[str, Any]:
    """검출 결과를 Scene Vector JSON 구조로 변환한다."""
    frame_width, frame_height = frame_size
    objects = []

    for detection in detections:
        bbox_2d = detection["bbox_2d"]
        object_type = detection.get("type", "unknown")
        motion_score = float(detection.get("motion_score", 0.0))
        position_3d = estimate_position_3d(bbox_2d, frame_width, frame_height, object_type)
        estimated_x, estimated_y, _ = position_3d["estimate"]

        objects.append(
            {
                "track_id": detection.get("track_id"),
                "type": object_type,
                "subtype": detection.get("subtype"),
                "bbox_2d": bbox_2d,
                "confidence": detection.get("confidence", 0.0),
                "motion_score": round(motion_score, 4),
                "detection_sources": detection.get("detection_sources", ["unknown"]),
                "detection_reason": detection.get("detection_reason", "검출 근거가 기록되지 않았습니다."),
                "is_candidate": detection.get("is_candidate", False),
                "position_3d": position_3d,
                "motion_vector_3d": {
                    "vx": 0.0,
                    "vy": 0.0,
                    "vz": 0.0,
                    "confidence": round(min(motion_score, 1.0), 4),
                },
                "state": {
                    "distance_zone": classify_distance_zone(float(estimated_y)),
                    "lane_position": classify_lane_position(float(estimated_x)),
                    "motion_state": "moving_candidate" if motion_score >= 0.08 else "unknown",
                },
            }
        )

    return {
        "scene_id": f"clip_001_frame_{frame_index:04d}",
        "timestamp": timestamp,
        "coordinate_system": {
            "origin": "ego_vehicle",
            "axis": {
                "x": "right",
                "y": "forward",
                "z": "up",
            },
            "unit": "meter_estimated",
        },
        "ego_vehicle": {
            "position_3d": [0.0, 0.0, 0.0],
            "heading": [0.0, 1.0, 0.0],
            "speed": None,
        },
        "objects": objects,
        "events": [],
    }


def build_sample_scene_vector() -> dict[str, Any]:
    """앱 초기 화면 검증에 사용할 샘플 Scene Vector를 생성한다."""
    sample_detections = [
        {
            "track_id": 1,
            "type": "car",
            "bbox_2d": [520, 310, 180, 90],
            "confidence": 0.87,
            "motion_score": 0.0,
            "subtype": None,
            "detection_sources": ["sample"],
            "detection_reason": "앱 초기 화면 검증을 위한 샘플 차량입니다.",
            "is_candidate": False,
        }
    ]
    return build_scene_vector(
        frame_index=1,
        timestamp=0.0,
        detections=sample_detections,
        frame_size=(1280, 720),
    )
