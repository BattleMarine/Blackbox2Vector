# AGENTS.md

## 목적

이 문서는 BlackBox2Vector 프로젝트를 사람이든 AI 에이전트든 일관성 있게 개발하기 위한 공개 작업 지침서입니다.

BlackBox2Vector는 2D 블랙박스 영상을 입력받아 객체, 차선, 도로 기준선, 움직임 정보를 추출하고, 이를 자차 기준 3D Scene Vector JSON 데이터로 변환하는 데모 프로젝트입니다.

데모 v1은 정밀 3D 복원 시스템이 아닙니다. 2D 영상에서 추정 가능한 정보를 바탕으로 객체의 3D 위치 벡터, 움직임 벡터, 신뢰도, 추정 범위를 JSON으로 저장하는 것을 목표로 합니다.

## 언어 정책

다음 항목은 한국어로 작성합니다.

- 에이전트 응답
- 코드 주석
- README.md
- AGENTS.md
- docs 문서
- TODO 목록
- 로그 설명
- 커밋 메시지

변수명, 함수명, 클래스명, 라이브러리명, API명, 파일명, 표준 기술 용어는 영어를 사용할 수 있습니다.

## 작업 시작 전 확인 절차

작업을 시작하기 전에 다음 문서를 확인합니다.

1. README.md
2. AGENTS.md
3. docs/PROJECT_MAP.md
4. 작업과 관련된 docs 문서

문서가 아직 없으면 작업 중 생성합니다.

## 문서 읽기 우선순위

| 상황 | 확인 문서 |
|---|---|
| 항상 | README.md, AGENTS.md, docs/PROJECT_MAP.md |
| Scene Vector JSON 변경 | docs/SCENE_VECTOR_SCHEMA.md |
| 함수, 클래스, 파일 구조 변경 | docs/CODE_INDEX.md |
| 기술 선택이나 구조 결정 변경 | docs/DECISIONS.md |
| 반복 가능한 오류 수정 | docs/DEBUG_NOTES.md |

## 개발 원칙

- 요청된 작업과 직접 관련 없는 코드는 수정하지 않습니다.
- 불필요한 리팩토링을 수행하지 않습니다.
- 가능한 가장 단순한 구조를 우선합니다.
- 함수는 하나의 역할만 수행합니다.
- 예외를 조용히 무시하지 않습니다.
- 경로 처리는 `pathlib.Path`를 우선 사용합니다.
- 실제 모델이 없는 부분은 dummy 또는 placeholder임을 명확히 표시합니다.
- 정밀하지 않은 3D 추정값은 estimated임을 코드와 문서에 드러냅니다.
- 과도한 추상화와 불필요한 패키지 추가를 피합니다.
- 기존 내용을 무단으로 삭제하지 않습니다.

## 기술 스택 기준

데모 v1은 Python을 주 언어로 사용합니다.

기본 기술 스택은 다음과 같습니다.

- Python 3.10 이상 권장
- Streamlit
- OpenCV
- NumPy
- Matplotlib
- Pandas
- JSON
- Ultralytics YOLO

추후 도입 후보는 다음과 같습니다.

- Plotly
- PyTorch
- FFmpeg
- Open3D

v1.2에서 Ultralytics YOLO는 데모용 실제 객체 검출 백엔드로 사용합니다. v1.4에서는 YOLO가 놓치기 쉬운 야간 전조등/고휘도 후보를 OpenCV 기반 보조 detector로 보존합니다. v1.4.3에서는 샘플 프레임 간 차분으로 움직임 후보를 보강합니다. 다만 장기 구조에서는 YOLO나 특정 휴리스틱에 종속되지 않도록 detector 백엔드와 후보 생성 모듈을 분리해 유지합니다.

## 데모 v1에서 하지 말 것

- 정밀 3D 복원
- 실시간 처리
- 실제 LiDAR 센서 연동
- 법적 사고 판단
- 자율주행 모델 학습
- GPT API 연동
- 전후방 카메라 Re-ID
- 복잡한 차선 검출 알고리즘
- 데이터베이스 연동
- 복잡한 백엔드 서버 구축
- 불필요한 대규모 리팩토링

## 프로젝트 구조 기준

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
│  ├─ motion_candidate_detector.py
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

## 주요 모듈 역할

| 파일 | 역할 |
|---|---|
| app.py | Streamlit 데모 앱 진입점 |
| src/video_loader.py | 영상 저장, 메타데이터 확인, 프레임 추출 |
| src/detector.py | 객체 검출 백엔드, 더미와 YOLO 검출 지원 |
| src/light_candidate_detector.py | 야간 전조등/고휘도 후보 검출과 병합 |
| src/motion_candidate_detector.py | 프레임 차분 기반 움직임 후보 검출과 기존 후보 보강 |
| src/position_estimator.py | 2D bbox 기반 3D 위치 추정 |
| src/scene_vector.py | Scene Vector JSON 생성 |
| src/visualizer.py | 검출 결과 및 2.5D/3D 시각화 |
| src/summarizer.py | 규칙 기반 장면 요약 생성 |

## Scene Vector JSON 규칙

Scene Vector JSON은 데모 v1의 핵심 출력물입니다.

기본 좌표계는 자차 기준 3D 좌표계입니다.

```text
원점: 자차 위치
x: 오른쪽 양수, 왼쪽 음수
y: 전방 양수
z: 위쪽 양수, 도로면 0
단위: meter_estimated
```

초기 데모에서는 객체가 도로 위에 있다고 가정하고 z 좌표는 기본적으로 `0.0`으로 둡니다.

모든 3D 좌표는 정밀 측정값이 아니라 영상 기반 추정값입니다. 따라서 `position_3d`에는 반드시 다음 정보를 포함합니다.

- estimate
- range
- confidence

## 코드 작성 규칙

- 주석은 무엇을 하는지보다 왜 필요한지를 설명합니다.
- 더미 구현에는 추후 교체 방향을 주석으로 남깁니다.
- 오류가 발생하면 사용자가 원인을 파악할 수 있도록 메시지를 남깁니다.
- 외부에서 호출되는 주요 함수와 클래스는 docs/CODE_INDEX.md에 기록합니다.

## 문서화 규칙

- 구조가 바뀌면 docs/PROJECT_MAP.md를 갱신합니다.
- 공개 함수나 클래스가 바뀌면 docs/CODE_INDEX.md를 갱신합니다.
- JSON 구조가 바뀌면 docs/SCENE_VECTOR_SCHEMA.md를 갱신합니다.
- 설계 결정이 바뀌면 docs/DECISIONS.md를 갱신합니다.
- 재발 가능성이 있는 오류만 docs/DEBUG_NOTES.md에 기록합니다.

## Git 커밋 규칙

커밋은 작고 의미 있는 단위로 수행합니다.

커밋 메시지는 한국어로 작성합니다.

```text
<type>: 변경사항 요약

- 세부 내용 1
- 세부 내용 2
- 세부 내용 3
```

예시:

```text
feat: Streamlit 초기 데모 앱 구현

- 프로젝트 제목과 데모 목표 표시
- 영상 업로드 UI 추가
- 샘플 Scene Vector JSON 출력 추가
```

커밋 타입은 다음을 사용합니다.

- feat: 기능 추가
- fix: 버그 수정
- refactor: 리팩토링
- docs: 문서 수정
- style: 코드 스타일 수정
- test: 테스트 관련
- chore: 기타 작업

## 초기 빌드 성공 기준

- 프로젝트 구조가 생성되어 있습니다.
- README.md와 AGENTS.md가 존재합니다.
- docs 문서들이 존재합니다.
- `pip install -r requirements.txt`로 의존성 설치가 가능합니다.
- `streamlit run app.py`로 앱을 실행할 수 있습니다.
- 앱에서 샘플 Scene Vector JSON을 확인할 수 있습니다.
- 주요 파일과 함수가 docs/CODE_INDEX.md에 정리되어 있습니다.
- Scene Vector JSON 구조가 docs/SCENE_VECTOR_SCHEMA.md에 정리되어 있습니다.
