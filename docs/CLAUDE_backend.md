# CLAUDE_backend.md — 백엔드 개발 가이드

`Problem_Change_Project` 백엔드(FastAPI)의 구조와 동작 원리입니다.
루트 `CLAUDE.md`가 상위 진입점이고, 이 문서가 백엔드 상세를 담당합니다.
프론트엔드는 `docs/CLAUDE_frontend.md`를 보세요.

**문서와 코드가 충돌하면 코드가 맞습니다.** 그때는 이 문서를 고치세요.

---

## 1. 레이어 구조

요청은 항상 아래 방향으로만 흐릅니다. 역방향 import 는 금지입니다.

```text
apis/        HTTP 경계        FastAPI import 는 여기서만
  ↓
agents/      유형별 생성 로직   요청 → 문항
  ↓
llm/         provider 호출     프롬프트 → JSON
prompts/     프롬프트 조립
toolkit/     순수 함수 유틸     텍스트·검증·렌더·어휘
schemas/     Pydantic 계약     경계마다 검증
  ↓
storage/     저장              JSON 파일 + 선택적 DB
```

`core/` 는 어느 층에서나 쓰는 횡단 관심사입니다(설정·로깅·에러·사용량·진행상황).

### 디렉터리

```text
backend/
  main.py        앱 조립만(25줄). 라우트를 여기에 두지 마세요
  apis/
    __init__.py    ROUTERS 등록 + register(app)
    deps.py        에이전트·저장소·설정 싱글턴 + run_sync/run_agent 헬퍼
    health.py      GET /health
    generation.py  11개 유형 생성 엔드포인트
    problems.py    문항 저장·조회
    wordbooks.py   단어장 생성·저장·조회·삭제
    streaming.py   SSE 생성 2종
    middleware.py  요청 단위 토큰 사용량 집계
  agents/        BaseAgent + 유형별 11개 + wordbook_agent + synonym_swapper
  core/          config / logging / errors / usage / progress
  db/            SQLAlchemy 모델(문항 전용)
  llm/           provider.py + clients/ + json.py + schema.py
  prompts/       *.md 22개 + loader.py
  schemas/       요청·응답·저장 Pydantic 모델
  storage/       problem_store / wordbook_store / persistence / db_store
  toolkit/       text discourse labels render validators lexicon
                 synonym_swap difficulty vocab_grammar_normalize
  problems/      "사용"으로 저장된 문항 JSON (+ JSON Schema)
  wordbooks/     "사용"으로 저장된 단어장 JSON
```

---

## 2. 라우터 규칙

### 새 라우터 추가

1. `backend/apis/` 에 파일을 만들고 `router = APIRouter()` 를 선언합니다.
2. `backend/apis/__init__.py` 의 `ROUTERS` 튜플에 등록합니다.
3. `main.py` 는 건드리지 않습니다.

`ROUTERS` 등록 순서가 Swagger 문서 표시 순서입니다.

### 싱글턴 접근 방식 — 반드시 지켜야 합니다

```python
# 올바름
from backend.apis import deps
record = await deps.run_sync(deps.problem_store.get_record, uid)

# 틀림 — 테스트의 monkeypatch 가 먹지 않습니다
from backend.apis.deps import problem_store
```

값으로 import 하면 라우터가 모듈 로딩 시점의 객체를 영구히 붙들고,
테스트가 `deps.problem_store` 를 갈아끼워도 옛 객체를 계속 씁니다.

### 실행 헬퍼

| 헬퍼 | 위치 | 역할 |
|---|---|---|
| `run_sync(func, ...)` | `deps.py` | 동기 함수를 워커 스레드에서 실행. contextvars 복사 포함 |
| `run_agent(agent, request)` | `deps.py` | 동의어 교체 전처리 → 생성 → swap meta 부착 → 예외를 HTTP 상태로 변환 |
| `apply_synonym_swap` / `attach_swap_meta` | `deps.py` | 동의어 교체 전처리와 meta 기록 |

`run_agent` 의 예외 매핑:

| 예외 | HTTP |
|---|---|
| `InputValidationError` | 422 |
| `GenerationError` | 500 |
| `PersistenceError` | 500 |
| 그 외 | 502 |

---

## 3. 엔드포인트 전체 목록

### 생성 (저장하지 않음)

| 유형 | Endpoint | Agent | Prompt | Schema |
|---|---|---|---|---|
| 제목 | `POST /api/v1/title` | `TitleAgent` | `backend/prompts/title.md` | `backend/schemas/title.py` |
| 주제 | `POST /api/v1/topic` | `TopicAgent` | `backend/prompts/topic.md` | `backend/schemas/topic.py` |
| 요약 | `POST /api/v1/summary` | `SummaryAgent` | `backend/prompts/summary.md` | `backend/schemas/summary.py` |
| 함축의미 | `POST /api/v1/implicit` | `ImplicitAgent` | `backend/prompts/implicit.md` | `backend/schemas/implicit.py` |
| 문장삽입 | `POST /api/v1/insertion` | `InsertionAgent` | `backend/prompts/insertion.md` | `backend/schemas/insertion.py` |
| 글의 순서 | `POST /api/v1/order` | `OrderAgent` | `backend/prompts/order.md` | `backend/schemas/order.py` |
| 무관문장 | `POST /api/v1/irrelevant` | `IrrelevantAgent` | `backend/prompts/irrelevant.md` | `backend/schemas/irrelevant.py` |
| 빈칸 | `POST /api/v1/blank` | `BlankAgent` | `backend/prompts/blank.md` | `backend/schemas/blank.py` |
| 지칭 | `POST /api/v1/reference` | `ReferenceAgent` | `backend/prompts/reference.md` | `backend/schemas/reference.py` |
| 어휘 | `POST /api/v1/vocab` | `VocabAgent` | `backend/prompts/vocab.md` | `backend/schemas/vocab.py` |
| 어법 | `POST /api/v1/grammar` | `GrammarAgent` | `backend/prompts/grammar.md` | `backend/schemas/grammar.py` |
| 핵심단어장 | `POST /api/v1/wordbook` | `WordbookAgent` | `backend/prompts/wordbook.md` | `backend/schemas/wordbook.py` |

### 스트리밍 생성 (프론트가 실제로 쓰는 경로)

| Endpoint | 대상 |
|---|---|
| `POST /api/v1/stream/{problem_type}` | 문항 11종 |
| `POST /api/v1/stream-wordbook` | 단어장 |

### 저장·조회

| Endpoint | 설명 |
|---|---|
| `POST /api/v1/problems` | "사용" — `{request, result}` 를 받아 저장 (201) |
| `GET /api/v1/problems` | 저장 문항 목록. `problem_type`, `limit` 쿼리 |
| `GET /api/v1/problems/{problem_uid}` | 저장 문항 1건 |
| `POST /api/v1/wordbooks` | "사용" — `{title, request, result}` 저장 (201) |
| `GET /api/v1/wordbooks` | 저장 단어장 목록 |
| `GET /api/v1/wordbooks/{wordbook_uid}` | 저장 단어장 1건 |
| `DELETE /api/v1/wordbooks/{wordbook_uid}` | 단어장 삭제 (204) |
| `GET /health` | 상태 확인 |

---

## 4. 생성과 저장의 분리

**생성 엔드포인트는 저장하지 않습니다.** 사용자가 화면에서 "사용"을 눌러야
저장 엔드포인트가 호출되고 그때 개인DB에 들어갑니다.

```text
[생성]
POST /api/v1/{type}  또는  POST /api/v1/stream/{type}
  → deps.run_agent (또는 streaming._stream_agent)
  → apply_synonym_swap        동의어 교체 전처리
  → Agent.generate/agenerate
      → preprocess            정규화 + 60단어 미만 거부
      → analyze               파이썬으로 지문 분석 (LLM 아님)
      → _try_llm_generate     프롬프트 조립 → LLM → 스키마 검증
      → 유형별 validator
      → 실패 시 로컬 폴백
  → attach_swap_meta
  → ProblemResponse 반환 (저장 안 함)

[저장 - "사용" 버튼]
POST /api/v1/problems  {request, result}
  → PROBLEM_RESULT_MODELS 로 유형별 재검증
  → ProblemPersistenceService
  → backend/problems JSON + 선택적 DB

POST /api/v1/wordbooks {title, request, result}
  → LocalWordbookStore → backend/wordbooks JSON
```

이전에는 `_run_agent` 가 자동 저장했습니다. **되돌리지 마세요.**
회귀 테스트: `test_generation_no_longer_auto_saves`, `test_stream_does_not_save`

`ENABLE_PROBLEM_PERSISTENCE=false` 면 저장 엔드포인트가 409 를 돌려줍니다.
생성은 이 설정과 무관하게 동작합니다.

---

## 5. BaseAgent

`backend/agents/base.py`. 모든 문항 에이전트의 공통 흐름입니다.

| 메서드 | 역할 |
|---|---|
| `preprocess(passage)` | `normalize_text` + `truncate_if_too_long`. 60단어 미만이면 `InputValidationError` |
| `analyze(passage)` | 문단/문장 분할, 담화표지어, 키워드 빈도, thesis 후보, 대명사 후보 — **전부 파이썬** |
| `_prompt_context(...)` | 프롬프트 `$변수` 채우기 |
| `_try_llm_generate(...)` | 프롬프트 조립 → `generate_json` → 스키마 검증 → self-check |
| `_run_self_check(problem)` | `ENABLE_SELF_CHECK=true` 일 때만 LLM 재검증 |
| `_meta(request, analysis)` | `difficulty`, `seed`, `debug=true` 면 분석 일부 |
| `agenerate(request)` | `generate` 를 워커 스레드에서 실행 |

### 지문 분석은 LLM 을 쓰지 않습니다

`analyze()` 는 순수 파이썬 계산입니다. 초기 설계(`docs/spec-initial.md`)의
"Pass A: Analysis JSON"(LLM 호출)은 구현되지 않았고, 그래서 `prompts/analysis.md` 는
삭제했습니다. 분석을 LLM 으로 되돌리면 호출이 유형마다 1회씩 늘어납니다.

### `analysis_json` 은 문장 목록을 빼고 보냅니다

`PassageAnalysis.to_prompt_payload()` 가 `paragraphs[].sentences` 를 제거합니다.
이어붙이면 `$passage` 로 이미 보낸 원문과 글자 단위로 같아서, 그대로 두면
같은 지문을 두 번 보내게 됩니다(143단어 지문 기준 호출당 약 233토큰).

`function` 과 `markers` 는 grammar/order/reference/vocab 프롬프트가 참조하므로
**`paragraphs` 를 통째로 빼지 마세요.** 문장 목록이 필요한 에이전트는
`extra_context` 로 따로 넘깁니다.

### contextvars 전파 — 빼면 조용히 깨집니다

`run_in_executor` 는 contextvars 를 자동으로 넘기지 않습니다.
`BaseAgent.agenerate`, `deps.run_sync`, `streaming._stream_agent` 세 곳 모두
`contextvars.copy_context()` 로 명시 전달합니다.

빼면 워커 스레드의 LLM 호출이 요청 recorder 에 **기록되지 않고**(사용량 로그가 빈 채로 남고),
스트리밍 진행 상황도 emitter 를 못 찾아 사라집니다. 둘 다 예외가 아니라 침묵 실패입니다.

회귀 테스트: `test_usage_survives_the_thread_executor`

---

## 6. 프롬프트 구조

### 4겹 조립 (`render_prompt`)

문항 프롬프트는 뒤가 앞을 구체화하므로 **순서가 의미를 가집니다.**

| 층 | 파일 | 역할 |
|---|---|---|
| 1 | `base_system.md` | 출력 형식·JSON 규칙 |
| 2 | `item_craft.md` | 공통 출제 기법 — 오답 제작 레시피, 유일성 증명, 실패 사례 |
| 3 | `difficulty.md` | 난이도 5지표 |
| 4 | `{유형}.md` | 그 유형의 지문 적합성·대상 선정·오답 분류·실패 사례 |

```python
# backend/prompts/loader.py
def render_prompt(name, **context):
    parts = [load_prompt("base_system"), load_prompt("item_craft"),
             load_prompt("difficulty"), load_prompt(name)]
    return Template("\n\n".join(parts).strip()).safe_substitute(**context)
```

단어장·동의어 교체는 이 경로를 쓰지 않습니다. `base_system.md` 가
"선지 5개/정답 1개"를 전제하기 때문에, 각자 자기 base 를 갖고
`render_prompt_with_base(base, body, **context)` 로 2겹 조립합니다.

### 프롬프트 파일 인벤토리 (22개)

| 구분 | 파일 | 호출 조건 |
|---|---|---|
| 공통 층 | `base_system` `item_craft` `difficulty` | 항상 (합쳐져서 나감) |
| 문항 11종 | `title` `topic` `summary` `blank` `implicit` `insertion` `order` `irrelevant` `reference` `vocab` `grammar` | 유형 선택 시 |
| 빈칸 보조 | `blank_uniqueness_check` | 빈칸 생성 직후 **항상**(LLM 켜져 있을 때) |
| 빈칸 보조 | `blank_choices_repair` | 위 검증 실패 시**만** |
| 공통 보조 | `self_check` | `ENABLE_SELF_CHECK=true` 일 때**만** (기본 false) |
| 단어장 | `wordbook_system` | base 층. `wordbook`/`wordbook_expand` 양쪽에 붙음 |
| 단어장 | `wordbook` | 1차 추출 |
| 단어장 | `wordbook_expand` | 미커버 후보 2개 이상일 때만 |
| 동의어 교체 | `synonym_swap_system` | base 층 |
| 동의어 교체 | `synonym_swap` | `synonym_swap=true` 이고 지원 유형일 때 |

파일을 추가·삭제하면 `tests/test_difficulty_prompts.py` 의
`test_no_unused_prompt_files` / `test_every_loaded_prompt_exists` /
`test_every_prompt_actually_renders` 가 잡습니다.

### item_craft.md — 공통 출제 기법

`C1 지문 적합성` · `C2 오답 제작 레시피` · `C3 선지 표면 균형` ·
`C4 정답 유일성 증명` · `C5 해설 품질` · `C6 흔한 반려 사유`

C2 가 핵심입니다. 이전에는 오답 패턴을 **이름만**(`too narrow`) 나열해서
모델이 알아서 지어냈습니다. 지금은 **만드는 방법**을 줍니다.

| 변형 | 레시피 |
|---|---|
| `scope_narrow` | 정답의 일반어를 지문에 나온 특정 사례로 바꾼다. 참이지만 일부만 포괄 |
| `scope_broad` | 정답의 구체적 주장을 일반적 교훈으로 바꾼다 |
| `polarity_flip` | 내용어는 유지하고 입장만 뒤집는다 |
| `agent_swap` | 행위는 유지하고 행위자/대상을 바꾼다 |
| `degree_shift` | 수량화를 바꾼다(always↔sometimes) |
| `causal_reverse` | 원인과 결과를 뒤집는다 |
| `partial_truth` | 지문에 실제로 있는 참인 문장이되 중심 내용이 아닌 것 |
| `keyword_lure` | 지문의 인상적인 단어로 지문이 하지 않은 주장을 만든다 |

`partial_truth` 와 `keyword_lure` 가 가장 강력합니다. **지문에서 검증 가능**하기 때문입니다.

### 유형별 프롬프트의 필수 3절

1. **지문 적합성 / 대상 선정** — 이 지문이 이 유형에 맞는가, 어디를 빈칸·밑줄로 삼는가
2. **오답 분류** — 선지가 글인 유형(제목·주제·요약·빈칸·함축)은 C2 변형을 지정,
   선지가 표식인 유형(삽입·순서·무관·지칭·어휘·어법)은 자체 판별 장치 목록
3. **유형별 실패 사례** — 검토자가 반려하는 지점

한 줄짜리 지시로 되돌리지 마세요. `tests/test_difficulty_prompts.py`(111개)가
조립 순서·각 층의 존재·유형별 필수 절을 고정합니다.
`loader.py` 의 조립이 풀리면 44개가 실패합니다.

---

## 7. 난이도 설계

난이도는 형용사가 아니라 **측정 가능한 5개 지표**입니다.
`backend/prompts/difficulty.md` 하나에 정의하고 11개 문항 프롬프트 전부에 자동으로 붙습니다.

| 지표 | easy | mid | hard |
|---|---|---|---|
| L1 정답 패러프레이즈 거리 | 내용어 2~3개 그대로 | 1개 이하 + **두 문장 융합 필수** | 0개 |
| L2 오답–정답 거리 | 4개 중 3개가 주제 이탈 | 2개가 범위/극성에서 실패 | **주제 이탈 오답 금지**, 4개 모두 한 축에서만 실패 |
| L3 근거 범위 | 1문장 | 정확히 2문장, 서로 다른 기여 | 3문장 이상, 떨어진 위치 포함 |
| L4 선지 어휘 | A2~B1 | B1~B2 | B2~C1 (2개 이상 C1 포함) |
| L5 매력적 오답 수 | 1 | 2 | 3 이상 |

유형별 프롬프트에는 이 지표를 **그 유형의 기계로 번역한 짧은 블록**만 둡니다
(type-specific mapping of the shared levers). 한 줄짜리 형용사로 되돌리지 마세요 —
그러면 easy/mid/hard 가 구분되지 않습니다. 실측으로 확인한 문제였습니다.

`difficulty.md` 에는 모델이 출력 전에 스스로 5지표를 세어 보는
자체 감사 절차가 들어 있고, "세 난이도는 눈에 띄게 달라야 한다"를 명시합니다.
지표끼리 충돌하면 **정답 유일성이 이깁니다.**

`backend/toolkit/difficulty.py` 의 `blank_span_type` 은 빈칸 전용으로,
난이도별 빈칸 단위(word/phrase/clause)를 정합니다.

---

## 8. 동의어 교체 (지문 변형)

암기한 지문을 낯설게 만들어 학생이 실제로 읽게 하는 기능입니다.
`synonym_swap=true` 일 때만 동작합니다.

### 반드시 생성 "전"에 적용합니다

생성 후에 단어를 바꾸면 `validate_blank_from_original`(빈칸+정답 = 원문 복원) 같은
검증이 전부 깨집니다. 전처리로 두면 **바뀐 지문이 그 문항의 원문**이 되어
기존 검증이 그대로 살아납니다.

```text
원문 → SynonymSwapper → 교체된 지문 → 기존 에이전트 → 기존 검증 전부 통과
```

| 파일 | 역할 |
|---|---|
| `backend/toolkit/synonym_swap.py` | 개수 산정(`target_swap_count`), 거부 규칙(`rejection_reason`), 적용 |
| `backend/agents/synonym_swapper.py` | LLM 제안 요청 + 지원 유형 판정(`SUPPORTED_TYPES`) |
| `backend/apis/deps.py` | `apply_synonym_swap` / `attach_swap_meta` |
| `backend/apis/streaming.py` | 스트리밍 경로에서도 동일 전처리 호출 |

### 개수는 문장당 밀도로 정합니다

easy 0.7 / mid 1.0 / hard 1.5 (상한 12).
문장당 1개 미만이면 안 바뀐 문장이 많아 학생이 "봤던 지문"으로 인식하고,
2개를 넘으면 지문이 부자연스러워져 난이도가 어휘 때문에 엉뚱하게 올라갑니다.

### 적용 유형은 5개뿐입니다 — 넓히지 마세요

`title` / `topic` / `summary` / `blank` / `implicit`

| 제외 유형 | 이유 |
|---|---|
| `vocab` | "한 단어만 문맥상 부적절"이 문제인데, 교체된 단어가 어색하면 정답이 둘이 됩니다 |
| `grammar` | 교체가 수일치/시제/연어를 건드리면 의도치 않은 어법 오류가 생깁니다 |
| `insertion` `order` `irrelevant` | 연결어가 정답 근거인데 흔들릴 위험이 큽니다 |

### LLM 제안을 그대로 믿지 않습니다

`rejection_reason` 이 서버에서 다시 거릅니다:

- 연결어/담화표지 — `MARKERS` **구성 단어 포함**.
  `as a result` 의 `result` 를 바꾸면 `as a outcome` 이 됩니다
- 지문에 2번 이상 등장하는 단어 → **되돌리기가 엉뚱한 곳까지 되돌리므로 1회 등장만 허용**
- 기초 어휘, 같은 어근의 변화형, 숫자 포함, 문장 중간 대문자(고유명사)

교체 내역은 `meta.synonym_swap = {count, swaps}` 로 내려갑니다.
되돌리기는 프론트가 처리합니다(`docs/CLAUDE_frontend.md` 참조).

### 난이도별 단어 선별 기준

문항 설계가 아니라 **단어 선별** 문제라 별도 기준(`synonym_swap.md`)을 씁니다.

| | 고를 단어 | 바꿔 넣을 말 | 개수 |
|---|---|---|---|
| easy | A2~B1, 논지어 제외 | 고빈도 일상어 | 문장당 0.7 |
| mid | B1~B2 | 중빈도 학술어 | 문장당 1.0 |
| hard | B2~C1 + 주제어 | 저빈도 근접 동의어 | 문장당 1.5 |

레벨을 섞지 않습니다. easy 에 C1 대체어 하나가 들어가면 레벨이 무너집니다.

---

## 9. 핵심단어장

문항이 아니라 어휘 학습 기능이라 11개 유형과 계약이 다릅니다.

| | 문항 | 단어장 |
|---|---|---|
| 요청 | `GenerateRequest` | `WordbookRequest` |
| 응답 | `ProblemResponse` (선지·정답 있음) | `WordbookResponse` (없음) |
| 저장소 | `backend/problems` | `backend/wordbooks` |
| DB | `ENABLE_DB_PERSISTENCE` 대상 | **파일만.** DB 테이블 없음 |
| base 프롬프트 | `base_system.md` | `wordbook_system.md` |
| 난이도 | `difficulty` 있음 | **없음** |

### 커버리지 전략

주된 실패 방식은 오답이 아니라 **누락**입니다. LLM 에게 그냥 "핵심단어를 뽑아라"라고
하면 10줄 지문에서 2~3개만 뽑고 끝냅니다. 그래서 서버가 커버리지를 강제합니다.

1. `backend/toolkit/lexicon.py` 가 지문에서 후보 단어를 먼저 뽑습니다.
   기초 어휘(`BASIC_WORDS`, 494개)를 제외하고 얕은 표제어 추출(`lemma`)로 변화형을 묶습니다.
2. 이 목록을 프롬프트에 **하한선으로** 넘깁니다("floor, not a ceiling").
   함께 넘기는 `min_entries` 는 후보 수의 70%(최소 8)입니다.
3. 응답 후 `missing_candidates` 로 빠진 후보를 계산하고,
   2개 이상 남으면 `wordbook_expand.md` 로 **보강 패스**를 돌려 빠진 단어만 다시 받습니다
   (`MAX_EXPANSION_PASSES = 2`).
4. 그래도 남으면 `meta.uncovered_candidates` 로 내려보내 UI 에 노출합니다.
   조용히 숨기지 않습니다.

### 주의할 점

- **후보 dedup 키와 커버리지 대조 키는 반드시 같아야 합니다.** 둘 다 `match_key` 를 씁니다.
  서로 다른 키를 쓰면 후보 목록에 중복이 남거나 미커버 계산이 어긋납니다.
- **`lemma` 에 일반 `-es` 규칙을 다시 넣지 마세요.** `routines` 가 `routin` 이 되어
  표제어가 깨집니다. 치찰음 뒤 `-es` 는 `sses`/`ches`/`shes`/`xes` 규칙이 이미 처리합니다.
- `BASIC_WORDS` 추가는 보수적으로. **누락이 과추출보다 나쁩니다.**
  다의어(`free`, `certain`, `process`)는 기초어처럼 보여도 제외하지 않습니다.
- LLM 이 꺼져 있으면 뜻·동의어를 지어내지 않고 후보 단어만 반환하며,
  `meta.generation_mode="local_fallback"` 과 `meta.notice` 로 반쪽 결과임을 알립니다.
- **난이도가 없습니다.** 예전에는 easy/mid/hard 로 동의어 수준을 갈랐지만,
  학습자가 쉬운 동의어만 받거나 어려운 것만 받게 되어 쓸모가 떨어졌습니다.
  지금은 한 목록에 쉬운 것 → 중간 학술어 → 정밀 근접어 순으로 담고
  `max_related`(1~8)로만 개수를 자릅니다. 되돌리지 마세요.

### 응답 meta

| 필드 | 설명 |
|---|---|
| `candidate_count` | 서버가 뽑은 후보 수 |
| `entry_count` | 실제 정리된 단어 수 |
| `uncovered_candidates` | 보강 후에도 정리되지 않은 단어 |
| `generation_mode` | `llm` 또는 `local_fallback` |
| `notice` | 결과가 불완전할 때의 안내 |

---

## 10. 빈칸 3단 구조

빈칸은 "정답 2개" 사고가 가장 잘 나는 유형이라 검증과 부분 수리를 따로 뒀습니다.
LLM 호출이 유형 중 유일하게 3종류입니다.

```text
blank.md                   빈칸 문항 생성           항상
  ↓
blank_uniqueness_check.md  정답이 정말 유일한가     LLM 켜져 있으면 항상
  ↓ (실패 시에만)
blank_choices_repair.md    지문은 그대로, 선지만 재생성
  ↓
다시 uniqueness_check → 그래도 실패하면 로컬 폴백
```

재시도 시 이미 쓴 `blank_span` 은 `excluded_spans` 로 넘겨 재사용을 막습니다.

---

## 11. 스트리밍(SSE)

생성이 40~70초 걸려 체감 대기가 길기 때문에 진행 상황을 흘려보냅니다.

| 이벤트 | 내용 |
|---|---|
| `status` | 진행 단계 (`start` / `analyze` / `candidates` / `generating` / `expanding` / `validating`) |
| `partial` | 중간 결과. 단어장 1차 정리 결과가 여기로 옵니다 |
| `done` | 최종 결과(비스트리밍 엔드포인트와 같은 형식) |
| `error` | 실패. `detail` 과 `status` 포함 |

구현: 에이전트가 `backend/core/progress.py` 의 `emit_progress(...)` 를 호출하면
`ProgressEmitter` 가 `loop.call_soon_threadsafe` 로 큐에 넣고,
`backend/apis/streaming.py` 의 `_stream_agent` 가 꺼내 SSE 프레임으로 내보냅니다.

### 주의할 점

- **LLM 응답 자체는 토큰 단위로 스트리밍하지 않습니다.** 구조화된 JSON 을 스키마로
  받기 때문에 부분 JSON 은 파싱할 수 없습니다. 대신 단계별 진행 + 1차 결과를 먼저 보냅니다.
  단어장 실측(후보 37개): 0초 후보 수 → 35초 1차 27단어 → 49초 최종.
- `emit_progress` 는 emitter 가 없으면 아무 일도 하지 않습니다. 비스트리밍 경로에서도 안전합니다.
- **`_stream_agent` 는 `deps.run_agent` 를 거치지 않습니다.** 동의어 교체 전처리를
  안에서 직접 호출합니다. 여기서 빠뜨리면 **UI 가 쓰는 경로에서만** 교체가 조용히 무시됩니다.
  실제로 한 번 발생했던 버그입니다.
- 검증 오류(422)는 스트림이 열린 뒤 `error` 이벤트로 갑니다. HTTP 상태는 이미 200 이 나간 뒤입니다.
  프론트는 `error` 이벤트를 반드시 처리해야 합니다.
- 프록시(nginx 등)가 SSE 를 버퍼링하면 효과가 사라져 `X-Accel-Buffering: no` 를 보냅니다.

---

## 12. LLM Provider

`LLM_PROVIDER` 로 선택합니다. `APP_ENV=test` 면 무조건 `MockLLMClient` 입니다.

| Provider | 값 | 필요 설정 | 비고 |
|---|---|---|---|
| Gemini | `gemini` | `GOOGLE_API_KEY` 또는 `GEMINI_API_KEY` | 기본값 |
| OpenAI API | `openai` | `OPENAI_API_KEY` | 운영에는 이 경로 권장 |
| Codex CLI | `codex_cli` | 로컬 Codex CLI 로그인 | 실험용, 요청마다 subprocess |

Codex CLI 는 현재 로그인된 로컬 세션을 씁니다. 토큰 파일을 직접 읽어 API 키처럼
쓰는 방식이 아닙니다.

### clients/ 구조

```text
backend/llm/
  provider.py        LLM_PROVIDER → client 선택
  clients/
    base.py          공통 재시도 + JSON 복구 + 호출 예산. generate_json 은 여기에만
    gemini.py        _generate_raw + usage_metadata 수집
    openai.py        동일
    codex_cli.py     동일 (usage 없음)
    mock.py          호출 없이 payload 반환 (테스트)
  json.py            extract_first_json_object 등 파싱 복구
  schema.py          SelfCheckResult 등 공용 LLM 스키마
```

**재시도·JSON 복구 로직은 `base.py` 에만 둡니다.** provider 별로 복제하면
동작이 갈립니다. `tests/test_project_consistency.py::test_only_base_module_holds_shared_retry_logic`
가 이를 강제합니다(`mock.py` 만 의도적 예외).

### 호출 예산

```python
total_attempts = 1 + settings.llm_max_retries        # 기본 2
# 호출 전마다
if budget > 0 and attempts_made() >= budget:
    raise CallBudgetExceeded(...)
```

- `LLM_MAX_RETRIES`(기본 1) — 에이전트·provider 양쪽에서 쓰는 재시도 횟수
- `LLM_MAX_CALLS_PER_REQUEST`(기본 12) — 요청 1건의 총 호출 천장. 초과하면 로컬 폴백

**하드코딩된 `range(2)`/`range(3)` 으로 되돌리지 마세요.** 재시도가
에이전트 × provider × 스키마리스 복구로 곱해져 비용이 급증합니다.
스키마리스 복구는 **마지막 시도에만** 돕니다.

---

## 13. 저장 구조

### 문항

```text
backend/problems/{problem_type}/{passage_id}/attempt_{n}.json
```

| 필드 | 설명 |
|---|---|
| `problem_uid` | 저장 레코드 고유 ID |
| `problem_type` | 문제 유형 |
| `passage_id` | 지문 정규화 후 SHA-256 앞 16자 |
| `attempt_no` | 같은 `problem_type + passage_id` 조합의 순번(1부터) |
| `request` | 생성 요청 원본 |
| `result` | 생성 결과 |
| `storage_meta` | `file_path`, `db_saved`, `db_row_id` 등 |

JSON Schema: `backend/problems/problem_record.schema.json`

`ENABLE_DB_PERSISTENCE=true` 이고 `DATABASE_URL` 이 있으면 SQLAlchemy 로
`problem_records` 테이블에도 함께 저장됩니다(`backend/storage/db_store.py`).
`APP_ENV=test` 에서는 DB 저장이 강제로 꺼집니다.

저장 구조를 바꿀 때는 `SavedProblemRecord` 와 기존 `backend/problems` 호환성을
반드시 확인하세요.

### 단어장

`backend/wordbooks/` 에 파일로만 저장됩니다. 제목·지문·정리 결과를 함께 담습니다.

---

## 14. 토큰 사용량 / 비용 로그

LLM 을 호출하는 요청마다 `problem_log/usage-YYYY-MM-DD.log` 에
`call` 줄(호출별)과 `TOTAL` 줄(요청 합계)이 쌓입니다.
`request_id` 로 묶이고 `label` 로 어떤 프롬프트였는지 구분합니다.

```text
... | call  | request_id=355f7b36 feature=wordbook seq=1/2 ... label=wordbook        input_tokens=1799 output_tokens=9012 cost_usd=0.013968 price_source=table
... | call  | request_id=355f7b36 feature=wordbook seq=2/2 ... label=wordbook_expand input_tokens=1081 output_tokens=2342 cost_usd=0.003783 price_source=table
... | TOTAL | request_id=355f7b36 feature=wordbook calls=2 total_tokens=14234 cost_usd=0.017751 elapsed_ms=71565.6
```

| 위치 | 역할 |
|---|---|
| `backend/core/usage.py` | 단가표(`MODEL_PRICES`), 비용 계산, `UsageRecorder`, 로그 writer |
| `backend/llm/clients/*.py` | provider 별 `usage_metadata` 수집 후 `_record_usage` |
| `backend/llm/clients/base.py` | 호출 전 예산 검사 + `note_attempt` |
| `backend/apis/middleware.py` | `track_llm_usage` 가 요청 스코프 recorder 생성·flush |

### 주의할 점

- **비용은 `Decimal` 로 계산합니다.** float 누산은 장기 집계에서 오차가 쌓입니다.
- **모르는 모델이면 비용을 지어내지 않습니다.** `price_source=unknown_model` 로 남기고 비웁니다.
  provider 가 토큰 사용량을 안 주면(Codex CLI) `no_usage_metadata` 로 비웁니다.
- 단가는 바뀝니다. `MODEL_PRICES` 에 **조회일과 출처를 반드시 같이** 적으세요.
- 사용량 로깅 실패가 실제 요청을 깨뜨리면 안 됩니다. 쓰기 실패는 warning 만 남깁니다.
- **recorder 는 HTTP 미들웨어가 만듭니다.** 스크립트에서 `deps.run_agent()` 를 직접
  부르면 기록되지 않습니다. 로그가 세션 전체 사용량보다 적게 나올 수 있습니다.

---

## 15. 품질 원칙

### 원문 보존

문항 생성 중 지문을 임의로 재작성하지 않는 것이 중요합니다.

| 유형 | 처리 |
|---|---|
| `blank` | 원문 특정 span 만 `_____` 로 치환 |
| `implicit` | 원문 타깃만 `[[1]]...[[/1]]` 표식 |
| `vocab` `grammar` `reference` | 원문 내 표식으로 선택 위치 표시 |

프론트가 표식을 파싱해 밑줄/번호로 렌더링합니다.
`backend/toolkit/vocab_grammar_normalize.py` 가 어휘·어법의 표식 형태를 정규화합니다.

### 정답 유일성

- 선지 5개, 정답 1개
- 정답 label 이 choices 안에 존재
- 오답은 노골적이지 않고 지문 키워드를 공유하되 논리적으로 틀릴 것

검증은 `backend/toolkit/validators.py` 의 `validate_common` +
유형별 validator(`validate_blank_from_original` 등)가 담당합니다.

### 입력 정규화

`backend/toolkit/text.py` 의 `normalize_text` 는 **단일 개행을 공백으로 접습니다.**
PDF 에서 붙여넣은 지문이 줄마다 끊겨 오면 `blank_span` 매칭이 실패하고,
조용히 로컬 폴백(정형화된 오답)으로 떨어집니다. 되돌리지 마세요.

---

## 16. 테스트

```bash
uv run pytest                                  # 전체
uv run pytest tests/test_type_validators.py -q # 특정
```

정합성 테스트가 여러 개 있습니다. 구조를 바꾸면 이들이 먼저 깨집니다.

| 테스트 | 고정하는 것 |
|---|---|
| `tests/test_project_consistency.py` | 죽은 설정, 문서에 없는 엔드포인트/환경변수, 비밀 유출, provider 분리, 문서가 가리키는 경로의 실존 |
| `tests/test_difficulty_prompts.py` | 프롬프트 4겹 조립, 각 층 존재, 유형별 필수 절, 프롬프트 파일 인벤토리 |
| `tests/test_styles_structure.py` | 프론트 CSS 분할 구조 |
| `tests/test_save_and_stream.py` | 생성이 자동 저장하지 않음, 스트리밍도 저장하지 않음 |
| `tests/test_usage_logging.py` | 워커 스레드에서도 사용량이 기록됨 |
| `tests/test_call_budget.py` | 요청당 호출 천장 |

새 유형을 추가할 때는 **Agent, Schema, Prompt, Route, Smoke Test 를 함께** 추가하세요.

---

## 17. 리팩토링

구조 개선 작업을 할 때는 `docs/CLAUDE-refactoring.md` 를 먼저 읽으세요.
현재 구조의 실측값, 발견된 토큰 낭비, 목표 구조, 위험도순 실행 순서,
"건드리면 안 되는 것" 목록이 있습니다.

핵심만 옮기면:

- 리팩토링은 **응답 JSON 을 바꾸지 않는 작업**입니다. 바뀌면 기능 변경입니다.
- `USE_LLM_GENERATION=false` 로 폴백 출력을 스냅샷 떠서 전후 `diff` 로 동일성을 증명하세요.
- 비교 기준을 틀리지 마세요. 스테이징 내용과 비교하려면 `git show :파일` 이고,
  `git show HEAD:파일` 은 커밋된 옛 버전입니다.

### 남은 항목

- **Depends 전환(미완)** — `apis/deps.py` 의 전역 싱글턴을 FastAPI `Depends` 로 바꾸는
  작업이 보류되어 있습니다. 지금은 모듈 속성 접근 규칙(§2)으로 테스트 교체를 지탱합니다.
- 스키마리스 복구 프롬프트 단축.
- 스크립트 직접 호출 경로의 사용량 로깅(§14).
