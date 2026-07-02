# BlackBox2Vector

BlackBox2Vector는 2D 블랙박스 영상을 입력받아 객체, 차선, 도로 기준선, 움직임 정보를 추출하고, 이를 자차 기준 3D Scene Vector JSON 데이터로 변환하기 위한 데모 프로젝트입니다.

데모 v1.4는 정밀한 3D 복원 시스템이 아닙니다. 업로드한 동영상에서 샘플 프레임 시퀀스를 추출하고, 더미 detector 또는 Ultralytics YOLO 데모 백엔드 결과에 야간 전조등/고휘도 후보 검출을 더해 객체의 3D 위치 벡터, 움직임 벡터, 신뢰도, 추정 범위를 JSON으로 저장하는 초기 파이프라인을 검증합니다.

핵심 산출물은 단일 프레임 호환용 `scene_vector.json`과 샘플 프레임 시퀀스용 `scene_vectors.json`입니다.

## 데모 v1.4 목표

- Python + Streamlit 기반 최소 실행 앱 제공
- 영상 업로드, 저장, 메타데이터 표시
- OpenCV 기반 샘플 프레임 추출
- 추출된 샘플 프레임 전체에 더미 또는 YOLO detection 적용
- YOLO가 놓치기 쉬운 야간 전조등/고휘도 객체 후보 보존
- 앞 프레임의 고휘도 후보와 이어지는 temporal 후보 신뢰도 보강
- 슬라이더 기반 샘플 프레임 시퀀스 탐색 UI 제공
- YOLO에 종속되지 않는 detector backend 선택 구조 마련
- 2D bbox 기반 3D 위치 추정 초안 구현
- Scene Vector JSON 스키마 초안과 문서화
- 2.5D 탑뷰 시각화 데모 제공
- `data/output/scene_vector.json` 및 `data/output/scene_vectors.json` 저장 및 다운로드 제공

## 핵심 기능

- 블랙박스 영상 업로드 UI
- 업로드 파일 이름과 크기 표시
- 영상 메타데이터 표시
- 샘플 프레임 추출 및 시퀀스 표시
- 슬라이더를 통한 프레임별 원본/오버레이/JSON/탑뷰 전환
- 더미 detection 오버레이 표시
- YOLO detection 오버레이 표시
- 전조등/고휘도 후보 오버레이 표시
- 프레임별 Scene Vector JSON 생성 및 저장
- detection 근거와 후보 여부를 JSON에 기록
- JSON 다운로드 버튼 제공
- 규칙 기반 장면 요약
- Matplotlib 기반 간단한 2.5D 탑뷰 표시
- OpenCV 기반 프레임 추출 유틸리티 준비

## 데모 v1.4에서 제외하는 기능

- YOLO 외 고급 비전 모델 연결
- 고급 차선 검출
- 실제 LiDAR 연동
- 실시간 처리
- 복잡한 3D 렌더링
- 데이터베이스 연동
- GPT API 연동
- 법적 사고 판단 로직
- 프레임 간 동일 객체 추적
- 실제 속도 기반 움직임 벡터 추정
- 도로 ROI 기반 강한 필터링

## 시스템 흐름

```text
영상 업로드
  -> 영상 저장 및 메타데이터 확인
  -> 샘플 프레임 추출
  -> detector backend 선택
  -> 모든 샘플 프레임에 더미 또는 YOLO 객체 검출 적용
  -> 야간 전조등/고휘도 blob 후보 검출
  -> 앞 프레임의 고휘도 후보와 이어지는 경우 temporal 후보 보강
  -> 모델 검출과 고휘도 후보 병합
  -> 프레임별 2D bbox 기반 3D 위치 추정
  -> Scene Vector JSON 시퀀스 생성
  -> 슬라이더로 프레임별 요약, 오버레이, 2.5D 탑뷰 표시
```

현재 데모 앱은 업로드 영상에서 최대 12개의 샘플 프레임을 추출합니다. 객체 검출은 데모용 YOLO 백엔드 또는 프레임 크기에 맞춘 더미 detection 중 선택할 수 있으며, 야간 전조등/고휘도 후보 보존을 함께 켤 수 있습니다. 슬라이더로 샘플 프레임을 넘기며 결과를 확인할 수 있습니다.

## Scene Vector JSON 요약

Scene Vector JSON은 자차를 원점으로 하는 추정 좌표계 안에서 객체의 위치, 움직임, 상태를 표현합니다.

`scene_vector.json`은 첫 번째 샘플 프레임 결과를 담는 단일 객체 형식입니다. `scene_vectors.json`은 같은 구조의 Scene Vector 객체를 프레임 순서대로 담은 배열입니다.

주요 필드는 다음과 같습니다.

| 필드 | 의미 |
|---|---|
| `scene_id` | 장면 식별자 |
| `timestamp` | 영상 내 시간 |
| `coordinate_system` | 자차 기준 좌표계 정의 |
| `ego_vehicle` | 자차 위치와 진행 방향 |
| `objects` | 검출 객체 목록 |
| `events` | 장면 이벤트 목록 |

v1.4부터 객체 항목에는 `subtype`, `detection_sources`, `detection_reason`, `is_candidate`가 포함됩니다. 이 필드는 YOLO가 차량 형상을 놓친 야간 장면에서도 전조등 기반 후보를 `unknown` 또는 `car/headlight_pair`로 보존하기 위해 사용합니다.

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
- Ultralytics YOLO

YOLO는 데모 버전의 실제 객체 검출 백엔드로 사용합니다. 장기 구조에서는 YOLO를 기준선 백엔드로 두고, 다른 비전 모델이나 segmentation, depth, tracking 백엔드를 추가할 수 있도록 detector 인터페이스를 유지합니다.

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

## 실행 방법

```bash
pip install -r requirements.txt
streamlit run app.py
```

브라우저에서 Streamlit이 안내하는 로컬 주소를 열면 데모 앱을 확인할 수 있습니다.

YOLO 백엔드를 처음 사용할 때 `yolov8n.pt` 가중치가 로컬에 없으면 Ultralytics가 다운로드를 시도할 수 있습니다. 네트워크가 제한된 환경에서는 모델 파일을 미리 내려받은 뒤 앱 사이드바의 `YOLO 모델 경로`에 로컬 경로를 입력합니다.

## 현재 진행 상황

- 초기 프로젝트 폴더 구조 생성 완료
- Streamlit 데모 앱 작성 완료
- 업로드 영상 저장과 메타데이터 표시 연결 완료
- 샘플 프레임 추출과 화면 표시 연결 완료
- 프레임 크기 기반 더미 객체 검출 모듈 작성 완료
- Ultralytics YOLO 데모 백엔드 추가 완료
- 앱 사이드바 detector backend 선택 UI 추가 완료
- 추출된 샘플 프레임 전체에 detector 적용 완료
- 슬라이더 기반 샘플 프레임 시퀀스 탐색 UI 추가 완료
- 야간 전조등/고휘도 후보 검출 모듈 추가 완료
- 전조등 후보와 모델 detection 병합 구조 추가 완료
- 2D bbox 기반 3D 위치 추정 초안 작성 완료
- Scene Vector JSON 단일/시퀀스 파일 저장 완료
- `scene_vector.json` 및 `scene_vectors.json` 다운로드 버튼 추가 완료
- 탑뷰 시각화와 장면 요약 모듈 작성 완료
- 주요 문서 초안 작성 완료
- Streamlit 로컬 실행 확인 완료
- GitHub 공개 커밋을 위한 민감정보 스캔 및 `.gitignore` 작성 완료

## 다음 작업

1. 프레임 간 객체 추적과 움직임 벡터 추정
2. YOLO track 모드 또는 별도 tracker 백엔드 검토
3. 전조등 후보 threshold와 pairing 기준을 실제 야간 영상으로 튜닝
4. 차선과 도로 기준선 추정 모듈 설계
5. 샘플링 FPS와 최대 프레임 수 UI 조정 기능 추가

## 의사결정 기록

초기 의사결정은 [docs/DECISIONS.md](docs/DECISIONS.md)에 기록합니다.

## 한계 및 주의사항

- 데모 v1.4의 3D 좌표는 정밀 복원 결과가 아닙니다.
- 거리 추정은 카메라 캘리브레이션 없이 bbox 위치와 크기를 이용한 휴리스틱입니다.
- YOLO 결과는 프레임별 bbox이며, 현재는 프레임 간 동일 객체 추적을 보장하지 않습니다.
- 전조등/고휘도 후보는 차량이라고 확정하지 않고 `is_candidate`와 `detection_reason`을 함께 기록합니다.
- 법적 사고 판단이나 운전자 과실 판단에는 사용할 수 없습니다.
