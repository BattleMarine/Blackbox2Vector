from typing import Any

import cv2
import numpy as np


def build_rejected_light(reason: str, bbox_2d: list[float] | None = None) -> dict[str, Any]:
    """오탐 튜닝을 위해 Scene Vector에 넣지 않은 광원 후보의 제외 이유를 남긴다."""
    return {
        "reason": reason,
        "bbox_2d": [round(value, 2) for value in bbox_2d] if bbox_2d else None,
    }


def summarize_rejections(rejected_lights: list[dict[str, Any]]) -> dict[str, int]:
    """프레임별 제외 이유를 앱에서 빠르게 검토할 수 있도록 집계한다."""
    summary: dict[str, int] = {}
    for rejected_light in rejected_lights:
        reason = rejected_light["reason"]
        summary[reason] = summary.get(reason, 0) + 1
    return summary


def calculate_iou(first_bbox: list[float], second_bbox: list[float]) -> float:
    """후보 병합 시 같은 영역을 중복 객체로 남기지 않기 위해 IoU를 계산한다."""
    first_x, first_y, first_w, first_h = [float(value) for value in first_bbox]
    second_x, second_y, second_w, second_h = [float(value) for value in second_bbox]

    first_x2 = first_x + first_w
    first_y2 = first_y + first_h
    second_x2 = second_x + second_w
    second_y2 = second_y + second_h

    overlap_x1 = max(first_x, second_x)
    overlap_y1 = max(first_y, second_y)
    overlap_x2 = min(first_x2, second_x2)
    overlap_y2 = min(first_y2, second_y2)

    overlap_w = max(0.0, overlap_x2 - overlap_x1)
    overlap_h = max(0.0, overlap_y2 - overlap_y1)
    overlap_area = overlap_w * overlap_h
    first_area = max(first_w * first_h, 1.0)
    second_area = max(second_w * second_h, 1.0)
    union_area = first_area + second_area - overlap_area
    return overlap_area / max(union_area, 1.0)


def get_artifact_zone_reason(blob: dict[str, Any], frame_size: tuple[int, int]) -> str | None:
    """차량 후보가 되기 어려운 화면 영역과 반사 형태를 먼저 제거한다."""
    frame_width, frame_height = frame_size
    x, y, width, height = blob["bbox_2d"]
    center_x, center_y = blob["center"]
    aspect_ratio = blob.get("aspect_ratio", width / max(height, 1))
    bbox_area_ratio = blob.get("bbox_area_ratio", (width * height) / max(frame_width * frame_height, 1))

    if center_y > frame_height * 0.72:
        return "보닛/대시보드 반사 영역"
    if center_y < frame_height * 0.24:
        return "상단 고정 광원 영역"
    if (center_x < frame_width * 0.1 or center_x > frame_width * 0.9) and center_y < frame_height * 0.68:
        return "측면 간판/건물 광원 영역"
    if aspect_ratio > 2.5:
        return "긴 수평 반사선"
    if aspect_ratio < 0.28:
        return "긴 수직 광원/기둥 반사"
    if bbox_area_ratio > 0.018 and blob.get("fill_ratio", 0.0) < 0.42:
        return "넓은 빛번짐"

    return None


def build_light_mask(frame: Any, brightness_threshold: int = 220) -> Any:
    """야간 전조등처럼 형상보다 밝기가 먼저 보이는 객체 후보를 분리한다."""
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    hue, saturation, value = cv2.split(hsv)

    white_light = (value >= brightness_threshold) & (saturation <= 120)
    yellow_light = (value >= max(brightness_threshold - 35, 160)) & (saturation >= 45) & (hue >= 10) & (hue <= 45)
    mask = np.where(white_light | yellow_light, 255, 0).astype(np.uint8)

    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
    mask = cv2.dilate(mask, kernel, iterations=1)
    return mask


def extract_light_blobs_with_rejections(
    frame: Any,
    brightness_threshold: int = 220,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """고휘도 영역을 bbox 후보로 변환한다."""
    if frame is None:
        raise ValueError("전조등 후보 검출에 사용할 프레임이 없습니다.")

    frame_height, frame_width = frame.shape[:2]
    frame_area = frame_width * frame_height
    mask = build_light_mask(frame, brightness_threshold)
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    blobs: list[dict[str, Any]] = []
    rejected_lights: list[dict[str, Any]] = []

    for contour in contours:
        area = float(cv2.contourArea(contour))
        if area < max(frame_area * 0.00003, 10.0):
            rejected_lights.append(build_rejected_light("작은 물방울/노이즈"))
            continue

        x, y, width, height = cv2.boundingRect(contour)
        bbox_2d = [float(x), float(y), float(width), float(height)]
        if width <= 3 or height <= 3:
            rejected_lights.append(build_rejected_light("작은 물방울/노이즈", bbox_2d))
            continue
        if width > frame_width * 0.28 or height > frame_height * 0.22:
            rejected_lights.append(build_rejected_light("과도하게 큰 광원/간판", bbox_2d))
            continue

        roi = mask[y : y + height, x : x + width]
        fill_ratio = float(cv2.countNonZero(roi)) / max(width * height, 1)
        if fill_ratio < 0.16:
            rejected_lights.append(build_rejected_light("희미한 빛번짐", bbox_2d))
            continue

        aspect_ratio = width / max(height, 1)
        if aspect_ratio > 4.2 or aspect_ratio < 0.18:
            rejected_lights.append(build_rejected_light("길게 늘어진 반사/잔상", bbox_2d))
            continue

        perimeter = max(float(cv2.arcLength(contour, True)), 1.0)
        circularity = 4.0 * np.pi * area / (perimeter * perimeter)
        if circularity < 0.08:
            rejected_lights.append(build_rejected_light("불규칙한 물방울/번짐 형태", bbox_2d))
            continue

        bbox_area_ratio = (width * height) / max(frame_area, 1)
        if bbox_area_ratio > 0.025 and fill_ratio < 0.34:
            rejected_lights.append(build_rejected_light("넓은 빛번짐", bbox_2d))
            continue

        center_x = x + width / 2
        center_y = y + height / 2
        shape_score = min(circularity / 0.55, 1.0)
        size_score = min(area / max(frame_area * 0.0035, 1.0), 1.0)
        confidence = min(0.56, 0.2 + fill_ratio * 0.22 + shape_score * 0.08 + size_score * 0.1)
        blobs.append(
            {
                "bbox_2d": [float(x), float(y), float(width), float(height)],
                "center": [float(center_x), float(center_y)],
                "area": area,
                "fill_ratio": round(fill_ratio, 4),
                "aspect_ratio": round(aspect_ratio, 4),
                "circularity": round(circularity, 4),
                "bbox_area_ratio": round(bbox_area_ratio, 6),
                "confidence": round(confidence, 4),
            }
        )

    return sorted(blobs, key=lambda blob: (blob["bbox_2d"][1], blob["bbox_2d"][0])), rejected_lights


def extract_light_blobs(frame: Any, brightness_threshold: int = 220) -> list[dict[str, Any]]:
    """기존 호출부 호환을 위해 통과 blob만 반환한다."""
    blobs, _ = extract_light_blobs_with_rejections(frame, brightness_threshold)
    return blobs


def is_headlight_pair(left_blob: dict[str, Any], right_blob: dict[str, Any], frame_width: int, frame_height: int) -> bool:
    """나란한 두 고휘도 blob이 같은 차량의 전조등 쌍인지 휴리스틱으로 판단한다."""
    left_x, left_y, left_w, left_h = left_blob["bbox_2d"]
    right_x, right_y, right_w, right_h = right_blob["bbox_2d"]
    left_center_x, left_center_y = left_blob["center"]
    right_center_x, right_center_y = right_blob["center"]

    if left_center_x >= right_center_x:
        return False

    average_height = max((left_h + right_h) / 2, 1.0)
    average_width = max((left_w + right_w) / 2, 1.0)
    horizontal_gap = right_center_x - left_center_x
    vertical_gap = abs(right_center_y - left_center_y)
    height_ratio = min(left_h, right_h) / max(left_h, right_h, 1.0)
    width_ratio = min(left_w, right_w) / max(left_w, right_w, 1.0)
    average_y = (left_center_y + right_center_y) / 2
    pair_width = (right_x + right_w) - left_x

    if average_y < frame_height * 0.22:
        return False
    if average_y > frame_height * 0.72:
        return False
    if vertical_gap > average_height * 0.9:
        return False
    if horizontal_gap < average_width * 1.8:
        return False
    if horizontal_gap > frame_width * 0.16:
        return False
    if pair_width > frame_width * 0.14:
        return False
    if pair_width / average_height > 6.0:
        return False
    if height_ratio < 0.55 or width_ratio < 0.45:
        return False
    if min(left_blob.get("circularity", 0.0), right_blob.get("circularity", 0.0)) < 0.12:
        return False

    return True


def build_pair_detection(
    first_blob: dict[str, Any],
    second_blob: dict[str, Any],
    track_id: str,
) -> dict[str, Any]:
    """전조등 쌍을 가능한 차량 후보 detection으로 변환한다."""
    first_x, first_y, first_w, first_h = first_blob["bbox_2d"]
    second_x, second_y, second_w, second_h = second_blob["bbox_2d"]
    x1 = min(first_x, second_x)
    y1 = min(first_y, second_y)
    x2 = max(first_x + first_w, second_x + second_w)
    y2 = max(first_y + first_h, second_y + second_h)
    confidence = min(0.72, max(first_blob["confidence"], second_blob["confidence"]) + 0.18)

    return {
        "track_id": track_id,
        "type": "car",
        "subtype": "headlight_pair",
        "bbox_2d": [round(x1, 2), round(y1, 2), round(x2 - x1, 2), round(y2 - y1, 2)],
        "confidence": round(confidence, 4),
        "detection_sources": ["headlight_blob"],
        "detection_reason": "나란한 고휘도 blob 쌍이 감지되어 전조등 기반 차량 후보로 보존했습니다.",
        "is_candidate": True,
    }


def build_single_light_detection(blob: dict[str, Any], track_id: str) -> dict[str, Any]:
    """차량이라고 단정하기 어려운 단일 고휘도 blob을 unknown 후보로 보존한다."""
    x, y, width, height = blob["bbox_2d"]
    return {
        "track_id": track_id,
        "type": "unknown",
        "subtype": "possible_vehicle_headlight",
        "bbox_2d": [round(x, 2), round(y, 2), round(width, 2), round(height, 2)],
        "confidence": blob["confidence"],
        "detection_sources": ["headlight_blob"],
        "detection_reason": "엄격한 형태 기준을 통과한 단일 고휘도 전조등 후보가 감지되었습니다.",
        "is_candidate": True,
    }


def should_keep_single_light_candidate(blob: dict[str, Any], frame_size: tuple[int, int]) -> bool:
    """단일 광원은 오탐이 많으므로 전조등 후보로 볼 만한 경우만 남긴다."""
    return get_single_light_rejection_reason(blob, frame_size) is None


def get_single_light_rejection_reason(blob: dict[str, Any], frame_size: tuple[int, int]) -> str | None:
    """단일 광원을 Scene Vector 후보로 남기지 않을 이유를 판단한다."""
    frame_width, frame_height = frame_size
    x, y, width, height = blob["bbox_2d"]
    center_x, center_y = blob["center"]
    aspect_ratio = blob.get("aspect_ratio", width / max(height, 1))
    circularity = blob.get("circularity", 0.0)
    fill_ratio = blob.get("fill_ratio", 0.0)
    bbox_area_ratio = blob.get("bbox_area_ratio", (width * height) / max(frame_width * frame_height, 1))

    artifact_reason = get_artifact_zone_reason(blob, frame_size)
    if artifact_reason:
        return artifact_reason
    if center_y < frame_height * 0.45:
        return "상단 단일 광원"
    if center_x < frame_width * 0.05 or center_x > frame_width * 0.95:
        return "화면 가장자리 단일 광원"
    if aspect_ratio > 2.8 or aspect_ratio < 0.3:
        return "전조등으로 보기 어려운 종횡비"
    if circularity < 0.16:
        return "불규칙한 물방울/번짐 형태"
    if fill_ratio < 0.22:
        return "희미한 빛번짐"
    if bbox_area_ratio > 0.012:
        return "단일 후보로 보기엔 큰 광원"
    if width > frame_width * 0.05 or height > frame_height * 0.08:
        return "단일 후보로 보기엔 큰 광원"
    if bbox_area_ratio < 0.00035:
        return "작은 원거리 광원/물방울"
    if float(blob.get("confidence", 0.0)) < 0.43:
        return "낮은 단일 광원 신뢰도"

    return None


def apply_temporal_boost(
    candidates: list[dict[str, Any]],
    previous_candidates: list[dict[str, Any]] | None,
    frame_size: tuple[int, int],
) -> list[dict[str, Any]]:
    """앞 프레임의 고휘도 후보와 이어지는 객체는 누락 방지 후보로 신뢰도를 보강한다."""
    if not previous_candidates:
        return candidates

    frame_width, frame_height = frame_size
    max_distance = max(frame_width, frame_height) * 0.08
    boosted_candidates: list[dict[str, Any]] = []

    for candidate in candidates:
        x, y, width, height = candidate["bbox_2d"]
        center_x = x + width / 2
        center_y = y + height / 2
        boosted = dict(candidate)

        for previous in previous_candidates:
            prev_x, prev_y, prev_w, prev_h = previous["bbox_2d"]
            prev_center_x = prev_x + prev_w / 2
            prev_center_y = prev_y + prev_h / 2
            distance = ((center_x - prev_center_x) ** 2 + (center_y - prev_center_y) ** 2) ** 0.5
            size_ratio = min(width * height, prev_w * prev_h) / max(width * height, prev_w * prev_h, 1.0)
            if distance <= max_distance and size_ratio >= 0.35:
                sources = list(dict.fromkeys(boosted.get("detection_sources", []) + ["temporal_motion"]))
                boosted["detection_sources"] = sources
                boosted["confidence"] = round(min(float(boosted.get("confidence", 0.0)) + 0.12, 0.82), 4)
                boosted["detection_reason"] = (
                    f"{boosted.get('detection_reason', '고휘도 후보가 감지되었습니다.')} "
                    "이전 샘플 프레임의 고휘도 후보와 위치가 이어져 temporal 후보로 보강했습니다."
                )
                break

        boosted_candidates.append(boosted)

    return boosted_candidates


def detect_light_candidates(
    frame: Any,
    previous_candidates: list[dict[str, Any]] | None = None,
    brightness_threshold: int = 220,
) -> list[dict[str, Any]]:
    """YOLO가 놓치기 쉬운 야간 전조등/고휘도 객체 후보를 찾는다."""
    candidates, _ = detect_light_candidates_with_diagnostics(frame, previous_candidates, brightness_threshold)
    return candidates


def detect_light_candidates_with_diagnostics(
    frame: Any,
    previous_candidates: list[dict[str, Any]] | None = None,
    brightness_threshold: int = 220,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """전조등 후보와 제외된 광원/반사 이유를 함께 반환한다."""
    frame_height, frame_width = frame.shape[:2]
    frame_size = (frame_width, frame_height)
    blobs, rejected_lights = extract_light_blobs_with_rejections(frame, brightness_threshold)
    used_indexes: set[int] = set()
    rejected_indexes: set[int] = set()
    detections: list[dict[str, Any]] = []

    for first_index, first_blob in enumerate(blobs):
        if first_index in used_indexes:
            continue
        artifact_reason = get_artifact_zone_reason(first_blob, frame_size)
        if artifact_reason:
            rejected_lights.append(build_rejected_light(artifact_reason, first_blob["bbox_2d"]))
            rejected_indexes.add(first_index)
            continue

        best_pair_index = None
        best_gap = float("inf")
        for second_index, second_blob in enumerate(blobs):
            if second_index <= first_index or second_index in used_indexes:
                continue
            second_artifact_reason = get_artifact_zone_reason(second_blob, frame_size)
            if second_artifact_reason:
                continue
            if is_headlight_pair(first_blob, second_blob, frame_width, frame_height):
                gap = abs(second_blob["center"][0] - first_blob["center"][0])
                if gap < best_gap:
                    best_gap = gap
                    best_pair_index = second_index

        if best_pair_index is not None:
            used_indexes.add(first_index)
            used_indexes.add(best_pair_index)
            detections.append(
                build_pair_detection(
                    first_blob,
                    blobs[best_pair_index],
                    track_id=f"light_pair_{len(detections) + 1}",
                )
            )

    for blob_index, blob in enumerate(blobs):
        if blob_index in used_indexes or blob_index in rejected_indexes:
            continue
        rejection_reason = get_single_light_rejection_reason(blob, frame_size)
        if rejection_reason is not None:
            rejected_lights.append(build_rejected_light(rejection_reason, blob["bbox_2d"]))
            rejected_indexes.add(blob_index)
            continue
        detections.append(build_single_light_detection(blob, track_id=f"light_{len(detections) + 1}"))

    boosted_detections = apply_temporal_boost(detections, previous_candidates, frame_size)
    diagnostics = {
        "rejected_count": len(rejected_lights),
        "rejected_by_reason": summarize_rejections(rejected_lights),
        "rejected_samples": rejected_lights[:20],
    }
    return boosted_detections, diagnostics


def merge_detections(
    model_detections: list[dict[str, Any]],
    light_candidates: list[dict[str, Any]],
    iou_threshold: float = 0.25,
) -> list[dict[str, Any]]:
    """모델 검출과 전조등 후보를 합치되 같은 영역은 하나의 객체로 보존한다."""
    merged: list[dict[str, Any]] = []
    for detection in model_detections:
        enriched = dict(detection)
        enriched.setdefault("subtype", None)
        enriched.setdefault("detection_sources", [enriched.get("backend", "model")])
        enriched.setdefault("detection_reason", "객체 검출 모델이 bbox를 반환했습니다.")
        enriched.setdefault("is_candidate", False)
        merged.append(enriched)

    for candidate in light_candidates:
        matched_detection = None
        for detection in merged:
            if calculate_iou(detection["bbox_2d"], candidate["bbox_2d"]) >= iou_threshold:
                matched_detection = detection
                break

        if matched_detection is None:
            merged.append(candidate)
            continue

        sources = list(dict.fromkeys(matched_detection.get("detection_sources", []) + candidate.get("detection_sources", [])))
        matched_detection["detection_sources"] = sources
        matched_detection["confidence"] = round(max(float(matched_detection.get("confidence", 0.0)), float(candidate.get("confidence", 0.0))), 4)
        matched_detection["detection_reason"] = (
            f"{matched_detection.get('detection_reason', '모델 검출 결과입니다.')} "
            "같은 영역에서 전조등 후보도 감지되어 검출 근거를 보강했습니다."
        )
        if matched_detection.get("subtype") is None:
            matched_detection["subtype"] = candidate.get("subtype")

    return merged
