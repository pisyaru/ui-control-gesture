# ui-control-gesture

English version: [README.md](README.md)

MediaPipe 기반 손/머리 추적과 모듈형 STT/TTS 백엔드를 이용해 macOS UI를 제어하는 카메라 기반 앱입니다.

## 주요 기능

- 오른손으로 커서 이동, 좌클릭, 우클릭, 드래그, 주먹 STT 시작
- 오른손 UI 제어와 동시에 가능한 왼손 중지 스와이프 스크롤
- 머리 회전 방향을 이용한 자막 위치 결정
- 항상 듣기 기반 wake-word STT와 교체 가능한 ASR 백엔드
- 향후 기능 연결을 위한 교체 가능한 TTS 백엔드
- hand/head/STT/TTS 토글과 캘리브레이션을 제공하는 메뉴바 UI
- 사용할 macOS 카메라를 고를 수 있는 메뉴바 카메라 선택 UI

## 기술 스택

- Python 3.12
- MediaPipe Tasks Vision
- PyObjC / AppKit / Quartz
- OpenCV
- MLX-Audio

## 실행 방법

저장소 루트:

```bash
cd /Users/ijin-yeong/Desktop/1_Programming/ui-control-gesture
```

1. 로컬 가상환경을 만들고 의존성을 설치합니다.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .
```

2. 필요한 MediaPipe task 모델 파일을 `models/` 아래에 내려받습니다.

```bash
mkdir -p models
curl -L https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task -o models/hand_landmarker.task
curl -L https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task -o models/face_landmarker.task
```

3. 저장소 루트에서 앱을 실행합니다.

```bash
source .venv/bin/activate
PYTHONPATH=src python3 -m ui_control_gesture
```

## 참고 사항

- 이 앱은 Apple Silicon macOS를 기준으로 설계되었습니다.
- 카메라, 마이크, 접근성, 입력 모니터링 권한이 필요합니다.
- 첫 실행 시 추적 시작 전에 카메라와 마이크 권한을 먼저 요청합니다.
- STT/TTS 백엔드는 로컬 실행을 기본으로 하며 어댑터 구조로 교체할 수 있습니다.
- `.venv/`와 `models/`는 이 맥북에서만 쓰는 로컬 자산이라 git에 올리지 않습니다.
- 앞으로 큰 바이너리 파일을 공유해야 하면 일반 git 커밋 대신 GitHub Release asset으로 관리합니다.
