# CODE_INDEX.md

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
| `show_detector_settings` | 함수 | 없음 | backend, model_path, confidence_threshold | detector 설정을 사이드바에서 입력 | v1.2 UI |
| `show_runtime_status` | 함수 | 없음 | 없음 | 앱이 사용하는 Python 경로와 YOLO 설치 상태 표시 | 환경 혼선 진단 |
| `create_object_detector` | 함수 | `backend`, `model_path`, `confidence_threshold` | `ObjectDetector` 인스턴스 | Streamlit 모듈 캐시를 갱신한 뒤 detector 생성 | hot reload 안정화 |
| `analyze_sample_frames` | 함수 | `sample_frames`, `detector`, `frame_size` | scene_vectors, detections_by_frame | 추출된 모든 샘플 프레임에 detector 적용 | v1.3 시퀀스 분석 |
| `store_sample_result` | 함수 | `scene_vector` | 없음 | 업로드 없이 실행한 샘플 결과 저장 | 세션 상태 사용 |
| `store_video_result` | 함수 | `metadata`, `sample_frames`, `scene_vectors`, `detections_by_frame`, `detector_backend` | 없음 | 영상 분석 결과를 파일과 세션 상태에 저장 | 단일/시퀀스 JSON 저장 |
| `render_sample_result` | 함수 | `scene_vector` | 없음 | 샘플 Scene Vector 결과 표시 | 업로드 없는 실행 경로 |
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
| `draw_detection_overlay` | 함수 | `frame`, `detections` | 그려진 프레임 | OpenCV로 bbox와 라벨 표시 | 실제 프레임 연결 대비 |
| `draw_top_view` | 함수 | `scene_vector` | Matplotlib figure | 자차와 객체의 추정 위치를 탑뷰로 표시 | 2.5D 시각화 |

## src/summarizer.py

| 이름 | 종류 | 입력 | 출력 | 역할 | 비고 |
|---|---|---|---|---|---|
| `summarize_scene` | 함수 | `scene_vector` | 한국어 문장 | 객체 수, 위치 구간, 신뢰도를 요약 | 규칙 기반 |
