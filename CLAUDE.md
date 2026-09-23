# CLAUDE.md

이 저장소를 수정하는 개발자와 코드 에이전트의 **최상위 기준 문서**입니다.
전체 그림과 공통 규칙만 여기에 두고, 상세는 아래 두 문서로 나눠 두었습니다.

| 문서 | 다루는 것 |
|---|---|
| **`docs/CLAUDE_backend.md`** | FastAPI 레이어, 에이전트, 프롬프트 4겹 구조, 난이도 5지표, 동의어 교체, 단어장 커버리지, LLM provider, 저장 구조, 사용량 로그 |
| **`docs/CLAUDE_frontend.md`** | Svelte 화면 전환, API 계층, SSE 처리, 표식 파싱, 스타일 순서 규칙 |
| `docs/CLAUDE-refactoring.md` | 구조 개선 작업 시 실행 순서와 금지 사항 |
| `docs/spec-initial.md` / `docs/spec-update.md` | 보관용 초기 설계 문서 (현행 아님) |

문서와 구현이 충돌하면 **현재 코드가 기준**입니다. 문서를 고치세요.

---

## 1. 프로젝트 목적

영어 지문 1개를 입력받아 한국 고교 모의고사 스타일의 객관식 변형문항을 생성하는 서비스입니다.

- 영어 지문을 11개 유형의 시험 문항으로 변환
- 지문의 핵심단어를 빠짐없이 뽑아 뜻·품사·동의어·반의어로 정리
- 사용자가 "사용"을 누른 자료만 개인DB에 보관
- 보관한 자료로 모의고사 문제지·해설지와 단어 암기지를 구성
- Gemini / OpenAI API / 로컬 Codex CLI 생성 경로 지원

---

## 2. 전체 구조

```text
사용자
  ├─ 웹 UI (Svelte, :5174)
  └─ Swagger (/docs)
        ↓
FastAPI (:8100)
  backend/apis/          HTTP 경계. 라우터 · 미들웨어 · 실행 헬퍼
        ↓
  backend/agents/        유형별 생성 로직 (BaseAgent 공통 흐름)
        ↓
  backend/prompts/       base_system + item_craft + difficulty + 유형별 (4겹)
  backend/llm/           provider 선택 + 재시도 + JSON 복구
  backend/toolkit/       텍스트·검증·렌더·어휘 (순수 함수)
  backend/schemas/       Pydantic 계약
        ↓
  backend/storage/       "사용" 시에만 저장 → JSON 파일 (+ 선택적 DB)
```

```text
backend/
  main.py        앱 조립만(25줄). 라우트를 여기에 두지 마세요
  apis/          __init__(ROUTERS) deps health generation problems wordbooks streaming middleware
  agents/ core/ db/ llm/ prompts/ schemas/ storage/ toolkit/
  problems/      저장된 문항 JSON (+ JSON Schema)
  wordbooks/     저장된 단어장 JSON

frontend/src/
  App.svelte     홈 + 탭 + 개인DB 하위 구분 라우팅
  components/    HomeLanding ProblemCreator WordbookCreator LibraryHub
                 ProblemLibrary WordbookLibrary MockExamBuilder ProblemView
                 wordbook/WordCard  exam/ProblemSheet  exam/VocabSheet
  lib/api/       모든 HTTP 호출의 단일 통로
  lib/problemUtils.js
  styles/        index.css + 역할별 18개 (@import 순서 = 우선순위)

tests/           295개. API·저장소·스키마·검증·정합성
dev.sh           macOS/Linux 실행
dev.bat dev.ps1  Windows 실행
package.sh       배포용 zip (.venv / node_modules / .env 제외)
START_HERE.md    비개발자 수령인용 안내
.env.example     .env 템플릿(키 없음)
```

---

## 3. 지원 유형

| 유형 | Endpoint | Agent |
|---|---|---|
| 제목 | `POST /api/v1/title` | `TitleAgent` |
| 주제 | `POST /api/v1/topic` | `TopicAgent` |
| 요약 | `POST /api/v1/summary` | `SummaryAgent` |
| 함축의미 | `POST /api/v1/implicit` | `ImplicitAgent` |
| 문장삽입 | `POST /api/v1/insertion` | `InsertionAgent` |
| 글의 순서 | `POST /api/v1/order` | `OrderAgent` |
| 무관문장 | `POST /api/v1/irrelevant` | `IrrelevantAgent` |
| 빈칸 | `POST /api/v1/blank` | `BlankAgent` |
| 지칭 | `POST /api/v1/reference` | `ReferenceAgent` |
| 어휘 | `POST /api/v1/vocab` | `VocabAgent` |
| 어법 | `POST /api/v1/grammar` | `GrammarAgent` |

문항이 아닌 기능: **핵심단어장** `POST /api/v1/wordbook` (`WordbookAgent`).
응답·저장소·요청 스키마가 위 11개와 다릅니다. 자세한 차이는 `docs/CLAUDE_backend.md` §9.

스트리밍: `POST /api/v1/stream/{problem_type}`, `POST /api/v1/stream-wordbook`
저장·조회: `POST|GET /api/v1/problems`, `GET /api/v1/problems/{problem_uid}`,
`POST|GET /api/v1/wordbooks`, `GET|DELETE /api/v1/wordbooks/{wordbook_uid}`
상태: `GET /health`

---

## 4. 반드시 지켜야 할 규칙

되돌리면 조용히 깨지는 것들입니다. 각 항목의 근거는 상세 문서에 있습니다.

### 백엔드

1. **생성은 저장하지 않습니다.** 사용자가 "사용"을 눌러 저장 엔드포인트를 호출할 때만
   개인DB에 들어갑니다. 회귀 테스트: `test_generation_no_longer_auto_saves`
2. **라우트를 `main.py` 에 추가하지 마세요.** `backend/apis/` 에 파일을 만들고
   `apis/__init__.py` 의 `ROUTERS` 에만 등록합니다.
3. **싱글턴은 모듈 속성으로 접근하세요.** `from backend.apis import deps` 후 `deps.problem_store`.
   값으로 import 하면 테스트의 monkeypatch 가 먹지 않습니다.
4. **`run_in_executor` 에는 `contextvars.copy_context()` 가 필요합니다.**
   빼면 사용량 로그와 스트리밍 진행 상황이 예외 없이 사라집니다.
5. **동의어 교체는 생성 "전"에 합니다.** 생성 후에 바꾸면 원문 복원 검증이 전부 깨집니다.
   비스트리밍(`deps.run_agent`)과 스트리밍(`streaming._stream_agent`) **양쪽 모두**에 있어야 합니다.
6. **재시도 상한을 하드코딩하지 마세요.** `LLM_MAX_RETRIES`(기본 1)와
   `LLM_MAX_CALLS_PER_REQUEST`(기본 12)를 씁니다. `range(2)`/`range(3)` 으로 되돌리면
   재시도가 곱해져 비용이 급증합니다.
7. **재시도·JSON 복구는 `llm/clients/base.py` 에만** 둡니다. provider 별 복제 금지.
8. **프롬프트를 한 줄 지시로 되돌리지 마세요.** 4겹 조립과 유형별 필수 3절을
   `tests/test_difficulty_prompts.py`(111개)가 고정합니다.
9. **단어장에는 난이도가 없습니다.** `max_related` 로만 개수를 자릅니다.
10. **`lemma` 에 일반 `-es` 규칙 금지** (`routines` → `routin`).
    후보 dedup 키와 커버리지 대조 키는 둘 다 `match_key` 로 같아야 합니다.

### 프론트엔드

11. **컴포넌트에서 `fetch` 를 직접 부르지 마세요.** `lib/api/` 를 통합니다.
12. **`styles/index.css` 의 `@import` 순서를 바꾸지 마세요.**
    `responsive.css` 와 `print.css` 는 반드시 마지막입니다.
13. **`Set`/`Map` 상태는 새 객체로 교체**해야 Svelte 가 감지합니다.
14. **Svelte 4 입니다.** `export let` / `$:` 를 씁니다. Svelte 5 runes 는 쓰지 않습니다.
15. **`App.svelte` 에 기능을 다시 몰아넣지 마세요.**

### 공통

16. 기존 사용자 변경을 되돌리지 마세요.
17. 새 유형을 추가할 때는 **Agent · Schema · Prompt · Route · Smoke Test 를 함께** 추가합니다.
18. 저장 구조를 바꿀 때는 `SavedProblemRecord` 와 기존 `backend/problems` 호환성을 확인합니다.
19. 백엔드/프론트 양쪽에 있는 목록은 함께 고칩니다
    (예: 동의어 교체 지원 유형 — `synonym_swapper.SUPPORTED_TYPES` 와 `ProblemCreator.SWAP_TYPES`).
20. **`.venv` 와 `frontend/node_modules` 는 절대 배포물에 넣지 마세요.**
    `.venv/pyvenv.cfg` 의 `home` 과 `bin/*` 셔뱅에 만든 PC 의 절대경로가 박히고,
    node_modules 에는 플랫폼 전용 바이너리가 들어갑니다.
    `package.sh` 가 이 둘과 `.env`(API 키)를 제외합니다.

---

## 5. 환경 변수

`backend/core/config.py` 기준입니다. 값의 의미는 `docs/CLAUDE_backend.md` 참조.

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
LLM_MAX_RETRIES=1
LLM_MAX_CALLS_PER_REQUEST=12
ENABLE_SELF_CHECK=false

ENABLE_PROBLEM_PERSISTENCE=true
ENABLE_DB_PERSISTENCE=false
DATABASE_URL=
DATABASE_ECHO=false

ENABLE_USAGE_LOG=true
USAGE_LOG_DIR=problem_log
LLM_INPUT_PRICE_PER_MTOK=0.0
LLM_OUTPUT_PRICE_PER_MTOK=0.0
USD_KRW_RATE=0.0
```

`APP_ENV=test` 는 LLM 을 `MockLLMClient` 로, DB 저장을 강제로 끕니다.

---

## 6. 실행

한 번에 실행(권장). 의존성 동기화 + 백엔드/프론트엔드 동시 기동, `Ctrl+C` 로 둘 다 종료:

```bash
./dev.sh          # macOS / Linux
dev.bat           # Windows (dev.ps1 을 실행 정책 우회로 호출)
```

- 기본 포트: 백엔드 `8100`, 프론트엔드 `5174` (`BACKEND_PORT` / `FRONTEND_PORT`)
- 옵션: `--no-reload`, `--skip-install`
- 로그: 터미널 + `.logs/backend.log`, `.logs/frontend.log`

개별 실행:

```bash
uv sync --group dev
cd frontend && npm ci

uv run uvicorn backend.main:app --reload --host 0.0.0.0 --port 8100
cd frontend && npm run dev

make start     # 백엔드
make frontend  # 프론트엔드
make up / make down   # Docker
```

---

## 7. 테스트와 검증

```bash
uv run pytest                 # 전체 295개
cd frontend && npm run build  # 프론트 빌드
git diff --check              # 공백 점검
```

구조를 바꾸면 아래 정합성 테스트가 먼저 깨집니다. 기능 테스트가 아니라
**코드와 문서/배포 설정이 어긋나는 것을 잡는** 테스트입니다.

| 테스트 | 고정하는 것 |
|---|---|
| `tests/test_project_consistency.py` | 죽은 설정, 문서에 없는 엔드포인트·환경변수, 비밀 유출, provider 분리, 문서가 가리키는 경로의 실존 |
| `tests/test_difficulty_prompts.py` | 프롬프트 4겹 조립, 각 층 존재, 유형별 필수 절, 프롬프트 파일 인벤토리 |
| `tests/test_styles_structure.py` | 프론트 CSS 분할 구조 |
| `tests/test_frontend_components.py` | Svelte 컴포넌트가 import 없이 쓰이지 않음 (Vite 는 경고만 냅니다) |
| `tests/test_save_and_stream.py` | 생성이 자동 저장하지 않음 |
| `tests/test_usage_logging.py` | 워커 스레드에서도 사용량이 기록됨 |
