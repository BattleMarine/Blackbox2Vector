# PROJECT_MAP.md

## 전체 폴더 구조

```text
blackbox2vector/
├─ README.md
├─ AGENTS.md
├─ .gitignore
├─ requirements.txt
├─ app.py
├─ data/
│  ├─ input/
│  ├─ frames/
│  └─ output/
├─ src/
│  ├─ __init__.py
│  ├─ video_loader.py
│  ├─ detector.py
│  ├─ light_candidate_detector.py
│  ├─ position_estimator.py
│  ├─ scene_vector.py
│  ├─ visualizer.py
│  └─ summarizer.py
└─ docs/
   ├─ PROJECT_MAP.md
   ├─ CODE_INDEX.md
   ├─ SCENE_VECTOR_SCHEMA.md
   ├─ DECISIONS.md
   └─ DEBUG_NOTES.md
```

## 각 폴더 역할

| 폴더 | 역할 |
|---|---|
| `data/input/` | 업로드된 원본 블랙박스 영상을 저장할 위치 |
| `data/frames/` | 영상에서 추출한 샘플 프레임 저장 위치 |
| `data/output/` | Scene Vector JSON 등 분석 결과 저장 위치 |
| `src/` | 앱의 핵심 처리 모듈 |
| `docs/` | 구조, 스키마, 의사결정, 디버깅 문서 |

## 주요 파일 역할

| 파일 | 역할 |
|---|---|
| `app.py` | Streamlit 데모 앱 진입점 |
| `requirements.txt` | 초기 실행 의존성 목록 |
| `.gitignore` | 캐시, 가상환경, 로컬 데이터, 비밀 설정 파일 제외 규칙 |
| `src/video_loader.py` | 영상 저장, 메타데이터 조회, 샘플 프레임 추출 |
| `src/detector.py` | 객체 검출 백엔드 인터페이스, 더미 detection, YOLO detection |
| `src/light_candidate_detector.py` | 야간 전조등/고휘도 blob 후보 검출과 detection 병합 |
| `src/position_estimator.py` | 2D bbox 기반 3D 위치 추정 |
| `src/scene_vector.py` | Scene Vector JSON 생성 |
| `src/visualizer.py` | bbox 오버레이와 2.5D 탑뷰 시각화 |
| `src/summarizer.py` | 규칙 기반 장면 요약 |

## 데모 v1.4.2 데이터 흐름

```text
Streamlit 앱
  -> 영상 업로드 UI
  -> data/input/에 업로드 영상 저장
  -> OpenCV 영상 메타데이터 조회
  -> data/frames/에 샘플 프레임 추출
  -> 사이드바 detector backend 선택
  -> 추출된 모든 샘플 프레임 로드
  -> 프레임별 더미 또는 YOLO detection 생성
  -> 프레임별 전조등/고휘도 blob 후보 생성
  -> blob 형태, 크기, 화면 위치, 전조등 쌍 구조 기준으로 오탐 필터링
  -> Scene Vector 제외 광원/반사의 이유 집계
  -> 이전 샘플 프레임 후보와 이어지는 경우 temporal 후보 보강
  -> 모델 detection과 전조등 후보 병합
  -> 프레임별 bbox 오버레이 생성
  -> 프레임별 2D bbox 기반 위치 추정
  -> Scene Vector JSON 시퀀스 생성
  -> data/output/scene_vector.json 저장
  -> data/output/scene_vectors.json 저장
  -> 슬라이더로 선택한 프레임의 장면 요약 생성
  -> 슬라이더로 선택한 프레임의 원본, 오버레이, 타입별 크기 2.5D 탑뷰 표시
  -> JSON 다운로드 제공
```

현재 앱은 실제 업로드 영상을 저장하고 샘플 프레임을 추출합니다. 객체 검출은 더미 detector와 Ultralytics YOLO detector 중 선택할 수 있습니다. v1.4.2에서는 YOLO가 놓치기 쉬운 야간 전조등/고휘도 후보를 별도 detection 후보로 보존하되, 가로등과 빛번짐 오탐을 줄이기 위해 후보 검증 기준을 더 엄격하게 적용합니다. 제외된 광원/반사는 Scene Vector에 넣지 않고 프레임별 제외 이유만 앱에 표시합니다. 2.5D 탑뷰는 고정 마커 대신 객체 타입별 추정 물리 크기 박스로 표시합니다.
