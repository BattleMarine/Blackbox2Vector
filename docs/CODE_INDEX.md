# CODE_INDEX.md

## v1.5 라벨링 관리자 추가 색인

| 이름 | 종류 | 입력 | 출력 | 역할 | 비고 |
|---|---|---|---|---|---|
| `append_jsonl` | 함수 | record, output_path | 없음 | 관리자 피드백을 JSONL로 누적 저장 | `label_feedback.jsonl` |
| `build_video_analysis_result` | 함수 | 업로드 파일과 detector 설정 | 분석 result dict | 분석 데모와 라벨링 관리자가 같은 분석 초안을 공유 | v1.5 |
| `build_label_record` | 함수 | frame, feedback_type, bbox, tag, note | label record dict | TP/TN/FP/FN 피드백 저장 형식 생성 | `feedback_meaning` 포함 |
| `save_feedback_record` | 함수 | record, success_message | 없음 | 피드백 저장과 성공 메시지 표시를 공통 처리 | v1.5 |
| `render_existing_box_feedback_panel` | 함수 | frame index, frame path, selected item | 없음 | 기존 박스 TP/TN 평가 패널 표시 | 캔버스 오른쪽 패널 |
| `render_click_feedback` | 함수 | frame index, frame path, overlay items | 없음 | 기존 분석 박스 클릭 캔버스와 피드백 패널 표시 | TP/TN 저장 |
| `get_last_canvas_rect` | 함수 | canvas result, scale | bbox 또는 null | 드래그한 마지막 사각형을 원본 프레임 좌표로 변환 | v1.5 |
| `render_new_box_feedback_panel` | 함수 | frame index, frame path, bbox | 없음 | 새 박스 FP/FN 평가 패널 표시 | 캔버스 오른쪽 패널 |
| `render_drag_feedback` | 함수 | frame index, frame path, frame image | 없음 | 새 박스 드래그 캔버스와 피드백 패널 표시 | FP/FN 저장 |
| `render_labeling_admin` | 함수 | 분석 result dict | 없음 | 라벨링 관리자 전체 화면 표시 | v1.5 |
| `render_labeling_page` | 함수 | uploaded_file, detector_settings | 없음 | 라벨링용 분석 실행과 관리자 화면 연결 | v1.5 |
## v1.4.4 추가 색인

### src/evidence_pipeline.py

| 이름 | 종류 | 입력 | 출력 | 역할 | 비고 |
|---|---|---|---|---|---|
| `is_in_analysis_roi` | 함수 | `bbox_2d`, `frame_size` | bool | 화면 상단 광원과 하단 보닛/자막 영역을 약하게 제외 | 초기 ROI 휴리스틱 |
| `build_raw_evidence` | 함수 | evidence id, type, detection, reason | dict | 객체로 확정하지 않는 원시 관측값 생성 | 밝은 영역, 움직임 영역 |
| `build_object_candidate` | 함수 | candidate id, type, detection, evidence ids, reason | dict | 확정 전 객체 후보 생성 | YOLO 저신뢰, 전조등 쌍 |
| `is_confirmable_model_detection` | 함수 | detection, frame_size | bool | YOLO 결과가 최종 객체로 승격 가능한지 판단 | confidence와 ROI 기준 |
| `split_detections_by_certainty` | 함수 | model, light, motion detections, frame_size | raw_evidence, object_candidates, confirmed_objects, diagnostics | 검출 결과를 세 단계로 분리 | v1.4.4 핵심 |
| `build_overlay_items` | 함수 | scene_vector | overlay item 목록 | 세 레이어를 한 화면에 표시할 수 있게 변환 | 시각화용 |

### 변경된 핵심 함수

| 이름 | 변경 내용 |
|---|---|
| `app.analyze_sample_frames` | model/light/motion 결과를 `split_detections_by_certainty`로 분리 |
| `src.scene_vector.build_scene_vector` | `raw_evidence`, `object_candidates`, `objects`를 함께 출력 |
| `src.visualizer.draw_detection_overlay` | confirmed object, object candidate, raw evidence를 다른 색상 레이어로 표시 |
| `src.visualizer.draw_top_view` | 확정 `objects`만 2.5D 탑뷰에 표시 |
| `src.summarizer.summarize_scene` | 확정 객체 수와 후보/evidence 수를 분리 요약 |

## app.py

| 이름 | 종류 | 입력 | 출력 | 역할 | 비고 |
|---|---|---|---|---|---|
| `format_file_size` | 함수 | `byte_size` | 문자열 | 업로드 파일 크기를 읽기 쉬운 단위로 변환 | UI 표시용 |
| `clear_previous_frames` | 함수 | `frames_dir` | 없음 | 이전 샘플 프레임 정리 | 새 분석 결과 혼합 방지 |
| `save_json_data` | 함수 | `data`, `output_path` | 저장된 `Path` | dict 또는 list 데이터를 UTF-8 JSON으로 저장 | 단일/시퀀스 저장 공통 함수 |
| `save_scene_vector` | 함수 | `scene_vector`, `output_path` | 저장된 `Path` | Scene Vector JSON 파일 저장 | UTF-8 JSON 저장 |
| `save_scene_vectors` | 함수 | `scene_vectors`, `output_path` | 저장된 `Path` | 프레임별 Scene Vector 배열 저장 | `scene_vectors.json` 저장 |
| `load_frame_rgb` | 함수 | `frame_path` | BGR 프레임, RGB 프레임 | OpenCV 프레임을 앱 표시용으로 변환 | 읽기 실패 시 예외 |
| `show_video_metadata` | 함수 | `metadata` | 없음 | 영상 메타데이터를 Streamlit metric으로 표시 | v1.1 UI |
| `show_detector_settings` | 함수 | 없음 | backend, model_path, confidence_threshold, use_light_candidates, light_brightness_threshold, use_motion_assist | detector, 전조등 후보, 움직임 보조 설정을 사이드바에서 입력 | v1.4.3 UI |
| `show_runtime_status` | 함수 | 없음 | 없음 | 앱이 사용하는 Python 경로와 YOLO 설치 상태 표시 | 환경 혼선 진단 |
| `create_object_detector` | 함수 | `backend`, `model_path`, `confidence_threshold` | `ObjectDetector` 인스턴스 | Streamlit 모듈 캐시를 갱신한 뒤 detector 생성 | hot reload 안정화 |
| `analyze_sample_frames` | 함수 | `sample_frames`, `detector`, `frame_size`, `use_light_candidates`, `light_brightness_threshold`, `use_motion_assist` | scene_vectors, detections_by_frame, light_diagnostics_by_frame, motion_diagnostics_by_frame | 추출된 모든 샘플 프레임에 detector, 전조등 후보, 움직임 후보 검출 적용 | 제외 이유 진단 포함 |
| `store_sample_result` | 함수 | `scene_vector` | 없음 | 업로드 없이 실행한 샘플 결과 저장 | 세션 상태 사용 |
| `store_video_result` | 함수 | `metadata`, `sample_frames`, `scene_vectors`, `detections_by_frame`, `light_diagnostics_by_frame`, `motion_diagnostics_by_frame`, `detector_backend` | 없음 | 영상 분석 결과와 진단 정보를 파일과 세션 상태에 저장 | 단일/시퀀스 JSON 저장 |
| `render_sample_result` | 함수 | `scene_vector` | 없음 | 샘플 Scene Vector 결과 표시 | 업로드 없는 실행 경로 |
| `render_rejection_caption` | 함수 | `prefix`, `diagnostics` | 없음 | 제외 후보 진단 문구 표시 | 광원/움직임 공통 표시 |
| `render_video_result` | 함수 | `result` | 없음 | 슬라이더로 프레임별 분석 결과 표시 | 원본, 오버레이, JSON, 탑뷰 표시 |
| `render_analysis_result` | 함수 | 없음 | 없음 | 세션 상태의 분석 결과를 화면에 다시 표시 | 슬라이더 조작 시 결과 유지 |
| `main` | 함수 | 없음 | 없음 | Streamlit 앱 화면 구성 | 업로드 영상 기반 더미/YOLO 시퀀스 분석 연결 |

## src/video_loader.py

| 이름 | 종류 | 입력 | 출력 | 역할 | 비고 |
|---|---|---|---|---|---|
| `save_uploaded_video` | 함수 | `uploaded_file`, `save_dir` | 저장된 `Path` | Streamlit 업로드 파일을 디스크에 저장 | 파일 없음 또는 저장 실패 시 예외 |
| `get_video_metadata` | 함수 | `video_path` | 메타데이터 dict | FPS, 프레임 수, 해상도, 길이 확인 | OpenCV 사용 |
| `extract_sample_frames` | 함수 | `video_path`, `output_dir`, `sample_fps`, `max_frames` | 프레임 경로 목록 | 지정한 초당 샘플 수로 이미지 추출 | 최대 프레임 수 제한 가능 |

## src/detector.py

| 이름 | 종류 | 입력 | 출력 | 역할 | 비고 |
|---|---|---|---|---|---|
| `SUPPORTED_YOLO_TYPES` | 상수 | 없음 | set | Scene Vector로 변환할 YOLO 클래스 제한 | 사람, 자전거, 차량 계열 |
| `ObjectDetector` | 클래스 | `backend`, `model_path`, `confidence_threshold` | 인스턴스 | 더미 또는 YOLO detector 백엔드 선택 | YOLO는 데모용 백엔드 |
| `ObjectDetector.detect_objects` | 메서드 | `frame` | detection 목록 | 프레임에서 객체 검출 결과 반환 | 공통 detection dict 반환 |
| `ObjectDetector._load_yolo_model` | 메서드 | 없음 | YOLO 모델 | Ultralytics YOLO 지연 로딩 | 미설치/로딩 실패 시 한국어 오류 |
| `ObjectDetector._detect_dummy` | 메서드 | `frame` | detection 목록 | 프레임 크기 기반 더미 bbox 반환 | 파이프라인 검증용 |
| `ObjectDetector._detect_yolo` | 메서드 | `frame` | detection 목록 | YOLO 결과를 공통 detection 형식으로 변환 | bbox는 `[x, y, width, height]` |

## src/light_candidate_detector.py

| 이름 | 종류 | 입력 | 출력 | 역할 | 비고 |
|---|---|---|---|---|---|
| `calculate_iou` | 함수 | 두 bbox | IoU 값 | 모델 detection과 전조등 후보의 중복 여부 계산 | 병합용 |
| `build_rejected_light` | 함수 | reason, bbox | 제외 기록 dict | Scene Vector에 넣지 않은 광원 후보 기록 | v1.4.2 진단 |
| `summarize_rejections` | 함수 | rejected_lights | reason별 count | 제외 이유 집계 | 앱 표시용 |
| `get_artifact_zone_reason` | 함수 | blob, frame_size | reason 또는 None | 보닛, 상단 광원, 측면 간판, 긴 반사선 제외 판단 | v1.4.2 |
| `build_light_mask` | 함수 | `frame`, `brightness_threshold` | mask | 흰색/노란색 고휘도 영역 분리 | OpenCV HSV 기반 |
| `extract_light_blobs` | 함수 | `frame`, `brightness_threshold` | blob 목록 | 고휘도 영역을 bbox 후보로 변환 | 노이즈, 큰 번짐, 길게 늘어진 잔상 제거 |
| `extract_light_blobs_with_rejections` | 함수 | `frame`, `brightness_threshold` | blob 목록, 제외 기록 목록 | 후보 blob과 제외된 광원 이유를 함께 반환 | v1.4.2 |
| `is_headlight_pair` | 함수 | 두 blob, `frame_width`, `frame_height` | bool | 나란한 전조등 쌍 후보 판단 | 위치와 대칭성 휴리스틱 |
| `build_pair_detection` | 함수 | 두 blob, `track_id` | detection dict | 전조등 쌍을 차량 후보로 변환 | `car/headlight_pair` |
| `build_single_light_detection` | 함수 | blob, `track_id` | detection dict | 단일 고휘도 blob을 unknown 후보로 변환 | `unknown/possible_vehicle_headlight` |
| `should_keep_single_light_candidate` | 함수 | blob, frame_size | bool | 단일 광원 후보를 엄격하게 필터링 | 가로등/물방울 잔상 오탐 완화 |
| `get_single_light_rejection_reason` | 함수 | blob, frame_size | reason 또는 None | 단일 광원 후보 제외 이유 판단 | v1.4.2 |
| `apply_temporal_boost` | 함수 | candidates, previous_candidates, frame_size | detection 목록 | 이전 샘플 프레임과 이어지는 후보 신뢰도 보강 | `temporal_motion` source 추가 |
| `detect_light_candidates` | 함수 | `frame`, `previous_candidates`, `brightness_threshold` | detection 목록 | 야간 전조등/고휘도 객체 후보 검출 | 호환용 |
| `detect_light_candidates_with_diagnostics` | 함수 | `frame`, `previous_candidates`, `brightness_threshold` | detection 목록, diagnostics | 후보와 제외 이유 집계를 함께 반환 | v1.4.2 핵심 보강 |
| `merge_detections` | 함수 | model_detections, light_candidates, iou_threshold | detection 목록 | 모델 검출과 전조등 후보 병합 | 중복 bbox 보강 |

## src/motion_candidate_detector.py

| 이름 | 종류 | 입력 | 출력 | 역할 | 비고 |
|---|---|---|---|---|---|
| `build_motion_mask` | 함수 | `previous_frame`, `current_frame`, `diff_threshold` | motion mask | 이전/현재 프레임 차분으로 움직임 영역 mask 생성 | OpenCV 기반 |
| `get_motion_artifact_reason` | 함수 | `bbox_2d`, `frame_size` | reason 또는 None | 보닛 반사, 상단 광원, 가장자리 변화 등 제외 판단 | 오탐 완화 |
| `extract_motion_candidates` | 함수 | `previous_frame`, `current_frame`, `min_area_ratio`, `diff_threshold` | 후보 detection 목록, diagnostics | 기존 detector가 놓친 움직임 영역을 `unknown/motion_region` 후보로 변환 | v1.4.3 핵심 보강 |
| `calculate_bbox_motion_score` | 함수 | `bbox_2d`, `motion_mask` | score | 기존 detection bbox와 motion mask의 겹침 비율 계산 | temporal 검증 |
| `annotate_detections_with_motion` | 함수 | `detections`, `previous_frame`, `current_frame`, `motion_threshold` | 보강 detection 목록, diagnostics | 기존 YOLO/전조등 후보에 `motion_score`, `motion_flow`, `temporal_verified` 근거 추가 | 신뢰도 보강 |
| `merge_motion_candidates` | 함수 | `detections`, `motion_candidates`, `iou_threshold` | detection 목록 | 기존 후보와 겹치지 않는 움직임 후보만 병합 | 중복 bbox 방지 |

## src/position_estimator.py

| 이름 | 종류 | 입력 | 출력 | 역할 | 비고 |
|---|---|---|---|---|---|
| `estimate_position_3d` | 함수 | `bbox_2d`, `frame_width`, `frame_height`, `object_type` | 위치 추정 dict | bbox 하단 중심점과 크기로 3D 위치를 추정 | 정밀 복원이 아닌 휴리스틱 |

## src/scene_vector.py

| 이름 | 종류 | 입력 | 출력 | 역할 | 비고 |
|---|---|---|---|---|---|
| `classify_distance_zone` | 함수 | `distance_y` | 문자열 | 전방 거리 구간 분류 | `near`, `mid`, `far` |
| `classify_lane_position` | 함수 | `position_x` | 문자열 | 좌우 차로 위치 분류 | 좌측, 중앙, 우측 |
| `build_scene_vector` | 함수 | `frame_index`, `timestamp`, `detections`, `frame_size` | Scene Vector dict | detection 목록을 Scene Vector JSON 구조로 변환 | 위치 추정 포함 |
| `build_sample_scene_vector` | 함수 | 없음 | Scene Vector dict | 앱 검증용 샘플 Scene Vector 생성 | 업로드 없이 실행 가능 |

## src/visualizer.py

| 이름 | 종류 | 입력 | 출력 | 역할 | 비고 |
|---|---|---|---|---|---|
| `get_detection_color_bgr` | 함수 | detection | BGR 색상 tuple | 오버레이에서 YOLO, 전조등, 움직임 후보 색상 구분 | v1.4.3 |
| `get_top_view_color` | 함수 | Scene Vector object | Matplotlib 색상 문자열 | 탑뷰에서 검출 출처별 색상 구분 | v1.4.3 |
| `draw_detection_overlay` | 함수 | `frame`, `detections` | 그려진 프레임 | OpenCV로 bbox와 라벨 표시 | 실제 프레임 연결 대비 |
| `estimate_top_view_box_size` | 함수 | Scene Vector object | width, length | 객체 타입별 기본 크기와 bbox 면적 보정으로 탑뷰 박스 크기 산정 | v1.4.1 |
| `draw_top_view` | 함수 | `scene_vector` | Matplotlib figure | 자차와 객체의 추정 위치 및 타입별 크기 박스를 탑뷰로 표시 | 2.5D 시각화 |

## src/summarizer.py

| 이름 | 종류 | 입력 | 출력 | 역할 | 비고 |
|---|---|---|---|---|---|
| `summarize_scene` | 함수 | `scene_vector` | 한국어 문장 | 객체 수, 위치 구간, 신뢰도를 요약 | 규칙 기반 |
