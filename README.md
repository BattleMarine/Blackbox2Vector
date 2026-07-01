# BlackBox2Vector

BlackBox2Vector는 2D 블랙박스 영상을 입력받아 객체, 차선, 도로 기준선, 움직임 정보를 추출하고, 이를 자차 기준 3D Scene Vector JSON 데이터로 변환하기 위한 데모 프로젝트입니다.

데모 v1은 정밀한 3D 복원 시스템이 아닙니다. 2D 영상에서 추정 가능한 정보를 바탕으로 객체의 3D 위치 벡터, 움직임 벡터, 신뢰도, 추정 범위를 JSON으로 저장하는 초기 구조를 검증합니다.

핵심 산출물은 `scene_vector.json`입니다.

## 데모 v1 목표

- Python + Streamlit 기반 최소 실행 앱 제공
- 영상 업로드 UI와 샘플 분석 결과 표시
- 추후 YOLO 연결이 가능한 detector 모듈 구조 마련
- 2D bbox 기반 3D 위치 추정 초안 구현
- Scene Vector JSON 스키마 초안과 문서화
- 2.5D 탑뷰 시각화 데모 제공

## 핵심 기능

- 블랙박스 영상 업로드 UI
- 업로드 파일 이름과 크기 표시
- 샘플 Scene Vector JSON 생성
- 규칙 기반 장면 요약
- Matplotlib 기반 간단한 2.5D 탑뷰 표시
- OpenCV 기반 프레임 추출 유틸리티 준비

## 데모 v1에서 제외하는 기능

- 실제 YOLO 추론 완성
- 고급 차선 검출
- 실제 LiDAR 연동
- 실시간 처리
- 복잡한 3D 렌더링
- 데이터베이스 연동
- GPT API 연동
- 법적 사고 판단 로직

## 시스템 흐름

```text
영상 업로드
  -> 영상 저장 및 메타데이터 확인
  -> 샘플 프레임 추출
  -> 객체 검출
  -> 2D bbox 기반 3D 위치 추정
  -> Scene Vector JSON 생성
  -> 요약 및 2.5D 탑뷰 표시
```

현재 데모 앱은 실제 영상 분석 대신 샘플 Scene Vector JSON을 표시합니다.

## Scene Vector JSON 요약

Scene Vector JSON은 자차를 원점으로 하는 추정 좌표계 안에서 객체의 위치, 움직임, 상태를 표현합니다.

주요 필드는 다음과 같습니다.

| 필드 | 의미 |
|---|---|
| `scene_id` | 장면 식별자 |
| `timestamp` | 영상 내 시간 |
| `coordinate_system` | 자차 기준 좌표계 정의 |
| `ego_vehicle` | 자차 위치와 진행 방향 |
| `objects` | 검출 객체 목록 |
| `events` | 장면 이벤트 목록 |

## 좌표계 정의

```text
원점: 자차 위치
x: 오른쪽이 양수
y: 전방이 양수
z: 위쪽이 양수
단위: meter_estimated
```

데모 v1에서는 객체가 도로면 위에 있다고 가정하므로 `z`는 기본적으로 `0.0`입니다. 모든 3D 위치는 정밀 측정값이 아니라 영상 기반 추정값입니다.

## 기술 스택

- Python
- Streamlit
- OpenCV
- NumPy
- Matplotlib
- Pandas
- JSON

추후 객체 검출은 Ultralytics YOLO 기반으로 연결할 예정입니다.

## 프로젝트 구조

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

## 실행 방법

```bash
pip install -r requirements.txt
streamlit run app.py
```

브라우저에서 Streamlit이 안내하는 로컬 주소를 열면 데모 앱을 확인할 수 있습니다.

## 현재 진행 상황

- 초기 프로젝트 폴더 구조 생성 완료
- Streamlit 데모 앱 작성 완료
- 더미 객체 검출 모듈 작성 완료
- 2D bbox 기반 3D 위치 추정 초안 작성 완료
- Scene Vector JSON 생성 모듈 작성 완료
- 탑뷰 시각화와 장면 요약 모듈 작성 완료
- 주요 문서 초안 작성 완료
- Streamlit 로컬 실행 확인 완료
- GitHub 공개 커밋을 위한 민감정보 스캔 및 `.gitignore` 작성 완료

## 다음 작업

1. 업로드 영상을 `data/input/`에 저장하는 흐름을 앱에 실제 연결
2. OpenCV 프레임 추출 결과를 앱 화면에 표시
3. Ultralytics YOLO 객체 검출 연결
4. 프레임별 Scene Vector JSON 저장 기능 추가
5. 차선과 도로 기준선 추정 모듈 설계

## 의사결정 기록

초기 의사결정은 [docs/DECISIONS.md](docs/DECISIONS.md)에 기록합니다.

## 한계 및 주의사항

- 데모 v1의 3D 좌표는 정밀 복원 결과가 아닙니다.
- 거리 추정은 카메라 캘리브레이션 없이 bbox 위치와 크기를 이용한 휴리스틱입니다.
- 현재 객체 검출 결과는 더미 데이터입니다.
- 법적 사고 판단이나 운전자 과실 판단에는 사용할 수 없습니다.
