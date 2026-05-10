# AGENTS.md

이 문서는 기존 `codex.md`와 `codex_update.md`의 구현 지시를 현재 코드 상태에 맞게 통합한 개발자/에이전트용 가이드입니다. 앞으로 Codex 또는 다른 코드 에이전트가 이 저장소를 수정할 때는 이 문서를 우선 기준으로 삼습니다.

## 1. 프로젝트 목적

`Problem_Change_Project`는 영어 지문 1개를 입력받아 한국 고교 모의고사 스타일의 객관식 변형문항을 생성하는 서비스입니다.

핵심 목표:

- 영어 지문을 11개 유형의 시험 문항으로 변환
- 생성 결과를 JSON 파일 및 선택적으로 DB에 저장
- 저장된 개인 문제를 다시 열람
- 저장 문제를 조합해 모의고사 문제지와 해설지 구성
- Gemini, OpenAI API, 로컬 Codex CLI 기반 생성 경로 지원

## 2. 현재 지원 유형

현재 실제 구현 기준은 11개 유형입니다. 과거 `codex.md`의 `LongAgent`/`/api/v1/long` 설계는 현재 구현 대상이 아닙니다.

| 유형 | Endpoint | Agent | Prompt | Schema |
|---|---|---|---|---|
| 제목 | `POST /api/v1/title` | `TitleAgent` | `app/prompts/title.md` | `app/schemas/title.py` |
| 주제 | `POST /api/v1/topic` | `TopicAgent` | `app/prompts/topic.md` | `app/schemas/topic.py` |
| 빈칸 | `POST /api/v1/blank` | `BlankAgent` | `app/prompts/blank.md` | `app/schemas/blank.py` |
| 요약 | `POST /api/v1/summary` | `SummaryAgent` | `app/prompts/summary.md` | `app/schemas/summary.py` |
| 함축의미 | `POST /api/v1/implicit` | `ImplicitAgent` | `app/prompts/implicit.md` | `app/schemas/implicit.py` |
| 문장삽입 | `POST /api/v1/insertion` | `InsertionAgent` | `app/prompts/insertion.md` | `app/schemas/insertion.py` |
| 글의 순서 | `POST /api/v1/order` | `OrderAgent` | `app/prompts/order.md` | `app/schemas/order.py` |
| 무관문장 | `POST /api/v1/irrelevant` | `IrrelevantAgent` | `app/prompts/irrelevant.md` | `app/schemas/irrelevant.py` |
| 지칭 | `POST /api/v1/reference` | `ReferenceAgent` | `app/prompts/reference.md` | `app/schemas/reference.py` |
| 어휘 | `POST /api/v1/vocab` | `VocabAgent` | `app/prompts/vocab.md` | `app/schemas/vocab.py` |
| 어법 | `POST /api/v1/grammar` | `GrammarAgent` | `app/prompts/grammar.md` | `app/schemas/grammar.py` |

## 3. 전체 구조

```text
app/
  agents/        # 유형별 문항 생성 Agent
  core/          # 설정, 로깅, 에러 정의
  db/            # SQLAlchemy DB 모델
  llm/           # Gemini/OpenAI/Codex CLI provider
  prompts/       # 유형별 LLM 프롬프트
  schemas/       # 요청/응답/저장 Pydantic 스키마
  storage/       # JSON 파일 저장 + DB 저장 래퍼
  toolkit/       # 텍스트 처리, 렌더링, 검증 유틸
  main.py        # FastAPI 라우트 진입점

frontend/
  src/
    App.svelte
    components/
      ProblemCreator.svelte   # 문제 만들기
      ProblemLibrary.svelte   # 개인 문제 저장소
      MockExamBuilder.svelte  # 모의고사 문제지/해설지 구성
      ProblemView.svelte      # 공통 문제 렌더링
    lib/
      problemUtils.js         # 공통 표시/파싱 유틸
    app.css

tests/           # API, 저장소, 스키마, 검증 테스트
```

## 4. 백엔드 실행 흐름

```text
사용자 요청
  -> FastAPI route (/api/v1/{type})
  -> 유형별 Agent.generate/agenerate
  -> BaseAgent 공통 분석 + LLM provider 호출
  -> 유형별 validator
  -> ProblemResponse
  -> ProblemPersistenceService
  -> app/problems JSON 저장
  -> 선택적으로 DB 저장
```

주요 파일:

- `app/main.py`: 라우트, Agent 인스턴스, 저장소 연결
- `app/agents/base.py`: 공통 생성 흐름, LLM fallback, 비동기 실행
- `app/llm/provider.py`: `LLM_PROVIDER`에 따라 provider 선택
- `app/llm/client.py`: Gemini/OpenAI/Codex CLI 클라이언트 구현
- `app/storage/problem_store.py`: 로컬 JSON 저장소
- `app/storage/persistence.py`: 로컬/DB 저장 통합

## 5. 프론트엔드 기능

현재 프론트는 기능별 컴포넌트로 분리되어 있습니다.

### 문제 만들기

파일: `frontend/src/components/ProblemCreator.svelte`

- 영어 지문 입력
- 11개 유형 중 선택
- 난이도 선택
- 해설 포함 여부 선택
- 생성 결과 즉시 확인
- 생성 성공 시 저장소 자동 갱신

### 내 문제 저장소

파일: `frontend/src/components/ProblemLibrary.svelte`

- `GET /api/v1/problems`로 저장 문제 조회
- 유형 필터
- 지문/질문/해설 검색
- 카드 클릭 시 모달로 큰 화면 보기

### 모의고사 시험지

파일: `frontend/src/components/MockExamBuilder.svelte`

- 개인 저장소 문제만 사용
- 문항 수 입력
- 포함할 문제 유형 선택
- 한국 모의고사 스타일 2단 문제지 구성
- 왼쪽 교체 후보 목록 제공
- 후보 문제 클릭 선택 후 특정 문항 교체
- 후보 문제 드래그앤드롭으로 특정 문항 교체
- 정답표 표시 옵션
- 해설지 표시 옵션
- 브라우저 인쇄/PDF 저장 지원

### 공통 문제 렌더링

파일: `frontend/src/components/ProblemView.svelte`

- 생성 결과와 저장 문제 상세 모달에서 공통 사용
- 삽입/요약/함축/어휘/어법/지칭 등 특수 표시 처리

## 6. 저장 구조

문항 생성 후 `ENABLE_PROBLEM_PERSISTENCE=true`이면 JSON 파일이 자동 저장됩니다.

```text
app/problems/{problem_type}/{passage_id}/attempt_{n}.json
```

저장 레코드 주요 필드:

- `problem_uid`: 저장 문제 고유 ID
- `problem_type`: 문제 유형
- `passage_id`: 지문 해시 ID
- `attempt_no`: 같은 지문/유형 조합의 생성 순번
- `request`: 생성 요청
- `result`: 생성 결과
- `storage_meta`: 파일/DB 저장 메타데이터

저장 API:

- `GET /api/v1/problems`
- `GET /api/v1/problems/{problem_uid}`

## 7. LLM Provider

환경 변수 `LLM_PROVIDER`로 provider를 선택합니다.

| Provider | 값 | 필요 설정 | 비고 |
|---|---|---|---|
| Gemini | `gemini` | `GOOGLE_API_KEY` 또는 `GEMINI_API_KEY` | 기본값 |
| OpenAI API | `openai` | `OPENAI_API_KEY` | 운영에는 이 경로 권장 |
| Codex CLI | `codex_cli` | 로컬 Codex CLI 로그인 | 실험용, 요청마다 CLI subprocess 실행 |

Codex CLI 경로는 현재 로그인된 로컬 Codex CLI 세션을 사용합니다. 토큰 파일을 직접 읽어 API 키처럼 쓰는 방식이 아닙니다.

## 8. 환경 변수

주요 설정은 `app/core/config.py` 기준입니다.

```env
APP_ENV=dev
LOG_LEVEL=INFO

LLM_PROVIDER=gemini

GOOGLE_API_KEY=
GEMINI_API_KEY=
GEMINI_MODEL=gemini-3-flash-preview

OPENAI_API_KEY=
OPENAI_MODEL=gpt-5-mini
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_REASONING_EFFORT=
OPENAI_TIMEOUT_SECONDS=120

CODEX_CLI_COMMAND=codex
CODEX_CLI_MODEL=
CODEX_CLI_TIMEOUT_SECONDS=300

DEFAULT_TEMPERATURE=0.6
DEFAULT_MAX_OUTPUT_TOKENS=20000

USE_LLM_GENERATION=true
ENABLE_SELF_CHECK=false
SELF_CHECK_MAX_RETRY=1

ENABLE_PROBLEM_PERSISTENCE=true
ENABLE_DB_PERSISTENCE=false
DATABASE_URL=
DATABASE_ECHO=false
```

## 9. 실행 명령

의존성 설치:

```bash
uv sync --group dev
cd frontend && npm install
```

백엔드:

```bash
make start
```

프론트엔드:

```bash
make frontend
```

Docker:

```bash
make up
make down
```

직접 실행:

```bash
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
cd frontend && npm run dev
```

## 10. 테스트와 검증

전체 테스트:

```bash
uv run pytest
```

프론트 빌드:

```bash
cd frontend
npm run build
```

문법/공백 점검:

```bash
git diff --check
```

## 11. 품질 원칙

### 원문 보존

문항 생성 중 지문을 임의로 재작성하지 않는 것이 중요합니다.

- `blank`: 원문 특정 span만 `_____`로 치환
- `implicit`, `vocab`, `grammar`: 원문 target만 표식 처리
- 프론트는 표식을 파싱해 밑줄/번호 형태로 렌더링

### 정답 유일성

모든 문제는 다음 조건을 만족해야 합니다.

- 선택지 5개
- 정답 1개
- 정답 label이 choices 안에 존재
- 오답은 너무 노골적이지 않고 지문 키워드를 공유하되 논리적으로 틀릴 것

### 오답 패턴

권장 오답 패턴:

- Too Broad / Too Narrow
- Polarity Flip
- Same Domain, Wrong Mechanism
- Near-Synonym Trap
- Scope Shift
- Collocation Trap
- Category Swap

## 12. 작업 시 주의사항

- 기존 사용자 변경을 되돌리지 마세요.
- 문서와 구현이 충돌하면 현재 코드 구현을 우선으로 문서를 갱신하세요.
- 새 유형을 추가할 때는 Agent, Schema, Prompt, Route, Smoke Test를 함께 추가하세요.
- 저장 구조를 바꿀 때는 `SavedProblemRecord`와 기존 `app/problems` 호환성을 확인하세요.
- 프론트 기능은 `App.svelte`에 다시 몰아넣지 말고 `components/` 아래 기능 단위로 확장하세요.
- 공통 표시/파싱 로직은 `frontend/src/lib/problemUtils.js` 또는 `ProblemView.svelte`에 모으세요.

## 13. 레거시 문서와의 관계

- `codex.md`: 초기 FastAPI/Agent 설계 문서
- `codex_update.md`: topic/implicit 추가와 원문 보존 강화 지시서
- `AGENTS.md`: 현재 코드 상태 기준 통합 문서

앞으로는 `AGENTS.md`를 우선 업데이트하고, 필요하면 `README.md`에는 사용자 관점의 실행/사용법만 반영합니다.
