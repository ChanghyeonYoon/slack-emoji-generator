# Slack Emoji Bot

슬랙에서 다양한 애니메이션 효과가 적용된 커스텀 이모지를 생성하는 봇입니다.

## 주요 기능

### 텍스트 이모지

- **9가지 이모지 효과** 지원
  - `none`: 정적 이미지 (PNG)
  - `scroll`: 글자가 흘러가는 전광판 효과 (여러 파일 생성)
  - `party`: 무지개색으로 변하는 파티 효과
  - `rotate`: 동그랗게 돌아가는 효과
  - `shake`: 좌우로 흔들리는 효과
  - `wave`: 물결처럼 움직이는 효과
  - `typing`: 한 글자씩 나타나는 타이핑 효과
  - `grow`: 글씨가 점점 커지는 효과
  - `split`: 글자별 개별 이모지 생성

- **6가지 폰트** 지원
  - 나눔고딕, 나눔스퀘어라운드 EB
  - 나눔명조 EB, Noto Sans Mono
  - EBS 주시경체, 호국체

### 이미지 이모지

- **이미지 업로드로 이모지 생성**
  - PNG, JPG, GIF, WEBP 형식 지원
  - 자동으로 128x128 크기로 변환

- **3가지 리사이징 모드**
  - `Cover (크롭)`: 비율 유지하며 중앙에서 크롭
  - `Contain (여백)`: 비율 유지, 남는 공간은 배경색으로 채움
  - `Fill (늘리기)`: 비율 무시하고 이미지를 늘림

- **이미지 애니메이션 효과**
  - 회전, 흔들림, 파티(무지개색), 물결, 커지기 효과 적용 가능

### 공통 기능

- **슬래시 명령어**
  - `/이모지 텍스트`: 텍스트 이모지 생성
  - `/이미지이모지`: 이미지 업로드 모달 열기
- **이미지 업로드 자동 감지**: 채널에 이미지 업로드 시 이모지 생성 제안
- **인터랙티브 UI**: 효과, 폰트, 색상 실시간 선택
- **Socket Mode (WebSocket)**: 실시간 양방향 통신
- **Docker 지원**: docker-compose로 간편 배포
- **Datadog APM 연동**: dd-trace로 성능 모니터링

## 아키텍처

```
┌─────────────────────────────────────────────────────────────┐
│                    Docker Environment                        │
│  ┌─────────────────┐  ┌─────────┐  ┌──────────────────┐    │
│  │   Flask App     │  │  MySQL  │  │  Datadog Agent   │    │
│  │  + Socket Mode  │──│         │  │                  │    │
│  │  + dd-trace     │  │ Tokens  │  │  APM / Logs      │    │
│  └────────┬────────┘  └─────────┘  └────────┬─────────┘    │
│           │                                  │              │
└───────────┼──────────────────────────────────┼──────────────┘
            │ WebSocket                        │
            ▼                                  ▼
      ┌──────────┐                      ┌──────────────┐
      │  Slack   │                      │   Datadog    │
      │   API    │                      │    Cloud     │
      └──────────┘                      └──────────────┘
```

## 빠른 시작

### 1. 환경 설정

```bash
# 환경변수 파일 생성
cp env.example .env

# .env 파일 편집
vim .env
```

필요한 환경변수:
- `SLACK_BOT_TOKEN`: Slack Bot 토큰 (xoxb-...)
- `SLACK_SIGNING_SECRET`: Slack Signing Secret
- `SLACK_APP_TOKEN`: Slack App 토큰 (xapp-...) - Socket Mode용
- `SLACK_CLIENT_ID`, `SLACK_CLIENT_SECRET`: OAuth용
- `DD_API_KEY`: Datadog API 키 (선택사항)

### 2. 폰트 설치

`fonts/` 디렉토리에 한글 폰트 파일을 추가합니다:
- NanumGothic.ttf
- NanumSquare.ttf
- NanumSquareRoundEB.ttf
- NanumMyeongjoEB.ttf
- NotoSansMonoCJKkr-Bold.otf
- EBSJusigyeongB.ttf
- Hoguk.ttf

[네이버 나눔글꼴](https://hangeul.naver.com/font)에서 다운로드 가능합니다.

### 3. Docker로 실행

```bash
docker-compose up -d
```

### 4. Slack App 설정

1. [Slack API](https://api.slack.com/apps)에서 새 앱 생성

2. **Socket Mode 활성화** (Settings > Socket Mode)
   - Enable Socket Mode
   - App-Level Token 생성 (connections:write 스코프)

3. **OAuth & Permissions에서 Bot Token Scopes 추가:**
   - `commands`
   - `files:write`
   - `files:read`
   - `chat:write`

4. **Slash Commands 등록:**
   - Command: `/이모지` - 텍스트 이모지 생성
   - Command: `/이미지이모지` - 이미지 이모지 생성

5. **Event Subscriptions 활성화:**
   - `app_home_opened`
   - `message.channels` (이미지 업로드 감지용)

## 사용 방법

### 텍스트 이모지 생성

```
/이모지 안녕하세요
```

명령어 실행 후 인터랙티브 UI에서 옵션을 선택할 수 있습니다:
- 효과 선택 (scroll, party, shake 등)
- 폰트 선택
- 텍스트 색상
- 배경색 (투명 또는 색상 지정)

### 이미지 이모지 생성

**방법 1: 슬래시 명령어**
```
/이미지이모지
```
모달에서 이미지 파일을 업로드하고 옵션을 선택합니다.

**방법 2: 이미지 업로드**
1. 채널에 이미지를 업로드
2. 봇이 "이모지 만들기" 버튼을 제안
3. 버튼 클릭 후 옵션 선택

이미지 이모지 옵션:
- 리사이징 모드 (Cover/Contain/Fill)
- 배경색 (Contain 모드에서 여백 색상)
- 애니메이션 효과 (회전, 흔들림, 파티, 물결, 커지기)

### 효과별 결과

| 효과 | 설명 | 결과 |
|------|------|------|
| scroll | 텍스트가 흘러가는 효과 | 여러 개의 GIF 파일 |
| split | 글자별 분리 | 글자 수만큼 PNG 파일 |
| 그 외 | 애니메이션 효과 | 단일 GIF 파일 |
| none | 정적 이미지 | 단일 PNG 파일 |

### 이미지 리사이징 모드

| 모드 | 설명 |
|------|------|
| Cover | 비율 유지, 128x128에 맞게 중앙 크롭 |
| Contain | 비율 유지, 남는 공간은 배경색으로 채움 |
| Fill | 비율 무시, 128x128로 늘림 |

## 로컬 개발

```bash
# 가상환경 생성
python -m venv venv
source venv/bin/activate

# 의존성 설치
pip install -r requirements.txt

# 개발 서버 실행 (Socket Mode)
python app.py
```

## 프로젝트 구조

```
slack-emoji-bot/
├── app.py                    # Flask 앱 + Socket Mode + dd-trace
├── config.py                 # 환경변수 설정
├── generators/
│   ├── base.py               # 이미지 생성기
│   ├── text_renderer.py      # 텍스트 렌더링
│   ├── image_processor.py    # 이미지 리사이징/처리
│   └── effects/              # 애니메이션 효과
│       ├── base_effect.py    # 기본 효과 클래스
│       ├── scroll.py
│       ├── party.py
│       ├── rotate.py
│       ├── shake.py
│       ├── wave.py
│       ├── typing.py
│       ├── grow.py
│       └── none.py
├── slack/
│   ├── workflow_step.py      # Workflow Step 핸들러
│   ├── emoji_uploader.py     # 이모지 업로드
│   └── oauth.py              # OAuth 핸들러
├── database/
│   ├── models.py             # SQLAlchemy 모델
│   └── token_store.py        # 토큰 저장소
├── fonts/                    # 폰트 파일
├── docker-compose.yml        # Docker Compose 설정
├── Dockerfile
├── requirements.txt
└── README.md
```

## Datadog 모니터링 (선택사항)

- **APM 트레이싱**: 모든 요청 자동 추적
- **커스텀 스팬**: 이모지 생성 성능 측정
- **로그 연동**: trace_id 자동 주입

## 라이선스

MIT License
