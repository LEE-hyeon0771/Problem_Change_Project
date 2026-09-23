# CLAUDE-refactoring.md — 리팩토링 작업 지침서

이 문서는 **리팩토링을 수행하는 에이전트/개발자를 위한 작업 지침서**입니다.
평소 개발 기준은 루트의 `CLAUDE.md`이고, 이 문서는 리팩토링 기간에만 그 위에 얹힙니다.
충돌하면 **이 문서가 우선**하되, `CLAUDE.md`의 "품질 원칙"과 "주의사항"은 그대로 유효합니다.

수치는 전부 2026-09-23 기준 실측값입니다. 코드가 바뀌면 다시 재고 갱신하세요.

---

## 진행 상황 (2026-09-23 기준)

9단계 중 **8개 완료**. 남은 것은 **6단계(전역 싱글턴 → `Depends`)** 하나입니다.

| 완료 | 1 analysis 슬림화 · 2 API 레이어 · 3 WordCard · 4 CSS 분리 · 5 apis/ · 7 시트 분리 · 8 clients/ · 9 재시도 상한 |
|---|---|
| **남음** | **6 DI 전환** (위험 높음, 테스트 4개 수정 필요) |

## 0. 절대 규칙

리팩토링의 정의: **겉보기 동작을 바꾸지 않고 내부 구조만 바꾸는 것.**

1. **응답 JSON이 바뀌면 리팩토링이 아니라 기능 변경입니다.** 필드명·구조·기본값을 건드리지 마세요.
2. **각 단계마다 `uv run pytest`가 통과해야 합니다.** 168개가 기준선이고, 줄어들면 안 됩니다.
3. **한 번에 한 단계씩.** 단계를 합치지 마세요. 깨졌을 때 원인을 못 찾습니다.
4. **테스트를 고쳐서 통과시키지 마세요.** 테스트가 깨졌다면 리팩토링이 틀린 것입니다.
   단, 테스트가 **내부 구현 경로**(예: `backend.apis.deps.problem_store`)를 직접 patch 하는 경우는
   예외이며, 이때도 검증하는 **동작**은 동일하게 유지해야 합니다.
5. **`CLAUDE.md`에 "되돌리지 마세요"라고 적힌 결정은 되돌리지 마세요.**
   (자동저장 제거, 단어장 난이도 제거, `lemma`의 `-es` 규칙, 동의어 교체 지원 유형 5개)

### 단계마다 돌릴 검증

```bash
uv run pytest -q                      # 146 passed 유지
cd frontend && npx vite build         # 경고/에러 없이 빌드
./dev.sh                              # 실제 기동 후 화면에서 1회 생성
```

CSS 를 건드렸다면 **빌드 결과물을 바이트 비교**하세요. 순서가 틀어지면
빌드는 성공하는데 화면만 조용히 깨지므로, 이게 유일하게 확실한 검증입니다.

```bash
cd frontend && npx vite build && cp dist/assets/*.css /tmp/css_before.css
# ... 수정 ...
npx vite build && diff /tmp/css_before.css dist/assets/*.css && echo "동일 ✅"
```

**컴포넌트를 쪼갤 때**는 화면에 나가는 한글 문구와 CSS 클래스 집합을 비교하세요.
빌드 산출물은 minify 변수명이 바뀌어 비교할 수 없습니다. 소스에서 뽑아야 합니다.
기준은 `git show HEAD:...` 가 아니라 **직전에 스테이징한 버전(`git show :경로`)** 입니다.

```python
import re, subprocess, pathlib
ko = lambda t: {m.strip() for m in re.findall(r'[가-힣][가-힣0-9A-Za-z ()·~%/,.\-]*', t) if len(m.strip()) > 1}
old = subprocess.run(["git","show",":frontend/src/components/X.svelte"], capture_output=True, text=True).stdout
new = "".join(pathlib.Path(p).read_text() for p in [...분리된 파일들...])
assert ko(old) == ko(new), "문구 유실"
```

동작 동일성까지 확인하려면, 리팩토링 전에 스냅샷을 떠 두고 비교하세요.

```bash
# 리팩토링 전
USE_LLM_GENERATION=false uv run python -c "
from fastapi.testclient import TestClient; from backend.main import app; import json
c=TestClient(app); from tests.fixtures import PASSAGE
out={r: c.post(f'/api/v1/{r}', json={'passage':PASSAGE,'seed':1}).json()
     for r in ['title','topic','summary','blank','implicit','insertion','order','irrelevant','reference','vocab','grammar']}
json.dump(out, open('/tmp/before.json','w'), ensure_ascii=False, sort_keys=True, indent=2)"

# 리팩토링 후 같은 명령으로 /tmp/after.json 생성 뒤
diff /tmp/before.json /tmp/after.json && echo "동작 동일 ✅"
```

`USE_LLM_GENERATION=false`가 핵심입니다. 로컬 폴백은 결정론적이라 정확히 비교됩니다.

---

## 1. 착수 시점 상태 (2026-09-23 실측)

> 아래 수치는 **리팩토링을 시작하기 전** 기준입니다. 완료된 항목은 취소선과 화살표로
> 현재 값을 함께 적었습니다. 지금 상태가 궁금하면 `## 6. 완료 기준` 의 검증 커맨드를 돌리세요.

### 백엔드 5,791줄

| 파일 | 줄 | 문제 |
|---|---|---|
| ~~`main.py`~~ | ~~661~~ → **25** | ✅ 완료. `apis/` 로 분리 |
| ~~`llm/client.py`~~ | ~~581~~ → **6개 파일** | ✅ 완료. 최대 166줄 |
| `agents/blank_agent.py` | 363 | LLM 경로 + 폴백 168줄 + 수리 로직 |
| `agents/wordbook_agent.py` | 284 | 폴백이 253줄(대부분 LLM 성공 시 미사용) |

### 프론트엔드 5,414줄

| 파일 | 줄 | 문제 |
|---|---|---|
| ~~`app.css`~~ | ~~2,421~~ → **18개 파일** | ✅ 완료. 최대 378줄 |
| ~~`MockExamBuilder.svelte`~~ | ~~831~~ → **30** | ✅ 완료. ProblemSheet(548) + VocabSheet(277) 로 분리 |
| `lib/problemUtils.js` | 584 | 표시/파싱/상수가 한 파일 |

### 구조적 결함

**a. `main.py` 전역 싱글턴 25개**
```python
title_agent = TitleAgent(llm_client=llm_client, settings=settings)
... (11개 반복)
problem_store = LocalProblemStore()
wordbook_store = LocalWordbookStore()
```
import 시점에 LLM 클라이언트가 만들어집니다. 테스트가 `monkeypatch.setattr(main_module, ...)`로
전역을 갈아끼워야 하는 이유이고, 이건 냄새입니다.

**b. `_build_choices` 시그니처 불일치 (LSP 위반)**
```python
# base.py
def _build_choices(self, texts: Sequence[str], request: GenerateRequest) -> list[Choice]
# blank_agent.py / implicit_agent.py — 인자 수가 다름
def _build_choices(self, texts: list[str]) -> list[Choice]
```
같은 이름으로 오버라이드했지만 계약이 다릅니다. 상위 타입으로 다룰 수 없습니다.

**c. ~~프론트 API 호출이 5개 파일에 흩어짐~~** ✅ 완료
`lib/api/` 로 통합. 컴포넌트에서 `fetch` 직접 호출 **0건**.
에러 본문 파싱은 `client.js` 의 `extractDetail` 한 곳에만 있습니다.

**d. ~~단어 카드 마크업이 두 컴포넌트에 복제~~** ✅ 완료
`components/wordbook/WordCard.svelte` 하나로 통합.
두 화면의 표시 밀도 차이는 `detailed` prop 으로 구분합니다
(생성 화면은 예문·영어정의·뉘앙스까지, 개인DB 는 표제어·뜻·동의어만).

---

## 2. 토큰 낭비 (실측)

### ✅ 완료: `analysis_json`이 지문을 통째로 중복 전송 (2026-09-23 해결)

143단어 지문 기준:

| 항목 | 토큰 |
|---|---|
| 지문 | 253 |
| `analysis_json` | 471 |
| └ **그중 지문 중복분** | **252 (53%)** |

`PassageAnalysis.paragraphs[].sentences`가 지문을 문장 단위로 쪼개 담고 있어서,
이어붙이면 원본과 **글자 단위로 완전히 동일**합니다. 이미 `$passage`로 보낸 것을 또 보냅니다.

**`analysis_json`은 12개 프롬프트 전부에 똑같이 통째로 들어갑니다.**
요청 1건은 프롬프트 1개만 쓰지만, 어떤 유형을 고르든 분석 전체를 받습니다.

그런데 프롬프트 본문이 그 항목을 실제로 언급하는 비율은 제각각입니다.
`analysis_json` 을 받는 12개 프롬프트만 대상으로 grep 한 결과:

```
  thesis_candidates      4 / 12
  keywords               4 / 12
  markers                4 / 12   (grammar, order, reference, vocab)
  coreference_candidates 2 / 12
  paragraphs             0 / 12   ← 가장 무거운데 단 하나도 쓰지 않음
```

재현:

```bash
FILES=$(grep -l 'analysis_json' backend/prompts/*.md)
for k in thesis keywords markers coreference paragraphs; do
  echo "$k: $(echo "$FILES" | xargs grep -l "$k" | wc -l) / 12"
done
```

`title.md` 로 요청해도 지문 복제본(`paragraphs[].sentences`)을 받아가는데,
12개 프롬프트 **어디에도** 그것을 쓰라는 지시가 없습니다.

### ⚠️ `paragraphs` 를 통째로 지우면 안 되는 이유

`markers` 가 `paragraphs` **안에 중첩**되어 있습니다.

```
analysis_json
├── topic / thesis_candidates / keywords
├── paragraphs[]
│   ├── sentences   ← 지문과 100% 중복. 지워야 할 것
│   ├── function
│   └── markers     ← 4개 프롬프트가 참조. 지우면 안 되는 것
└── coreference_candidates
```

`paragraphs` 를 통째로 빼면 지문 중복은 사라지지만 `markers` 도 함께 날아갑니다.
그래서 **`sentences` 만** 제거합니다.

**조치 완료**: `PassageAnalysis.to_prompt_payload()` 를 추가하고
`base.py` / `wordbook_agent.py` 두 호출부가 이를 쓰도록 바꿨습니다.
모델이 "프롬프트에 어떻게 실릴지"를 스스로 아는 형태입니다.

```python
# backend/schemas/analysis.py
def to_prompt_payload(self) -> dict:
    payload = self.model_dump()
    for paragraph in payload["paragraphs"]:
        paragraph.pop("sentences", None)   # 지문과 100% 중복. function/markers 는 보존
    return payload
```

회귀 테스트: `tests/test_analysis_payload.py` (6개).
`sentences` 제거를 되돌리면 5개가 실패하는 것까지 확인했습니다.

131단어 지문 실측:

| 안 | 토큰 | 절감 | 정보 손실 |
|---|---|---|---|
| 현행 | 412 | — | — |
| **`sentences`만 제거 (권장)** | **179** | **233** | 없음 |
| `paragraphs` 통째 제거 | 156 | 256 | `markers` 손실 ❌ |

문장 목록이 실제로 필요한 유형(insertion/order)은 `extra_context`로 따로 받게 하세요.
**절감: 호출당 약 233토큰(입력의 약 11%).**

### ✅ 완료: 재시도 증폭 (2026-09-23 해결)

이전에는 `generate_json` 이 실패 시 **3시도 × (본요청 + 스키마리스 복구) = 최대 6회**를 돌고,
그 위에 에이전트가 또 재시도해 요청 하나가 수십 번 호출될 수 있었습니다.

**⚠️ 이 항목은 순수 리팩토링이 아닙니다.** 실패 시 더 빨리 폴백으로 떨어지도록 동작을 바꿨습니다.

조치 두 가지:

1. **재시도 1회로 통일** (`LLM_MAX_RETRIES=1`).
   `base.py` 의 `range(3)` 과 `blank`/`implicit` 의 `range(2)` 를 모두 설정 기반으로 바꿨습니다.
2. **스키마리스 복구를 마지막 시도에서만** 실행. 매 시도마다 붙이면 호출 수가 두 배가 됩니다.

실패하는 provider 로 측정한 요청당 총 호출 수:

| | 이전 | **이후** |
|---|---|---|
| blank | 12회 | **6회** |
| implicit | 12회 | **6회** |
| wordbook | 6회 | **3회** |

실제 Gemini 로 11개 유형 전부 생성해 **11/11 이 폴백 없이 LLM 경로로 성공**하는 것을 확인했습니다.

추가로 `LLM_MAX_CALLS_PER_REQUEST`(기본 12) 로 요청당 천장을 두었습니다.
`CallBudgetExceeded` 는 `GenerationError` 를 상속하므로 기존 폴백 경로를 그대로 탑니다.

**주의**: `wordbook_agent.MAX_EXPANSION_PASSES` 는 재시도가 아니라 **커버리지 보강**입니다.
빠진 단어를 채우는 기능이므로 재시도 상한과 별개로 두었습니다. 줄이면 단어 누락이 늘어납니다.

### 🟡 남은 항목: 스키마리스 복구가 전체 프롬프트를 재전송

```python
recovery_raw = self._guarded_generate_raw(prompt=self._schema_less_prompt(prompt, schema), ...)
```
`base_system`(765tok) + 유형 프롬프트(536tok)를 포함해 전부 다시 보냅니다.
복구가 필요한 건 보통 **출력 형식**이지 지시문이 아닙니다.
(마지막 시도에서만 실행하도록 줄였지만, 프롬프트 자체는 여전히 전체를 보냅니다.)

**조치 후보**: 복구 프롬프트를 "직전 출력 + 스키마 위반 사항"만 담은 짧은 형태로 교체.

### 🟢 `base_system.md` 765토큰이 모든 호출에 고정 투입

12개 프롬프트가 공유하므로 중복은 아니지만, 유형별로 필요 없는 규칙도 함께 갑니다
(예: 단어장은 이미 별도 `wordbook_system.md`를 씁니다).
프롬프트 캐싱을 쓸 수 있는 provider라면 이 부분이 캐시 대상입니다.

---

## 3. 목표 구조

### 백엔드

```text
backend/
  apis/                     # ✅ 완료 — HTTP 경계, 여기서만 FastAPI 를 import
    __init__.py             #   ROUTERS 등록
    deps.py                 #   싱글턴 + run_agent/run_sync 헬퍼
    health.py               #   GET /health
    generation.py           #   POST /api/v1/{11개 유형}
    problems.py             #   문항 저장/목록/상세
    wordbooks.py            #   단어장 생성/저장/목록/상세/삭제
    streaming.py            #   SSE 2종
    middleware.py           #   사용량 추적
  services/                 # 유스케이스 — 라우터와 도메인 사이
    problem_service.py      # 생성 + 동의어 교체 전처리 + 저장 조율
    wordbook_service.py
    streaming_service.py    # _stream_agent 를 여기로
  agents/                   # 도메인 로직 (FastAPI 를 모름)
  llm/
    clients/                # ✅ 완료
      base.py               #   공통 JSON 파싱·재시도·사용량 기록 (166줄)
      gemini.py openai.py codex_cli.py mock.py
      __init__.py           #   provider 재수출 + LLMClient 별칭
    retry.py                # generate_json 재시도 정책 분리 (9단계에서)
  core/ schemas/ storage/ toolkit/   # 현행 유지
  main.py                   # 앱 조립만. 30줄 이내가 목표
```

**핵심 원칙 3가지**

1. **의존성 방향은 한쪽으로만**: `api → services → agents → toolkit`.
   역방향 import가 생기면 설계가 틀린 것입니다.
2. **전역 싱글턴을 FastAPI `Depends`로 교체**. 테스트가 `app.dependency_overrides`를 쓰게 되어
   `monkeypatch.setattr(main_module, ...)`이 사라집니다.
3. **`agents/`는 FastAPI를 import하지 않습니다.** 지금도 그런데, 앞으로도 유지하세요.
   `HTTPException`을 에이전트로 끌어들이지 마세요.

### 프론트엔드

```text
frontend/src/
  lib/
    api/                    # ✅ 완료
      client.js             #   fetch 래퍼 + extractDetail (에러 파싱 단일 지점)
      problems.js wordbooks.js generation.js stream.js index.js
    problem/                # problemUtils.js 를 역할별로 분리
      markers.js  summary.js  insertion.js  labels.js
  components/
    common/                 # Panel / ErrorBox / EmptyBox / SkeletonList / UseBar (미착수)
    wordbook/
      WordCard.svelte       # ✅ Creator·Library 공용
    exam/                   # ✅ 완료
      ProblemSheet.svelte   #   문제 출제 (548줄)
      VocabSheet.svelte     #   단어 암기지 (277줄)
    ...
  styles/                   # ✅ 완료 — 18개 파일, 최대 378줄
    index.css               #   @import 순서 = 우선순위. 바꾸면 화면이 깨집니다
    tokens.css layout.css forms.css feedback.css problem.css library.css
    exam-builder.css exam-paper.css animations.css home.css wordbook.css
    synonym-swap.css library-hub.css streaming.css wordbook-list.css
    vocab-sheet.css responsive.css print.css
```

**핵심 원칙 2가지**

1. **컴포넌트는 `fetch`를 직접 부르지 않습니다.** `lib/api/`만 부릅니다.
2. **`app.css` 2,421줄을 역할별로 쪼갭니다.** 특히 `print.css`는 분리 필수 —
   인쇄 스타일이 화면 스타일에 묻혀 있어 수정이 위험합니다.

---

## 4. 단계별 실행 순서

위험도가 낮은 것부터입니다. **각 단계 끝에 검증을 돌리고 커밋하세요.**

| # | 작업 | 위험 | 검증 포인트 |
|---|---|---|---|
| ~~1~~ | ~~`analysis_json` 슬림화~~ | — | **완료 (2026-09-23)** — 412→179tok, 폴백 12종 동일 |
| ~~2~~ | ~~프론트 `lib/api/` 추출~~ | — | **완료 (2026-09-23)** — 컴포넌트 fetch 0건 |
| ~~3~~ | ~~`WordCard.svelte` 공용화~~ | — | **완료 (2026-09-23)** — 마크업 복제 제거 |
| ~~4~~ | ~~`app.css` → `styles/*` 분리~~ | — | **완료 (2026-09-23)** — 빌드 CSS 바이트 동일 |
| ~~5~~ | ~~`main.py` → `apis/*` 분리~~ | — | **완료 (2026-09-23)** |
| 6 | 전역 싱글턴 → `Depends` | **높음** | 테스트의 monkeypatch 전부 수정 필요 |
| ~~7~~ | ~~`MockExamBuilder` 분리~~ | — | **완료 (2026-09-23)** — 한글 문구 112개·CSS 클래스 전부 동일 |
| ~~8~~ | ~~`llm/clients/` 분리~~ | — | **완료 (2026-09-23)** — provider 3종 분기·실호출 확인 |
| ~~9~~ | ~~재시도 상한 도입~~ | — | **완료 (2026-09-23)** — blank 12→6회, 11개 유형 전부 정상 |

### 5단계(라우터 분리) 안전 수칙

라우트 경로가 하나라도 바뀌면 프론트가 깨집니다. 분리 전후로 비교하세요.

```bash
uv run python -c "
from backend.main import app
print(sorted((r.path, tuple(sorted(r.methods))) for r in app.routes if hasattr(r,'methods')))
" > /tmp/routes_before.txt
# 분리 후 같은 명령 → /tmp/routes_after.txt
diff /tmp/routes_before.txt /tmp/routes_after.txt && echo "라우트 동일 ✅"
```

`tests/test_project_consistency.py::test_every_api_route_is_documented`가
이미 라우트-문서 일치를 지키고 있으니, 그것도 함께 통과해야 합니다.

### 6단계(DI) 주의

지금 테스트들이 이렇게 `apis/deps.py` 의 전역을 갈아끼웁니다.

```python
monkeypatch.setattr(deps, "problem_store", problem_store)
monkeypatch.setattr(deps, "wordbook_store", wordbook_store)
monkeypatch.setattr(deps, "synonym_swapper", swapper)
monkeypatch.setattr(deps.settings, "enable_problem_persistence", True)
```

대상 파일: `test_save_and_stream.py`, `test_synonym_swap.py`,
`test_usage_logging.py`, `test_endpoints_smoke.py`

`Depends`로 바꾸면 전부 `app.dependency_overrides[...]`로 교체해야 합니다.
**이 단계만 별도 커밋으로 분리**하세요. 다른 변경과 섞으면 되돌리기 어렵습니다.

---

## 5. 건드리지 말 것

리팩토링 중 "정리"하고 싶어지지만, 이유가 있어서 그 모양인 것들입니다.

- **`contextvars.copy_context()`** (`agents/base.agenerate`, `apis/deps.run_sync`, `apis/streaming._stream_agent`)
  `run_in_executor`는 context를 자동 전파하지 않습니다. 빼면 사용량 로그와 진행 상황이
  **조용히** 사라집니다. 회귀 테스트: `test_usage_survives_the_thread_executor`
- **`apis/streaming._stream_agent` 의 전처리** — 스트리밍 경로가 `deps.run_agent` 를 우회하므로 동의어 교체를
  **양쪽 모두**에 넣어야 합니다. 한때 이게 빠져서 UI에서 기능이 통째로 무시됐습니다.
  회귀 테스트: `test_streaming_path_applies_synonym_swap`, `test_both_paths_behave_the_same`
- **`normalize_text`의 단일 줄바꿈 → 공백 치환** — PDF 지문의 하드랩을 안 없애면
  LLM 스팬 매칭이 실패해 생성이 통째로 폴백으로 떨어집니다.
- **`ThreadPoolExecutor(max_workers=1)`을 기본 executor로 바꾸지 마세요.**
  주석대로 일부 환경에서 루프 종료가 멈춥니다.
- **로컬 폴백 경로 전체** — 길고 안 예뻐 보이지만 LLM 장애 시 유일한 방어선입니다.
  줄이려면 삭제가 아니라 공통화하세요.

---

## 6. 완료 기준

- [x] `main.py` 100줄 이하 → **25줄** ✅
- [x] `app.css` 파일당 400줄 이하로 분리 → **최대 378줄** ✅
- [x] `MockExamBuilder.svelte` → **30줄 껍데기** ✅ (자식은 548/277줄)
- [x] 컴포넌트에서 `fetch(` 직접 호출 **0건** ✅
- [x] `apis/` 밖에서 `from fastapi` import 0건 → **`main.py` 의 `FastAPI` 하나만** (앱 생성에 필수) ✅
- [x] 생성 1회 입력 토큰 **1,930 → 1,697** ✅
- [x] `uv run pytest` **168개** 통과 ✅
- [ ] 폴백 스냅샷 `diff` 무변화

검증 커맨드:

```bash
wc -l backend/main.py frontend/src/components/MockExamBuilder.svelte
wc -l frontend/src/styles/*.css | sort -rn | head -3          # 400줄 이하인가
grep -rn "fetch(" frontend/src/components/ frontend/src/App.svelte           # 0건이어야 함
grep -rln "from fastapi" backend/ | grep -vE "backend/apis/|backend/main.py"  # 0건이어야 함
find backend/llm/clients frontend/src/components/exam -type f | wc -l         # 분리 확인
uv run pytest -q                                                              # 170 passed
```
