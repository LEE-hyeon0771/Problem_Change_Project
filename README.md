# 영어 변형문제 제작소

영어 지문 1개를 입력하면 한국 고교 모의고사 스타일의 객관식 변형문항을 생성하고, 생성한 문제를 개인 저장소에 보관하며, 저장 문제를 조합해 모의고사 문제지와 해설지를 만들 수 있는 서비스입니다.

FastAPI 백엔드와 Svelte 프론트엔드로 구성되어 있습니다.

## 주요 기능

- 영어 지문 기반 변형문항 생성
- 11개 문제 유형 지원
- 생성 결과 자동 저장
- 개인 문제 저장소 조회/검색/상세 보기
- 저장 문제 기반 모의고사 시험지 구성
- 문제 교체 후보 목록 제공
- 클릭 선택 또는 드래그앤드롭으로 문항 교체
- 정답표 및 해설지 생성
- 브라우저 인쇄/PDF 저장
- Gemini, OpenAI API, Codex CLI provider 지원

## 화면 구성

프론트엔드는 3개 탭으로 구성됩니다.

| 탭 | 설명 |
|---|---|
| 문제 만들기 | 지문을 입력하고 유형/난이도를 선택해 변형문항 생성 |
| 내 문제 저장소 | 생성했던 문제를 개인 DB처럼 보관하고 다시 보기 |
| 모의고사 시험지 | 저장된 문제를 조합해 문제지와 해설지 구성 |

## 지원 문제 유형

| 유형 | API |
|---|---|
| 제목 | `POST /api/v1/title` |
| 주제 | `POST /api/v1/topic` |
| 빈칸 | `POST /api/v1/blank` |
| 요약 | `POST /api/v1/summary` |
| 함축의미 | `POST /api/v1/implicit` |
| 문장삽입 | `POST /api/v1/insertion` |
| 글의 순서 | `POST /api/v1/order` |
| 무관문장 | `POST /api/v1/irrelevant` |
| 지칭 | `POST /api/v1/reference` |
| 어휘 | `POST /api/v1/vocab` |
| 어법 | `POST /api/v1/grammar` |

저장 문제 API:

| 기능 | API |
|---|---|
| 저장 문제 목록 | `GET /api/v1/problems` |
| 저장 문제 상세 | `GET /api/v1/problems/{problem_uid}` |

## 빠른 시작

### 1. 프로젝트 이동

```bash
cd /mnt/d/English_Problem_Change/Problem_Change_Project
```

### 2. 의존성 설치

```bash
uv sync --group dev
cd frontend && npm install
```

### 3. 환경 변수 설정

프로젝트 루트에 `.env`를 만듭니다.

Gemini 사용 예시:

```env
APP_ENV=dev
LOG_LEVEL=INFO

LLM_PROVIDER=gemini
GOOGLE_API_KEY=여기에_Gemini_API_키
GEMINI_MODEL=gemini-3-flash-preview

USE_LLM_GENERATION=true
ENABLE_PROBLEM_PERSISTENCE=true
ENABLE_DB_PERSISTENCE=false
```

OpenAI API 사용 예시:

```env
APP_ENV=dev
LOG_LEVEL=INFO

LLM_PROVIDER=openai
OPENAI_API_KEY=여기에_OpenAI_API_키
OPENAI_MODEL=gpt-5-mini

USE_LLM_GENERATION=true
ENABLE_PROBLEM_PERSISTENCE=true
ENABLE_DB_PERSISTENCE=false
```

Codex CLI 사용 예시:

```env
APP_ENV=dev
LOG_LEVEL=INFO

LLM_PROVIDER=codex_cli
CODEX_CLI_COMMAND=codex
CODEX_CLI_MODEL=

USE_LLM_GENERATION=true
ENABLE_PROBLEM_PERSISTENCE=true
ENABLE_DB_PERSISTENCE=false
```

Codex CLI provider는 로컬에 로그인된 Codex CLI 세션을 subprocess로 호출합니다. 토큰 파일을 직접 꺼내 API 키처럼 사용하는 방식이 아니며, 운영용보다는 로컬 실험용에 가깝습니다.

### 4. 백엔드 실행

```bash
make start
```

직접 실행하려면:

```bash
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 5. 프론트엔드 실행

새 터미널에서:

```bash
make frontend
```

직접 실행하려면:

```bash
cd frontend
npm run dev
```

접속:

- 프론트엔드: `http://localhost:5173`
- API 문서: `http://localhost:8000/docs`
- 서버 상태: `http://localhost:8000/health`

## Docker 실행

```bash
make up
```

접속:

- API: `http://localhost:8000`
- Swagger: `http://localhost:8000/docs`
- PostgreSQL: `localhost:5432`

종료:

```bash
make down
```

## 사용 흐름

### 문제 만들기

1. `문제 만들기` 탭으로 이동합니다.
2. 문제 유형을 선택합니다.
3. 난이도를 선택합니다.
4. 영어 지문을 입력합니다.
5. `문항 생성`을 누릅니다.
6. 생성 결과는 자동으로 저장소에 쌓입니다.

### 내 문제 저장소

1. `내 문제 저장소` 탭으로 이동합니다.
2. 유형 필터 또는 검색어로 문제를 찾습니다.
3. 문제 카드를 클릭하면 모달로 크게 볼 수 있습니다.

### 모의고사 시험지

1. `모의고사 시험지` 탭으로 이동합니다.
2. 시험지 제목과 문항 수를 입력합니다.
3. 포함할 문제 유형을 선택합니다.
4. `시험지 만들기`를 누릅니다.
5. 왼쪽 `교체 후보 문제`에서 후보를 클릭하거나 드래그해 원하는 문항에 넣습니다.
6. 필요하면 `정답표 표시`, `해설지 표시`를 켭니다.
7. `인쇄 / PDF 저장`으로 출력합니다.

## 저장 구조

생성한 문제는 기본적으로 로컬 JSON 파일로 저장됩니다.

```text
app/problems/{problem_type}/{passage_id}/attempt_{n}.json
```

예시:

```text
app/problems/blank/d3fa7c95485109a0/attempt_001.json
```

저장 레코드에는 다음 정보가 포함됩니다.

- 생성 요청
- 생성 결과
- 문제 유형
- 지문 ID
- 시도 번호
- 파일 경로
- DB 저장 여부

DB 저장을 켜려면:

```env
ENABLE_DB_PERSISTENCE=true
DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/problem_db
```

## API 예시

요약 문제 생성:

```bash
curl -X POST "http://localhost:8000/api/v1/summary" \
  -H "Content-Type: application/json" \
  -d '{
    "passage": "People often rely on routines because habits reduce cognitive load and free attention for difficult tasks. However, habits can hide weak assumptions when people stop reflecting on why they act in a certain way. Therefore, good decision making requires stable routines and periodic review. When individuals compare evidence and context, they can keep useful patterns while revising outdated ones.",
    "difficulty": "mid",
    "choices": 5,
    "seed": 123,
    "style": "edu_office",
    "explain": true,
    "return_korean_stem": true,
    "debug": false
  }'
```

저장 문제 목록:

```bash
curl "http://localhost:8000/api/v1/problems?limit=50"
```

특정 유형만 조회:

```bash
curl "http://localhost:8000/api/v1/problems?problem_type=blank&limit=50"
```

## 프로젝트 구조

```text
app/
  agents/        # 유형별 문제 생성기
  core/          # 설정, 로깅, 에러
  db/            # SQLAlchemy 모델
  llm/           # Gemini/OpenAI/Codex CLI provider
  prompts/       # LLM 프롬프트
  schemas/       # 요청/응답/저장 스키마
  storage/       # 파일/DB 저장소
  toolkit/       # 텍스트 처리, 검증, 렌더링
  main.py        # FastAPI 앱

frontend/
  src/
    App.svelte
    components/
      ProblemCreator.svelte
      ProblemLibrary.svelte
      MockExamBuilder.svelte
      ProblemView.svelte
    lib/
      problemUtils.js
    app.css

tests/
Dockerfile
docker-compose.yml
Makefile
```

## 환경 변수 전체표

| 변수 | 기본값 | 설명 |
|---|---:|---|
| `APP_ENV` | `dev` | 실행 환경 |
| `LOG_LEVEL` | `INFO` | 로그 레벨 |
| `LLM_PROVIDER` | `gemini` | `gemini`, `openai`, `codex_cli` |
| `GOOGLE_API_KEY` |  | Gemini API 키 |
| `GEMINI_API_KEY` |  | Gemini 대체 API 키 |
| `GEMINI_MODEL` | `gemini-3-flash-preview` | Gemini 모델 |
| `OPENAI_API_KEY` |  | OpenAI API 키 |
| `OPENAI_MODEL` | `gpt-5-mini` | OpenAI 모델 |
| `OPENAI_BASE_URL` | `https://api.openai.com/v1` | OpenAI 호환 base URL |
| `OPENAI_REASONING_EFFORT` |  | reasoning effort 옵션 |
| `OPENAI_TIMEOUT_SECONDS` | `120` | OpenAI 요청 타임아웃 |
| `CODEX_CLI_COMMAND` | `codex` | Codex CLI 실행 명령 |
| `CODEX_CLI_MODEL` |  | Codex CLI 모델, 비우면 CLI 기본값 |
| `CODEX_CLI_TIMEOUT_SECONDS` | `300` | Codex CLI 타임아웃 |
| `DEFAULT_TEMPERATURE` | `0.6` | 기본 생성 온도 |
| `DEFAULT_MAX_OUTPUT_TOKENS` | `20000` | 기본 최대 출력 토큰 |
| `USE_LLM_GENERATION` | `true` | LLM 사용 여부 |
| `ENABLE_SELF_CHECK` | `false` | self-check 사용 여부 |
| `SELF_CHECK_MAX_RETRY` | `1` | self-check 재시도 횟수 |
| `ENABLE_PROBLEM_PERSISTENCE` | `true` | JSON 저장 여부 |
| `ENABLE_DB_PERSISTENCE` | `false` | DB 저장 여부 |
| `DATABASE_URL` |  | DB 연결 문자열 |
| `DATABASE_ECHO` | `false` | SQL 로그 출력 여부 |

## 테스트

전체 테스트:

```bash
uv run pytest
```

프론트 빌드:

```bash
cd frontend
npm run build
```

공백/문법 체크:

```bash
git diff --check
```

## 개발 참고

- 에이전트용 상세 개발 문서는 `AGENTS.md`를 확인하세요.
- 과거 설계 문서인 `codex.md`, `codex_update.md`는 `AGENTS.md`로 통합되었습니다.
- 프론트 기능 추가 시 `App.svelte`에 몰아넣지 말고 `frontend/src/components/` 아래 기능 단위로 분리하세요.
- 공통 문항 렌더링은 `ProblemView.svelte`, 공통 파싱/표시 유틸은 `problemUtils.js`에 둡니다.

## 문제 해결

WSL에서 Docker 권한 오류가 날 때:

```bash
sudo groupadd docker 2>/dev/null || true
sudo usermod -aG docker $USER
newgrp docker
```

프론트에서 백엔드 연결이 안 될 때:

```bash
cd frontend
VITE_PROXY_TARGET=http://127.0.0.1:8000 npm run dev
```

Codex CLI provider가 느릴 때:

- 정상입니다. 웹 요청마다 `codex` CLI subprocess를 실행합니다.
- 실제 서비스 운영은 `LLM_PROVIDER=openai` 또는 `LLM_PROVIDER=gemini`를 권장합니다.
