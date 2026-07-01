def estimate_position_3d(
    bbox_2d: list[float],
    frame_width: int,
    frame_height: int,
    object_type: str,
) -> dict[str, object]:
    """2D bbox를 이용해 자차 기준 3D 위치를 거칠게 추정한다."""
    if len(bbox_2d) != 4:
        raise ValueError("bbox_2d는 [x, y, width, height] 형식이어야 합니다.")
    if frame_width <= 0 or frame_height <= 0:
        raise ValueError("프레임 크기는 1 이상이어야 합니다.")

    x, y, width, height = [float(value) for value in bbox_2d]
    if width <= 0 or height <= 0:
        raise ValueError("bbox_2d의 width와 height는 1 이상이어야 합니다.")

    bottom_center_x = x + width / 2
    bottom_y = y + height

    normalized_x = (bottom_center_x - frame_width / 2) / (frame_width / 2)
    normalized_bottom_y = bottom_y / frame_height
    normalized_height = height / frame_height

    # 단일 2D 영상에서는 실제 깊이를 알 수 없으므로 bbox 하단 위치와 크기를 거리 추정의 보조 신호로 사용한다.
    estimated_x = round(normalized_x * 6.0, 2)
    y_from_bottom = (1.0 - normalized_bottom_y) * 35.0
    y_from_size = max(3.0, min(45.0, 4.0 / max(normalized_height, 0.03)))
    estimated_y = round((y_from_bottom + y_from_size) / 2, 2)
    estimated_z = 0.0

    object_confidence_bias = {
        "car": 0.62,
        "truck": 0.58,
        "bus": 0.58,
        "person": 0.45,
        "motorcycle": 0.5,
    }
    confidence = object_confidence_bias.get(object_type, 0.5)

    x_margin = max(0.6, abs(estimated_x) * 0.25)
    y_margin = max(3.0, estimated_y * 0.3)

    return {
        "estimate": [estimated_x, estimated_y, estimated_z],
        "range": {
            "x": [round(estimated_x - x_margin, 2), round(estimated_x + x_margin, 2)],
            "y": [round(max(0.0, estimated_y - y_margin), 2), round(estimated_y + y_margin, 2)],
            "z": [0.0, 0.0],
        },
        "confidence": confidence,
    }
