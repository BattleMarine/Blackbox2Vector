from typing import Any

import cv2

from src.light_candidate_detector import calculate_iou


def build_motion_mask(
    previous_frame: Any,
    current_frame: Any,
    diff_threshold: int = 28,
) -> Any:
    """야간 영상에서는 색보다 변화량이 더 안정적인 단서가 될 수 있어 프레임 차분 mask를 만든다."""
    previous_gray = cv2.cvtColor(previous_frame, cv2.COLOR_BGR2GRAY)
    current_gray = cv2.cvtColor(current_frame, cv2.COLOR_BGR2GRAY)
    previous_blur = cv2.GaussianBlur(previous_gray, (7, 7), 0)
    current_blur = cv2.GaussianBlur(current_gray, (7, 7), 0)

    frame_diff = cv2.absdiff(previous_blur, current_blur)
    _, mask = cv2.threshold(frame_diff, diff_threshold, 255, cv2.THRESH_BINARY)

    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
    mask = cv2.dilate(mask, kernel, iterations=2)
    return mask


def get_motion_artifact_reason(bbox_2d: list[float], frame_size: tuple[int, int]) -> str | None:
    """후드 반사, 화면 가장자리 변화, 상단 고정 광원처럼 객체 후보가 되기 어려운 움직임을 걸러낸다."""
    frame_width, frame_height = frame_size
    x, y, width, height = bbox_2d
    center_x = x + width / 2
    center_y = y + height / 2
    aspect_ratio = width / max(height, 1.0)
    area_ratio = (width * height) / max(frame_width * frame_height, 1)

    if center_y > frame_height * 0.74:
        return "보닛/대시보드 반사 움직임"
    if center_y < frame_height * 0.20:
        return "상단 배경/가로등 변화"
    if center_x < frame_width * 0.04 or center_x > frame_width * 0.96:
        return "화면 가장자리 움직임"
    if aspect_ratio > 7.0:
        return "긴 수평 반사 움직임"
    if area_ratio > 0.18:
        return "전역 밝기 변화"

    return None


def extract_motion_candidates(
    previous_frame: Any,
    current_frame: Any,
    min_area_ratio: float = 0.0007,
    diff_threshold: int = 28,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """프레임 차분으로 YOLO와 전조등 후보가 놓친 움직임 영역을 unknown 후보로 보존한다."""
    if previous_frame is None or current_frame is None:
        return [], {"rejected_count": 0, "rejected_by_reason": {}}

    frame_height, frame_width = current_frame.shape[:2]
    frame_size = (frame_width, frame_height)
    frame_area = frame_width * frame_height
    mask = build_motion_mask(previous_frame, current_frame, diff_threshold)
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    candidates: list[dict[str, Any]] = []
    rejected_by_reason: dict[str, int] = {}

    for contour in contours:
        area = float(cv2.contourArea(contour))
        if area < frame_area * min_area_ratio:
            rejected_by_reason["작은 움직임 노이즈"] = rejected_by_reason.get("작은 움직임 노이즈", 0) + 1
            continue

        x, y, width, height = cv2.boundingRect(contour)
        bbox_2d = [float(x), float(y), float(width), float(height)]
        artifact_reason = get_motion_artifact_reason(bbox_2d, frame_size)
        if artifact_reason is not None:
            rejected_by_reason[artifact_reason] = rejected_by_reason.get(artifact_reason, 0) + 1
            continue

        roi = mask[y : y + height, x : x + width]
        fill_ratio = float(cv2.countNonZero(roi)) / max(width * height, 1)
        if fill_ratio < 0.08:
            rejected_by_reason["희박한 움직임 번짐"] = rejected_by_reason.get("희박한 움직임 번짐", 0) + 1
            continue

        motion_score = min(0.85, 0.25 + fill_ratio * 0.35 + min(area / (frame_area * 0.04), 1.0) * 0.25)
        candidates.append(
            {
                "track_id": f"motion_{len(candidates) + 1}",
                "type": "unknown",
                "subtype": "motion_region",
                "bbox_2d": [round(x, 2), round(y, 2), round(width, 2), round(height, 2)],
                "confidence": round(motion_score, 4),
                "motion_score": round(motion_score, 4),
                "detection_sources": ["motion_flow"],
                "detection_reason": "이전 샘플 프레임과 비교해 움직임이 있는 영역으로 보존했습니다.",
                "is_candidate": True,
            }
        )

    diagnostics = {
        "rejected_count": sum(rejected_by_reason.values()),
        "rejected_by_reason": rejected_by_reason,
    }
    return candidates, diagnostics


def calculate_bbox_motion_score(bbox_2d: list[float], motion_mask: Any) -> float:
    """기존 detection bbox 내부에 움직임 mask가 얼마나 겹치는지 계산한다."""
    if motion_mask is None:
        return 0.0

    mask_height, mask_width = motion_mask.shape[:2]
    x, y, width, height = [int(round(value)) for value in bbox_2d]
    x1 = max(x, 0)
    y1 = max(y, 0)
    x2 = min(x + max(width, 1), mask_width)
    y2 = min(y + max(height, 1), mask_height)
    if x1 >= x2 or y1 >= y2:
        return 0.0

    roi = motion_mask[y1:y2, x1:x2]
    return float(cv2.countNonZero(roi)) / max((x2 - x1) * (y2 - y1), 1)


def annotate_detections_with_motion(
    detections: list[dict[str, Any]],
    previous_frame: Any,
    current_frame: Any,
    motion_threshold: float = 0.08,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """기존 YOLO/전조등 후보가 실제 프레임 변화와 겹치면 검출 근거를 보강한다."""
    if previous_frame is None or current_frame is None:
        return detections, {"verified_count": 0}

    motion_mask = build_motion_mask(previous_frame, current_frame)
    annotated: list[dict[str, Any]] = []
    verified_count = 0

    for detection in detections:
        enriched = dict(detection)
        motion_score = calculate_bbox_motion_score(enriched["bbox_2d"], motion_mask)
        enriched["motion_score"] = round(motion_score, 4)
        if motion_score >= motion_threshold:
            sources = list(dict.fromkeys(enriched.get("detection_sources", []) + ["motion_flow", "temporal_verified"]))
            enriched["detection_sources"] = sources
            enriched["confidence"] = round(min(float(enriched.get("confidence", 0.0)) + min(motion_score, 0.25), 0.95), 4)
            enriched["detection_reason"] = (
                f"{enriched.get('detection_reason', '검출 후보입니다.')} "
                "이전 샘플 프레임과 비교한 motion mask와 겹쳐 temporal 검증 근거를 추가했습니다."
            )
            verified_count += 1
        annotated.append(enriched)

    return annotated, {"verified_count": verified_count}


def merge_motion_candidates(
    detections: list[dict[str, Any]],
    motion_candidates: list[dict[str, Any]],
    iou_threshold: float = 0.18,
) -> list[dict[str, Any]]:
    """기존 detection과 겹치지 않는 움직임 영역만 unknown 후보로 추가한다."""
    merged = list(detections)
    for candidate in motion_candidates:
        if any(calculate_iou(candidate["bbox_2d"], detection["bbox_2d"]) >= iou_threshold for detection in merged):
            continue
        merged.append(candidate)
    return merged
