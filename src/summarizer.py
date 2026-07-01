from typing import Any


def summarize_scene(scene_vector: dict[str, Any]) -> str:
    """Scene Vector를 사람이 읽기 쉬운 한 문장으로 요약한다."""
    objects = scene_vector.get("objects", [])
    if not objects:
        return "감지된 객체가 없습니다."

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
    }.get(first_object.get("type", "unknown"), "객체")

    return (
        f"{zone_text}에 {object_type_text} {len(objects)}대가 감지되었습니다. "
        f"해당 객체의 위치는 영상 기반 추정값이며 신뢰도는 {confidence:.2f}입니다."
    )
