from typing import Any

import cv2
import matplotlib.pyplot as plt


def draw_detection_overlay(frame: Any, detections: list[dict[str, Any]]) -> Any:
    """프레임 위에 bbox와 객체 정보를 그린다."""
    if frame is None:
        raise ValueError("시각화할 프레임이 없습니다.")

    overlay = frame.copy()
    for detection in detections:
        x, y, width, height = [int(value) for value in detection["bbox_2d"]]
        sources = detection.get("detection_sources", [])
        is_light_candidate = "headlight_blob" in sources
        color = (0, 215, 255) if is_light_candidate else (0, 255, 0)
        subtype = detection.get("subtype")
        type_label = detection.get("type", "unknown")
        label_type = f"{type_label}/{subtype}" if subtype else type_label
        label = f"{label_type} {detection.get('confidence', 0.0):.2f}"

        cv2.rectangle(overlay, (x, y), (x + width, y + height), color, 2)
        cv2.putText(
            overlay,
            label,
            (x, max(y - 8, 0)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            color,
            2,
            cv2.LINE_AA,
        )

    return overlay


def draw_top_view(scene_vector: dict[str, Any]):
    """자차와 객체의 추정 위치를 2.5D 탑뷰로 표시한다."""
    figure, axis = plt.subplots(figsize=(6, 6))
    axis.set_title("2.5D Top View")
    axis.set_xlabel("x: right (meter estimated)")
    axis.set_ylabel("y: forward (meter estimated)")

    axis.scatter([0], [0], marker="^", s=180, color="tab:blue", label="ego")
    axis.text(0, -1.5, "ego", ha="center", color="tab:blue")

    for obj in scene_vector.get("objects", []):
        position = obj["position_3d"]["estimate"]
        x, y, _ = position
        color = "tab:orange" if "headlight_blob" in obj.get("detection_sources", []) else "tab:red"
        axis.scatter([x], [y], marker="s", s=120, color=color)
        axis.text(x, y + 1.0, f"{obj['type']} #{obj['track_id']}", ha="center", color=color)

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
