# CODE_INDEX.md

## app.py

| 이름 | 종류 | 입력 | 출력 | 역할 | 비고 |
|---|---|---|---|---|---|
| `format_file_size` | 함수 | `byte_size` | 문자열 | 업로드 파일 크기를 읽기 쉬운 단위로 변환 | UI 표시용 |
| `main` | 함수 | 없음 | 없음 | Streamlit 앱 화면 구성 | 샘플 Scene Vector 표시 |

## src/video_loader.py

| 이름 | 종류 | 입력 | 출력 | 역할 | 비고 |
|---|---|---|---|---|---|
| `save_uploaded_video` | 함수 | `uploaded_file`, `save_dir` | 저장된 `Path` | Streamlit 업로드 파일을 디스크에 저장 | 파일 없음 또는 저장 실패 시 예외 |
| `get_video_metadata` | 함수 | `video_path` | 메타데이터 dict | FPS, 프레임 수, 해상도, 길이 확인 | OpenCV 사용 |
| `extract_sample_frames` | 함수 | `video_path`, `output_dir`, `sample_fps` | 프레임 경로 목록 | 지정한 초당 샘플 수로 이미지 추출 | 추출 실패 시 예외 |

## src/detector.py

| 이름 | 종류 | 입력 | 출력 | 역할 | 비고 |
|---|---|---|---|---|---|
| `ObjectDetector` | 클래스 | `model_path` | 인스턴스 | 추후 YOLO 모델을 감싸는 객체 검출기 | 현재는 더미 구현 |
| `ObjectDetector.detect_objects` | 메서드 | `frame` | detection 목록 | 프레임에서 객체 검출 결과 반환 | 현재 고정 샘플 반환 |

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
