# Problem_Change_Project

영어 지문 1개를 입력하면, 한국 고교 모의고사 스타일의 객관식 문항을 자동으로 생성하는 서비스입니다.  
현재 총 11개 유형을 지원하며, FastAPI 백엔드 + Svelte 프론트엔드로 구성되어 있습니다.

## 서비스 개요

이 프로젝트는 단순 번역기가 아니라, 지문을 분석해 "시험 문제 형태"로 바꾸는 문제 생성 엔진입니다.

- 입력: 영어 지문 1개
- 출력: 문제 지시문, 선지 5개, 정답 1개, 해설
- 특징: 정답 유일성 검증, 유형별 생성 전략, 원문 보존 기반 표식 처리(빈칸/함축)

비전공자 기준으로 보면, 이 서비스는 "영어 지문을 넣으면 바로 문제지를 만들어주는 생성기"라고 이해하면 됩니다.

## 서비스 구조 (시각화)

### 1) 전체 요청 흐름

```mermaid
flowchart LR
    U[사용자] --> W[웹 UI<br/>Svelte]
    U --> D[Swagger Docs<br/>/docs]

    W -->|POST /api/v1/*| API[FastAPI<br/>app/main.py]
    D --> API

    API --> R[_run_agent<br/>async]
    R --> A[유형별 Agent<br/>Title/Topic/Summary/...]

    A --> P[Prompt Loader<br/>app/prompts/*.md]
    A --> T[Toolkit<br/>text/validators/render]
    A --> S[Schemas<br/>요청/응답 검증]

    A -->|LLM 사용 시| LLM[Gemini Client<br/>app/llm/client.py]
    LLM --> A

    A --> V[유형별 검증<br/>정답 유일성/형식]
    V --> API
    API --> W
    W --> U
```

### 2) 백엔드 내부 구성

```mermaid
flowchart TB
    subgraph Entry
      M[app/main.py<br/>라우트 + 에이전트 연결]
    end

    subgraph Agents
      AG[app/agents/*_agent.py<br/>문항 유형별 생성 로직]
      BA[BaseAgent<br/>공통 분석/LLM 경로]
    end

    subgraph LLM
      LC[app/llm/client.py]
      LP[app/llm/provider.py]
      LJ[app/llm/json.py]
      LS[app/llm/schema.py]
    end

    subgraph Prompt
      PR[app/prompts/*.md]
      PL[app/prompts/loader.py]
    end

    subgraph Data
      SC[app/schemas/*.py]
      TK[app/toolkit/*<br/>text/validators/render/discourse]
    end

    M --> AG
    AG --> BA
    BA --> PL --> PR
    BA --> LC
    LC --> LJ
    AG --> SC
    AG --> TK
    LP --> LC
    LS --> LC
```

## 지원 문제 유형 (11개)

| 유형 | Endpoint | Agent | Prompt | Schema |
|---|---|---|---|---|
| 제목 | `POST /api/v1/title` | `TitleAgent` | `app/prompts/title.md` | `app/schemas/title.py` |
| 주제 | `POST /api/v1/topic` | `TopicAgent` | `app/prompts/topic.md` | `app/schemas/topic.py` |
| 요약 | `POST /api/v1/summary` | `SummaryAgent` | `app/prompts/summary.md` | `app/schemas/summary.py` |
| 함축의미 | `POST /api/v1/implicit` | `ImplicitAgent` | `app/prompts/implicit.md` | `app/schemas/implicit.py` |
| 문장삽입 | `POST /api/v1/insertion` | `InsertionAgent` | `app/prompts/insertion.md` | `app/schemas/insertion.py` |
| 글의 순서 | `POST /api/v1/order` | `OrderAgent` | `app/prompts/order.md` | `app/schemas/order.py` |
| 무관문장 | `POST /api/v1/irrelevant` | `IrrelevantAgent` | `app/prompts/irrelevant.md` | `app/schemas/irrelevant.py` |
| 빈칸 | `POST /api/v1/blank` | `BlankAgent` | `app/prompts/blank.md` | `app/schemas/blank.py` |
| 지칭 | `POST /api/v1/reference` | `ReferenceAgent` | `app/prompts/reference.md` | `app/schemas/reference.py` |
| 어휘 | `POST /api/v1/vocab` | `VocabAgent` | `app/prompts/vocab.md` | `app/schemas/vocab.py` |
| 어법 | `POST /api/v1/grammar` | `GrammarAgent` | `app/prompts/grammar.md` | `app/schemas/grammar.py` |

## 에이전트 구조 설명

각 문제 유형은 "전담 생성기(Agent)"가 따로 있습니다.  
예를 들어 요약 문제는 `SummaryAgent`가, 함축의미 문제는 `ImplicitAgent`가 담당합니다.

공통적으로 다음 흐름으로 동작합니다.

1. 지문 전처리 (길이, 형식 점검)
2. 지문 분석 (주제, 핵심 문장, 키워드 추출)
3. LLM 생성 시도 (프롬프트 + JSON 스키마)
4. 검증 (선지 5개, 정답 일치, 유형별 형식 검사)
5. 실패 시 fallback 로직으로 안전 생성

## 비동기 처리 구조

현재 API 라우트는 전부 `async`로 동작합니다.

- 라우트 함수: `async def`
- 공통 실행기: `app/main.py`의 `_run_agent(...)`
- Agent 실행: `BaseAgent.agenerate(...)`에서 `asyncio.to_thread(...)` 사용

즉, 내부 생성 로직이 동기 함수여도 이벤트 루프를 막지 않도록, 요청 처리 경계는 비동기 방식으로 구성되어 있습니다.

## 원문 보존 원칙

이 프로젝트는 "문제 생성 중 원문을 임의로 바꾸지 않는 것"을 중요하게 다룹니다.

- `blank`: 원문에서 정답 스팬만 `_____`로 치환
- `implicit`: 원문에서 타깃 스팬만 `[[1]]...[[/1]]` 표식 처리

이 방식 덕분에 원문 무결성을 검증할 수 있고, UI에서도 정확한 위치 표시가 가능합니다.

## 프로젝트 구조

```text
app/
  agents/        # 유형별 문제 생성기
  schemas/       # 요청/응답 + 저장 스키마
  prompts/       # LLM 지시문 템플릿
  toolkit/       # 검증, 텍스트 처리, 렌더링 유틸
  llm/           # LLM 클라이언트, JSON 파싱/스키마 처리
  storage/       # 파일/DB 저장 서비스
  db/            # SQLAlchemy DB 모델
  problems/      # 저장된 문제 JSON + JSON Schema
  main.py        # FastAPI 라우트 진입점
frontend/
  src/           # Svelte UI
tests/           # 스모크/유효성/무결성 테스트
Dockerfile
docker-compose.yml
Makefile
```

## 문제 저장 구조 (JSON + DB)

문항이 생성되면(기본값 `ENABLE_PROBLEM_PERSISTENCE=true`) 자동으로 JSON 파일이 저장됩니다.

- 파일 경로 규칙: `app/problems/{problem_type}/{passage_id}/attempt_{n}.json`
- `passage_id`: 지문 정규화(공백/대소문자 정리) 후 SHA-256 해시 앞 16자리
- `attempt_no`: 같은 `problem_type + passage_id` 조합에서 1부터 순번 증가
- 저장 스키마 파일: `app/problems/problem_record.schema.json`

저장된 JSON에는 `request`, `result`, `storage_meta`가 함께 들어가며, API 응답의 `meta.storage`에도 아래 정보가 포함됩니다.

- `problem_uid`
- `passage_id`
- `attempt_no`
- `file_path`
- `db_saved`
- `db_row_id`

`ENABLE_DB_PERSISTENCE=true`이고 `DATABASE_URL`이 설정되면 SQLAlchemy로 `problem_records` 테이블에도 함께 저장됩니다.

## 환경 변수(.env) 설명

`app/core/config.py` 기준으로 아래 값을 사용합니다.

| 변수명 | 기본값 | 설명 |
|---|---|---|
| `APP_ENV` | `dev` | 실행 환경 (`dev`, `test` 등) |
| `LOG_LEVEL` | `INFO` | 로그 레벨 |
| `GOOGLE_API_KEY` | `""` | Gemini API 키 (권장) |
| `GEMINI_API_KEY` | `""` | 대체 API 키 |
| `GEMINI_MODEL` | `gemini-3-flash-preview` | 사용 모델 |
| `DEFAULT_TEMPERATURE` | `0.6` | 기본 생성 온도 |
| `DEFAULT_MAX_OUTPUT_TOKENS` | `20000` | 기본 최대 토큰 |
| `USE_LLM_GENERATION` | `true` | LLM 생성 사용 여부 |
| `ENABLE_SELF_CHECK` | `false` | 자체 점검 사용 여부 |
| `SELF_CHECK_MAX_RETRY` | `1` | 자체 점검 재시도 횟수 |
| `ENABLE_PROBLEM_PERSISTENCE` | `true` | 생성 결과를 `app/problems`에 JSON 파일로 저장할지 여부 |
| `ENABLE_DB_PERSISTENCE` | `false` | SQLAlchemy를 통해 DB에도 함께 저장할지 여부 |
| `DATABASE_URL` | `""` | DB 연결 문자열 (예: `postgresql+psycopg://postgres:postgres@db:5432/problem_db`) |
| `DATABASE_ECHO` | `false` | SQLAlchemy SQL 로그 출력 여부 |

`GOOGLE_API_KEY` 또는 `GEMINI_API_KEY` 중 하나만 있어도 됩니다.

## 백엔드 실행

```bash
uv sync --group dev
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Swagger 문서:

- `http://localhost:8000/docs`

상태 확인:

- `GET /health`

## Makefile 명령

```bash
make start      # 백엔드(uvicorn) 포그라운드 실행
make stop       # 백엔드(uvicorn) 종료
make frontend   # 프론트엔드(vite) 실행
make up         # docker compose up --build -d
make down       # docker compose down
```

`make start`는 로그를 현재 터미널에 바로 출력합니다. 종료는 `Ctrl+C` 또는 다른 터미널에서 `make stop`으로 가능합니다.

## Docker Compose 실행 (API 8000 + PostgreSQL)

```bash
make up
```

- API: `http://localhost:8000`
- Swagger: `http://localhost:8000/docs`
- PostgreSQL: `localhost:5432`

문제 JSON은 로컬 `app/problems` 디렉터리로 볼륨 마운트되어 컨테이너 재시작 후에도 유지됩니다.

종료:

```bash
make down
```

## 프론트엔드 실행

```bash
make frontend
```

기본적으로 Vite proxy는 `http://localhost:8000` 백엔드로 연결됩니다.

WSL + Windows 혼합 실행 시, `frontend/vite.config.js`가 Windows host IP를 자동 감지해 proxy target으로 사용합니다.

proxy를 강제로 지정하려면:

```bash
cd frontend
VITE_PROXY_TARGET=http://127.0.0.1:8000 npm run dev
```

프론트 빌드:

```bash
cd frontend
npm run build
```

## 테스트

전체 테스트:

```bash
uv run pytest
```

특정 테스트만:

```bash
uv run pytest tests/test_type_validators.py -q
```

## API 빠른 예시

요약 문제 생성 예시:

```bash
curl -X POST "http://localhost:8000/api/v1/summary" \
  -H "Content-Type: application/json" \
  -d '{
    "passage": "People often rely on routines because habits reduce cognitive load and free attention for difficult tasks. However, habits can hide weak assumptions when people stop reflecting on why they act in a certain way. Therefore, good decision making requires stable routines and periodic review. When individuals compare evidence and context, they can keep useful patterns while revising outdated ones.",
    "difficulty": "mid",
    "seed": 123,
    "explain": true,
    "return_korean_stem": true,
    "debug": false
  }'
```

## <가이드>

아래 순서대로 진행하면 개발/도커 실행을 바로 할 수 있습니다.

### 1) 준비물

- Python 3.10+
- Node.js 18+
- `uv`
- Docker Desktop (Docker 사용 시)

WSL에서 `make`가 없다면:

```bash
sudo apt update
sudo apt install -y make
```

### 2) 프로젝트 이동

```bash
cd /mnt/d/English_Problem_Change/Problem_Change_Project
```

### 3) `.env` 설정

```env
APP_ENV=dev
LOG_LEVEL=INFO

GOOGLE_API_KEY=여기에_키_입력
GEMINI_MODEL=gemini-3-flash-preview

USE_LLM_GENERATION=true
ENABLE_SELF_CHECK=false
SELF_CHECK_MAX_RETRY=1

ENABLE_PROBLEM_PERSISTENCE=true
ENABLE_DB_PERSISTENCE=false
# DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/problem_db
DATABASE_ECHO=false
```

### 4) 의존성 설치

```bash
uv sync --group dev
cd frontend && npm install
```

### 5) 로컬 실행 (권장)

백엔드:

```bash
make start
```

프론트엔드(새 터미널):

```bash
make frontend
```

### 6) Docker 실행

```bash
make up
```

종료:

```bash
make down
```

### 7) 저장 결과 확인

문항 생성 후 아래 경로에 JSON이 생깁니다.

```text
app/problems/{problem_type}/{passage_id}/attempt_{n}.json
```

### 8) 문제 해결 팁 (WSL + Docker)

`permission denied ... /var/run/docker.sock`가 나오면:

```bash
sudo groupadd docker 2>/dev/null || true
sudo usermod -aG docker $USER
newgrp docker
```
