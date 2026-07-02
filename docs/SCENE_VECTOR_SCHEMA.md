# SCENE_VECTOR_SCHEMA.md

## Scene Vector JSON 전체 구조

`scene_vector.json`은 단일 프레임을 표현하는 하나의 Scene Vector 객체입니다.

```json
{
  "scene_id": "clip_001_frame_0001",
  "timestamp": 0.0,
  "coordinate_system": {
    "origin": "ego_vehicle",
    "axis": {
      "x": "right",
      "y": "forward",
      "z": "up"
    },
    "unit": "meter_estimated"
  },
  "ego_vehicle": {
    "position_3d": [0.0, 0.0, 0.0],
    "heading": [0.0, 1.0, 0.0],
    "speed": null
  },
  "objects": [],
  "events": []
}
```

v1.3의 `scene_vectors.json`은 같은 Scene Vector 객체를 프레임 순서대로 담은 배열입니다.

```json
[
  {
    "scene_id": "clip_001_frame_0001",
    "timestamp": 0.0,
    "coordinate_system": {
      "origin": "ego_vehicle",
      "axis": {
        "x": "right",
        "y": "forward",
        "z": "up"
      },
      "unit": "meter_estimated"
    },
    "ego_vehicle": {
      "position_3d": [0.0, 0.0, 0.0],
      "heading": [0.0, 1.0, 0.0],
      "speed": null
    },
    "objects": [
      {
        "track_id": "light_001",
        "type": "unknown",
        "subtype": "possible_vehicle_headlight",
        "bbox_2d": [610, 330, 92, 38],
        "confidence": 0.48,
        "detection_sources": ["headlight_blob", "temporal_motion"],
        "detection_reason": "야간 프레임에서 차량 형상 대신 고휘도 전조등 후보가 감지되었습니다.",
        "is_candidate": true,
        "position_3d": {
          "estimate": [0.4, 22.0, 0.0],
          "range": {
            "x": [-0.2, 1.0],
            "y": [15.4, 28.6],
            "z": [0.0, 0.0]
          },
          "confidence": 0.5
        },
        "motion_vector_3d": {
          "vx": 0.0,
          "vy": 0.0,
          "vz": 0.0,
          "confidence": 0.0
        },
        "state": {
          "distance_zone": "mid",
          "lane_position": "center_front",
          "motion_state": "unknown"
        }
      }
    ],
    "events": []
  }
]
```

## 최상위 필드

| 필드 | 타입 | 필수 | 의미 | 예시 값 |
|---|---|---|---|---|
| `scene_id` | string | 예 | 장면 식별자 | `clip_001_frame_0001` |
| `timestamp` | number | 예 | 영상 내 시간 | `0.0` |
| `coordinate_system` | object | 예 | 좌표계 정의 | 아래 표 참고 |
| `ego_vehicle` | object | 예 | 자차 상태 | 아래 표 참고 |
| `objects` | array | 예 | 검출 객체 목록 | `[]` |
| `events` | array | 예 | 장면 이벤트 목록 | `[]` |

## coordinate_system

| 필드 | 타입 | 필수 | 의미 | 예시 값 |
|---|---|---|---|---|
| `origin` | string | 예 | 좌표계 원점 | `ego_vehicle` |
| `axis.x` | string | 예 | x축 양의 방향 | `right` |
| `axis.y` | string | 예 | y축 양의 방향 | `forward` |
| `axis.z` | string | 예 | z축 양의 방향 | `up` |
| `unit` | string | 예 | 좌표 단위 | `meter_estimated` |

## ego_vehicle

| 필드 | 타입 | 필수 | 의미 | 예시 값 |
|---|---|---|---|---|
| `position_3d` | number array | 예 | 자차 위치 | `[0.0, 0.0, 0.0]` |
| `heading` | number array | 예 | 자차 진행 방향 | `[0.0, 1.0, 0.0]` |
| `speed` | number 또는 null | 예 | 자차 속도 | `null` |

## objects 항목

| 필드 | 타입 | 필수 | 의미 | 예시 값 |
|---|---|---|---|---|
| `track_id` | number 또는 string | 예 | 객체 추적 ID | `1` |
| `type` | string | 예 | 객체 종류 | `car` |
| `subtype` | string 또는 null | 아니오 | 보조 객체 유형 | `headlight_pair` |
| `bbox_2d` | number array | 예 | 2D bbox `[x, y, width, height]` | `[520, 310, 180, 90]` |
| `confidence` | number | 예 | 객체 검출 신뢰도 | `0.87` |
| `detection_sources` | string array | 아니오 | 객체 후보를 만든 근거 목록 | `["yolo", "headlight_blob"]` |
| `detection_reason` | string | 아니오 | 사람이 읽을 수 있는 검출 근거 설명 | `전조등 후보가 감지됨` |
| `is_candidate` | boolean | 아니오 | 확정 객체가 아니라 보존 후보인지 여부 | `true` |
| `position_3d` | object | 예 | 3D 위치 추정값 | 아래 표 참고 |
| `motion_vector_3d` | object | 예 | 3D 움직임 벡터 | 아래 표 참고 |
| `state` | object | 예 | 객체 상태 요약 | 아래 표 참고 |

## detection_sources

| 값 | 의미 |
|---|---|
| `dummy` | 앱 파이프라인 검증용 더미 detector 결과 |
| `yolo` | Ultralytics YOLO 데모 백엔드 결과 |
| `headlight_blob` | 야간 전조등/고휘도 blob 기반 후보 |
| `temporal_motion` | 이전 샘플 프레임 후보와 이어진 고휘도 후보 |
| `sample` | 업로드 없이 생성한 샘플 데이터 |

## 2.5D 탑뷰 표시 기준

v1.4.1부터 2.5D 탑뷰는 고정 크기 마커 대신 객체 타입별 추정 물리 크기 박스를 사용합니다. 이 값은 JSON 필드가 아니라 현재 시각화 기준입니다.

| type/subtype | 기본 폭 | 기본 길이 | 의미 |
|---|---:|---:|---|
| `car` | 1.8m | 4.5m | 일반 승용차 기준 |
| `car/headlight_pair` | 1.8m | 4.5m | 전조등 쌍 기반 차량 후보 |
| `truck` | 2.5m | 8.0m | 트럭 기준 |
| `bus` | 2.6m | 10.0m | 버스 기준 |
| `motorcycle` | 0.8m | 2.2m | 오토바이 기준 |
| `bicycle` | 0.6m | 1.8m | 자전거 기준 |
| `person` | 0.6m | 0.6m | 보행자 기준 |
| `unknown/possible_vehicle_headlight` | 1.2m | 2.0m | 단일 전조등 가능 후보 |

`bbox_2d`의 화면상 면적은 실제 물리 크기가 아니므로 0.75~1.25배 범위의 약한 보정만 적용합니다. `is_candidate`가 `true`인 객체는 낮은 투명도와 점선 테두리로 표시합니다.

## position_3d

| 필드 | 타입 | 필수 | 의미 | 예시 값 |
|---|---|---|---|---|
| `estimate` | number array | 예 | 추정 위치 `[x, y, z]` | `[-1.4, 18.5, 0.0]` |
| `range.x` | number array | 예 | x 추정 범위 | `[-2.0, -0.8]` |
| `range.y` | number array | 예 | y 추정 범위 | `[14.0, 24.0]` |
| `range.z` | number array | 예 | z 추정 범위 | `[0.0, 0.0]` |
| `confidence` | number | 예 | 위치 추정 신뢰도 | `0.62` |

## motion_vector_3d

| 필드 | 타입 | 필수 | 의미 | 예시 값 |
|---|---|---|---|---|
| `vx` | number | 예 | x축 속도 추정 | `0.0` |
| `vy` | number | 예 | y축 속도 추정 | `0.0` |
| `vz` | number | 예 | z축 속도 추정 | `0.0` |
| `confidence` | number | 예 | 움직임 추정 신뢰도 | `0.0` |

## state

| 필드 | 타입 | 필수 | 의미 | 예시 값 |
|---|---|---|---|---|
| `distance_zone` | string | 예 | 전방 거리 구간 | `mid` |
| `lane_position` | string | 예 | 차로 기준 위치 | `center_front` |
| `motion_state` | string | 예 | 움직임 상태 | `unknown` |

## 좌표계 정의

```text
원점: 자차 위치
x: 오른쪽 양수, 왼쪽 음수
y: 전방 양수
z: 위쪽 양수, 도로면 0
단위: meter_estimated
```

## 데모 v1의 한계

- 단일 2D 영상만으로 실제 깊이를 정밀하게 복원하지 않습니다.
- 카메라 캘리브레이션이 반영되지 않았습니다.
- `z`는 초기에는 도로면 기준 `0.0`으로 둡니다.
- 움직임 벡터는 추후 프레임 간 추적이 연결될 때 갱신합니다.
- `scene_vectors.json`은 프레임별 결과 배열이며, 현재는 프레임 간 동일 객체 ID 연속성을 보장하지 않습니다.
- `headlight_blob` 후보는 차량 형상이 보이지 않는 야간 장면의 누락을 줄이기 위한 보존 후보이며 차량 확정 판정이 아닙니다.
- v1.4.1의 전조등 후보 필터는 가로등과 앞유리 물방울 잔상을 줄이기 위한 휴리스틱이며 모든 우천/야간 상황을 완전히 분리하지는 못합니다.
- 2.5D 탑뷰 박스 크기는 시각화를 위한 타입별 추정값이며 실제 차량 제원 측정값이 아닙니다.
- 모든 위치값은 영상 기반 추정값이며 `confidence`와 `range`를 함께 해석해야 합니다.
