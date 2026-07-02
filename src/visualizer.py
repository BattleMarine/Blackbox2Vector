from typing import Any

import cv2
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle


TOP_VIEW_BASE_SIZES = {
    "car": (1.8, 4.5),
    "truck": (2.5, 8.0),
    "bus": (2.6, 10.0),
    "motorcycle": (0.8, 2.2),
    "bicycle": (0.6, 1.8),
    "person": (0.6, 0.6),
    "unknown": (1.2, 2.0),
}

TOP_VIEW_SUBTYPE_SIZES = {
    "headlight_pair": (1.8, 4.5),
    "possible_vehicle_headlight": (1.2, 2.0),
    "motion_region": (1.4, 2.4),
}


def get_detection_color_bgr(detection: dict[str, Any]) -> tuple[int, int, int]:
    """시각화 색상은 검출 출처보다 확정 단계를 우선해 사용자가 오해하지 않게 한다."""
    layer = detection.get("visual_layer")
    if layer == "confirmed_object":
        return (0, 255, 0)
    if layer == "object_candidate":
        return (0, 215, 255)
    if layer == "raw_evidence":
        return (255, 0, 255)

    sources = detection.get("detection_sources", [])
    if "headlight_blob" in sources:
        return (0, 215, 255)
    if "motion_flow" in sources:
        return (255, 0, 255)
    return (0, 255, 0)


def get_top_view_color(obj: dict[str, Any]) -> str:
    sources = obj.get("detection_sources", [])
    if "headlight_blob" in sources:
        return "tab:orange"
    if "motion_flow" in sources:
        return "tab:purple"
    return "tab:red"


def draw_detection_overlay(frame: Any, detections: list[dict[str, Any]]) -> Any:
    """프레임 위에 확정 객체, 후보, 원시 관측값을 서로 다른 레이어로 표시한다."""
    if frame is None:
        raise ValueError("시각화할 프레임이 없습니다.")

    overlay = frame.copy()
    for detection in detections:
        x, y, width, height = [int(value) for value in detection["bbox_2d"]]
        color = get_detection_color_bgr(detection)
        layer = detection.get("visual_layer", "detection")
        subtype = detection.get("subtype")
        type_label = detection.get("type", "unknown")
        label_type = f"{type_label}/{subtype}" if subtype else type_label
        label = f"{layer}: {label_type} {detection.get('confidence', 0.0):.2f}"
        thickness = 2 if layer == "confirmed_object" else 1

        cv2.rectangle(overlay, (x, y), (x + width, y + height), color, thickness)
        cv2.putText(
            overlay,
            label,
            (x, max(y - 8, 0)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            color,
            2,
            cv2.LINE_AA,
        )

    return overlay


def estimate_top_view_box_size(obj: dict[str, Any]) -> tuple[float, float]:
    """탑뷰 박스는 객체 타입의 평균 물리 크기에 bbox 크기를 약하게 반영해 정한다."""
    object_type = obj.get("type", "unknown")
    subtype = obj.get("subtype")
    base_width, base_length = TOP_VIEW_SUBTYPE_SIZES.get(
        subtype,
        TOP_VIEW_BASE_SIZES.get(object_type, TOP_VIEW_BASE_SIZES["unknown"]),
    )
    bbox = obj.get("bbox_2d", [0, 0, 1, 1])
    _, _, bbox_width, bbox_height = [float(value) for value in bbox]
    bbox_area = max(bbox_width * bbox_height, 1.0)

    # bbox 픽셀 크기는 실제 물리 크기가 아니므로 0.75~1.25 범위의 약한 보정만 적용한다.
    scale = (bbox_area / 12000.0) ** 0.15
    scale = min(max(scale, 0.75), 1.25)
    return base_width * scale, base_length * scale


def draw_top_view(scene_vector: dict[str, Any]):
    """탑뷰는 최종 확정 객체만 표시해 후보와 raw evidence가 3D 객체처럼 보이지 않게 한다."""
    figure, axis = plt.subplots(figsize=(6, 6))
    axis.set_title("2.5D Top View - Confirmed Objects")
    axis.set_xlabel("x: right (meter estimated)")
    axis.set_ylabel("y: forward (meter estimated)")

    axis.scatter([0], [0], marker="^", s=180, color="tab:blue", label="ego")
    axis.text(0, -1.5, "ego", ha="center", color="tab:blue")

    for obj in scene_vector.get("objects", []):
        position = obj["position_3d"]["estimate"]
        x, y, _ = position
        color = get_top_view_color(obj)
        box_width, box_length = estimate_top_view_box_size(obj)
        box = Rectangle(
            (x - box_width / 2, y - box_length / 2),
            box_width,
            box_length,
            linewidth=1.8,
            edgecolor=color,
            facecolor=color,
            alpha=0.55,
        )
        axis.add_patch(box)
        axis.text(x, y + box_length / 2 + 0.8, f"{obj['type']} #{obj['track_id']}", ha="center", color=color)

        x_range = obj["position_3d"]["range"]["x"]
        y_range = obj["position_3d"]["range"]["y"]
        axis.fill_between(
            x_range,
            y_range[0],
            y_range[1],
            color=color,
            alpha=0.12,
        )

    axis.axhline(0, color="black", linewidth=0.8)
    axis.axvline(0, color="black", linewidth=0.8)
    axis.set_xlim(-8, 8)
    axis.set_ylim(-3, 45)
    axis.grid(True, alpha=0.3)
    axis.legend(loc="upper right")
    figure.tight_layout()
    return figure
