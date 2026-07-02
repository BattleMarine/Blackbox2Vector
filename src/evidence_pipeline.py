from typing import Any


CONFIRMED_OBJECT_TYPES = {"person", "bicycle", "car", "motorcycle", "bus", "truck"}
YOLO_CONFIRMATION_THRESHOLD = 0.50


def get_bbox_center(bbox_2d: list[float]) -> tuple[float, float]:
    x, y, width, height = [float(value) for value in bbox_2d]
    return x + width / 2, y + height / 2


def is_in_analysis_roi(bbox_2d: list[float], frame_size: tuple[int, int]) -> bool:
    """초기 ROI는 보수적으로 화면 상단 광원과 하단 보닛/자막 영역을 피하기 위한 약한 필터다."""
    frame_width, frame_height = frame_size
    center_x, center_y = get_bbox_center(bbox_2d)
    return (
        frame_width * 0.05 <= center_x <= frame_width * 0.95
        and frame_height * 0.22 <= center_y <= frame_height * 0.78
    )


def build_raw_evidence(
    evidence_id: str,
    evidence_type: str,
    detection: dict[str, Any],
    reason: str,
    status: str = "observed",
) -> dict[str, Any]:
    """Raw Evidence는 객체가 아니라 후보 판단에 쓰는 원시 관측값으로만 보존한다."""
    return {
        "evidence_id": evidence_id,
        "type": evidence_type,
        "subtype": detection.get("subtype"),
        "bbox_2d": detection.get("bbox_2d"),
        "evidence_confidence": detection.get("confidence", detection.get("motion_score", 0.0)),
        "motion_score": detection.get("motion_score", 0.0),
        "sources": detection.get("detection_sources", ["unknown"]),
        "reason": reason,
        "status": status,
    }


def build_object_candidate(
    candidate_id: str,
    candidate_type: str,
    detection: dict[str, Any],
    evidence_ids: list[str],
    reason: str,
    status: str = "pending",
) -> dict[str, Any]:
    """Object Candidate는 아직 확정 객체가 아니므로 objects와 분리한다."""
    return {
        "candidate_id": candidate_id,
        "type": candidate_type,
        "subtype": detection.get("subtype"),
        "bbox_2d": detection.get("bbox_2d"),
        "candidate_confidence": detection.get("confidence", 0.0),
        "motion_score": detection.get("motion_score", 0.0),
        "detection_sources": detection.get("detection_sources", ["unknown"]),
        "evidence_ids": evidence_ids,
        "reason": reason,
        "status": status,
    }


def is_confirmable_model_detection(detection: dict[str, Any], frame_size: tuple[int, int]) -> bool:
    """YOLO 결과도 위치와 신뢰도가 약하면 후보로 내려 확정 객체 오염을 막는다."""
    sources = detection.get("detection_sources", [])
    object_type = detection.get("type", "unknown")
    confidence = float(detection.get("confidence", 0.0))

    if "dummy" in sources or "sample" in sources:
        return True
    if "yolo" not in sources:
        return False
    if object_type not in CONFIRMED_OBJECT_TYPES:
        return False
    if confidence < YOLO_CONFIRMATION_THRESHOLD:
        return False
    return is_in_analysis_roi(detection["bbox_2d"], frame_size)


def split_detections_by_certainty(
    model_detections: list[dict[str, Any]],
    light_detections: list[dict[str, Any]],
    motion_detections: list[dict[str, Any]],
    frame_size: tuple[int, int],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    """검출 결과를 Raw Evidence, Object Candidate, Confirmed Object로 분리한다."""
    raw_evidence: list[dict[str, Any]] = []
    object_candidates: list[dict[str, Any]] = []
    confirmed_objects: list[dict[str, Any]] = []
    rejected_count = 0

    for detection in model_detections:
        if is_confirmable_model_detection(detection, frame_size):
            confirmed = dict(detection)
            confirmed["is_candidate"] = False
            confirmed["certainty_level"] = "confirmed_object"
            confirmed_objects.append(confirmed)
            continue

        candidate_id = f"candidate_model_{len(object_candidates) + 1}"
        reason = "YOLO 결과이지만 신뢰도 또는 ROI 기준이 부족해 확정 객체로 승격하지 않았습니다."
        object_candidates.append(
            build_object_candidate(
                candidate_id=candidate_id,
                candidate_type=detection.get("type", "unknown"),
                detection=detection,
                evidence_ids=[],
                reason=reason,
                status="insufficient_evidence",
            )
        )

    for detection in light_detections:
        evidence_id = f"evidence_light_{len(raw_evidence) + 1}"
        raw_evidence.append(
            build_raw_evidence(
                evidence_id=evidence_id,
                evidence_type="bright_region",
                detection=detection,
                reason="밝은 영역은 차량이 아니라 차량 후보 판단에 쓰는 원시 관측값입니다.",
            )
        )
        if detection.get("subtype") == "headlight_pair" and is_in_analysis_roi(detection["bbox_2d"], frame_size):
            object_candidates.append(
                build_object_candidate(
                    candidate_id=f"candidate_light_{len(object_candidates) + 1}",
                    candidate_type="car",
                    detection=detection,
                    evidence_ids=[evidence_id],
                    reason="전조등 쌍처럼 보이는 밝은 영역이지만 YOLO 확정 객체가 아니므로 차량 후보로만 보존했습니다.",
                    status="pending",
                )
            )
        else:
            rejected_count += 1

    for detection in motion_detections:
        evidence_id = f"evidence_motion_{len(raw_evidence) + 1}"
        raw_evidence.append(
            build_raw_evidence(
                evidence_id=evidence_id,
                evidence_type="motion_region",
                detection=detection,
                reason="프레임 차분으로 관측된 움직임 영역이며 최종 객체로 직접 저장하지 않습니다.",
            )
        )

    diagnostics = {
        "confirmed_count": len(confirmed_objects),
        "candidate_count": len(object_candidates),
        "raw_evidence_count": len(raw_evidence),
        "not_promoted_count": rejected_count,
    }
    return raw_evidence, object_candidates, confirmed_objects, diagnostics


def build_overlay_items(scene_vector: dict[str, Any]) -> list[dict[str, Any]]:
    """화면 오버레이는 세 레이어를 함께 보여주되 label과 색으로 확정도를 구분한다."""
    overlay_items: list[dict[str, Any]] = []
    for obj in scene_vector.get("objects", []):
        item = dict(obj)
        item["visual_layer"] = "confirmed_object"
        overlay_items.append(item)
    for candidate in scene_vector.get("object_candidates", []):
        item = dict(candidate)
        item["confidence"] = candidate.get("candidate_confidence", 0.0)
        item["track_id"] = candidate.get("candidate_id")
        item["visual_layer"] = "object_candidate"
        overlay_items.append(item)
    for evidence in scene_vector.get("raw_evidence", []):
        item = dict(evidence)
        item["confidence"] = evidence.get("evidence_confidence", 0.0)
        item["track_id"] = evidence.get("evidence_id")
        item["detection_sources"] = evidence.get("sources", [])
        item["visual_layer"] = "raw_evidence"
        overlay_items.append(item)
    return overlay_items
