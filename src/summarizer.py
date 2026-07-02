from typing import Any


def summarize_scene(scene_vector: dict[str, Any]) -> str:
    """Scene Vector의 확정 객체와 후보/evidence 수를 구분해 한 문장으로 요약한다."""
    objects = scene_vector.get("objects", [])
    candidates = scene_vector.get("object_candidates", [])
    raw_evidence = scene_vector.get("raw_evidence", [])

    if not objects:
        return (
            f"확정 객체는 없습니다. 객체 후보 {len(candidates)}개와 raw evidence {len(raw_evidence)}개가 "
            "분리 보존되었습니다."
        )

    first_object = objects[0]
    position = first_object.get("position_3d", {})
    confidence = position.get("confidence", 0.0)
    distance_zone = first_object.get("state", {}).get("distance_zone", "unknown")

    zone_text = {
        "near": "전방 근거리 영역",
        "mid": "전방 중거리 영역",
        "far": "전방 원거리 영역",
    }.get(distance_zone, "전방 추정 영역")

    object_type_text = {
        "car": "차량",
        "truck": "트럭",
        "bus": "버스",
        "person": "보행자",
        "motorcycle": "오토바이",
        "bicycle": "자전거",
        "unknown": "미확정 객체",
    }.get(first_object.get("type", "unknown"), "객체")
    object_unit = "대" if first_object.get("type") in {"car", "truck", "bus", "motorcycle"} else "개"

    return (
        f"{zone_text}에 확정 {object_type_text} {len(objects)}{object_unit}가 감지되었습니다. "
        f"위치는 영상 기반 추정값이며 위치 신뢰도는 {confidence:.2f}입니다. "
        f"별도로 객체 후보 {len(candidates)}개와 raw evidence {len(raw_evidence)}개가 보존되었습니다."
    )
