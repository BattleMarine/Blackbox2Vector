# DEBUG_NOTES.md

## 기록 규칙

재발 가능성이 있는 오류만 기록한다.

## 문제 기록 템플릿

### 문제

### 증상

### 원인

### 해결

### 관련 파일

### 문제

Streamlit 앱에서 `ObjectDetector.__init__()`이 `backend` 인자를 받지 못한다는 오류가 발생했다.

### 증상

더미 detector와 YOLO detector 모두 분석 시작 시 `unexpected keyword argument 'backend'` 오류가 표시된다.

### 원인

Streamlit hot reload 중 `src.detector` 모듈 캐시에 v1.1의 이전 `ObjectDetector` 클래스가 남아 있을 수 있다.

### 해결

`app.py`에서 detector를 생성하기 직전에 `src.detector` 모듈을 `importlib.reload()`로 다시 읽도록 했다.

### 관련 파일

- `app.py`
- `src/detector.py`

### 문제

YOLO 백엔드 선택 시 `ultralytics`가 필요하다는 오류가 계속 발생했다.

### 증상

한 Python 환경에서는 `ultralytics` import가 가능하지만, Streamlit 앱에서는 설치되지 않은 것으로 표시된다.

### 원인

패키지를 설치한 Python과 Streamlit 앱을 실행한 Python이 서로 다를 수 있다.

### 해결

앱 사이드바에 실제 실행 중인 `sys.executable`과 `ultralytics` 설치 여부를 표시하도록 했다. 오류 메시지도 현재 Python 경로 기준 설치 명령을 안내하도록 변경했다.

### 관련 파일

- `app.py`
- `src/detector.py`
