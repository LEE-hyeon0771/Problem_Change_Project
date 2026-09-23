# CLAUDE_frontend.md — 프론트엔드 개발 가이드

`Problem_Change_Project` 프론트엔드(Svelte 4 + Vite 5)의 구조와 동작 원리입니다.
루트 `CLAUDE.md`가 상위 진입점이고, 이 문서가 프론트엔드 상세를 담당합니다.
백엔드는 `docs/CLAUDE_backend.md`를 보세요.

**문서와 코드가 충돌하면 코드가 맞습니다.** 그때는 이 문서를 고치세요.

---

## 1. 레이어 구조

```text
App.svelte           화면 전환 + 저장소 목록 로딩(단일 소유자)
  ↓ props
components/          기능 단위 컴포넌트
  ↓
lib/api/             모든 HTTP 호출의 단일 통로
lib/problemUtils.js  표시·파싱 공통 유틸
  ↓
styles/              index.css 가 @import 순서로 우선순위 결정
```

### 디렉터리

```text
frontend/src/
  main.js
  App.svelte                 홈 + 탭 + 개인DB 하위 구분 라우팅
  components/
    HomeLanding.svelte       첫 화면 진입 버튼 3개
    ProblemCreator.svelte    문제변형 (스트리밍 + 동의어 되돌리기 + "사용")
    WordbookCreator.svelte   핵심단어장 (스트리밍 + 검색/필터 + "사용")
    LibraryHub.svelte        개인DB 허브 버튼 2개
    ProblemLibrary.svelte    개인DB > 변형문제
    WordbookLibrary.svelte   개인DB > 단어장 (아코디언)
    wordbook/
      WordCard.svelte        단어 카드 (생성·개인DB 공용, detailed prop)
    MockExamBuilder.svelte   모드 전환 껍데기(30줄)
    exam/
      ProblemSheet.svelte    문제 출제
      VocabSheet.svelte      단어 암기지
    ProblemView.svelte       공통 문제 렌더링
  lib/
    problemUtils.js          표식/요약/삽입 파싱, 라벨, 날짜, 미리보기
    api/
      client.js              fetch 래퍼 + 에러 파싱
      stream.js              SSE 파서
      problems.js            변형문항 API
      wordbooks.js           단어장 API
      generation.js          스트리밍 생성 API
      index.js               컴포넌트가 import 하는 진입점
  styles/                    index.css + 역할별 18개
```

---

## 2. 화면 전환

파일: `frontend/src/App.svelte`

상태 두 개로 전체 화면을 결정합니다.

| 상태 | 값 |
|---|---|
| `activePage` | `home` / `create` / `wordbook` / `library` / `exam` |
| `librarySection` | `''`(허브) / `problems` / `wordbooks` |

```text
home ─┬─ 문제변형   → create
      ├─ 핵심단어장 → wordbook
      └─ 개인DB     → library ─┬─ (허브) ─┬─ 변형문제 → librarySection='problems'
                                │          └─ 단어장   → librarySection='wordbooks'
                                └─ 하위 탭으로 둘 사이 이동
exam ─ examMode ─┬─ problem → ProblemSheet
                 └─ vocab   → VocabSheet
```

- 첫 진입은 `home` 이며, 홈에서는 탭 바를 숨기고 진입 버튼 3개만 보여 줍니다.
- 홈을 벗어나면 상단 탭으로 네 화면과 홈을 자유롭게 오갑니다.
- 개인DB 는 홈과 같은 패턴으로 한 번 더 갈라집니다(허브 → 하위 탭).
- `navigate(page, section)` 이 전환과 스크롤 초기화를 함께 처리합니다.

**탭을 늘릴 때는 `tabs` 배열과 `headings` 객체를 함께 갱신하세요.**
둘이 어긋나면 `heading` 이 `undefined` 가 되어 헤더가 비어 렌더링됩니다.

### 저장소 목록의 소유자는 App.svelte 하나입니다

`savedProblems` / `savedWordbooks` 를 `App.svelte` 가 `onMount` 에서 한 번 불러오고
자식에게 props 로 내려 줍니다. 자식이 저장에 성공하면 `onSaved` 콜백으로 알리고,
`App.svelte` 가 `{ silent: true }` 로 조용히 다시 불러옵니다(로딩 스피너 없이).

목록을 자식에서 따로 fetch 하지 마세요. 탭마다 카운트가 어긋납니다.

---

## 3. API 계층 — 컴포넌트에 `fetch` 가 없어야 합니다

컴포넌트는 `lib/api/index.js` 에서만 가져다 씁니다.
엔드포인트 경로를 아는 곳은 `lib/api/` 안뿐입니다.

```javascript
import { saveProblem, streamProblem } from '../lib/api/index.js';
```

| 파일 | 내보내는 것 |
|---|---|
| `client.js` | `requestJson` `getJson` `postJson` `deleteResource` `getList` `extractDetail` |
| `problems.js` | `listProblems` `saveProblem` |
| `wordbooks.js` | `listWordbooks` `saveWordbook` `deleteWordbook` |
| `generation.js` | `streamProblem` `streamWordbook` |
| `stream.js` | `streamJson` (generation.js 가 감쌉니다) |

### client.js 가 흡수하는 것

- **에러 파싱** — 백엔드는 `{"detail": ...}` 를 주지만 프록시 오류 등은 평문입니다.
  `extractDetail` 이 둘 다 읽을 수 있는 메시지로 바꿉니다.
  컴포넌트에서 `fetch` 를 직접 부르면 이 코드가 파일마다 복제되고,
  백엔드 에러 형식이 바뀔 때 전부 찾아 고쳐야 합니다.
- **204 처리** — 본문이 없으면 `null` 을 돌려줍니다.
- **삭제 멱등성** — `deleteResource` 는 404 를 실패로 보지 않습니다.
  이미 지워진 것을 다시 지우는 건 사용자 입장에서 성공입니다.
- **목록 형식 검증** — `getList` 는 배열이 아니면 throw 합니다.
  이게 없으면 형식이 깨졌을 때 화면이 조용히 비어 원인을 못 찾습니다.

---

## 4. 스트리밍 (SSE)

생성은 **항상 스트리밍 경로**를 씁니다. 비스트리밍 엔드포인트는 Swagger 용입니다.

| 함수 | 엔드포인트 |
|---|---|
| `streamProblem(prefix, type, payload, handlers)` | `POST /api/v1/stream/{type}` |
| `streamWordbook(prefix, payload, handlers)` | `POST /api/v1/stream-wordbook` |

```javascript
result = await streamProblem(apiPrefix, selectedType, payload, {
  onStatus: (event) => { progressMessage = event.message; },
  onPartial: (data) => { partialEntries = data.entries; }   // 단어장만
});
```

### 구현 주의점 (`lib/api/stream.js`)

- **`EventSource` 를 쓸 수 없습니다.** GET 만 지원하는데 우리는 POST 본문에 지문을 실어 보냅니다.
  그래서 `fetch` + `ReadableStream` 으로 직접 파싱합니다.
- SSE 프레임은 빈 줄(`\n\n`)로 구분됩니다. 청크 경계에서 잘린 마지막 조각은
  버퍼에 남겨 다음 청크와 이어 붙입니다. `split` 결과를 전부 처리하면 프레임이 깨집니다.
- **`error` 이벤트를 반드시 처리해야 합니다.** 검증 오류(422)는 스트림이 열린 뒤에 오므로
  HTTP 상태는 이미 200 입니다. `response.ok` 만 보면 실패를 놓칩니다.
- `done` 이벤트 없이 스트림이 끝나면 에러로 처리합니다. 조용히 빈 화면이 되는 것보다 낫습니다.
- `reader.releaseLock()` 은 `finally` 에서 합니다.

---

## 5. 문제변형 화면

파일: `frontend/src/components/ProblemCreator.svelte`

- 영어 지문 입력 (`샘플 넣기` 버튼 제공)
- 11개 유형 선택, 난이도(easy/mid/hard), 해설 포함 여부, seed, debug
- 생성 중 진행 상황 표시
- 결과 확인 후 **"사용"** 을 눌러야 `POST /api/v1/problems` 로 저장

`usedPayload` 에 생성에 쓴 요청 원본을 보관합니다. 저장 엔드포인트가
`{request, result}` 를 함께 요구하기 때문입니다.

### 동의어 교체 되돌리기

```javascript
const SWAP_TYPES = new Set(['title', 'topic', 'summary', 'blank', 'implicit']);
$: swapSupported = SWAP_TYPES.has(selectedType);
```

지원하지 않는 유형을 고르면 체크박스가 자동으로 비활성화되고,
`buildPayload()` 가 `synonym_swap: swapSupported && form.synonym_swap` 으로
한 번 더 막습니다. 이 목록은 백엔드 `synonym_swapper.SUPPORTED_TYPES` 와 같아야 합니다.

되돌리기는 `revertedSwaps`(Set)에 담고 `applyReverts` 가 반영합니다.

```javascript
$: displayedProblem = applyReverts(result, revertedSwaps);
```

- **지문·선지·정답·해설을 한꺼번에** 되돌립니다. 지문만 되돌리면 문항 내부 정합성이 깨집니다.
- 전역 문자열 치환으로 처리합니다. 서버가 **"지문에 한 번만 등장하는 단어"만 교체**하기
  때문에 이 단순한 구현이 안전합니다. 서버의 그 규칙을 풀면 여기가 먼저 깨집니다.
- `result` 는 원본 그대로 두고 화면에만 반영합니다. 되돌리기를 해제하면 바로 복구됩니다.
- **"사용" 저장 시에는 화면에 보이는(되돌림이 반영된) 버전**이 저장됩니다.

---

## 6. 핵심단어장 화면

파일: `frontend/src/components/WordbookCreator.svelte`

- 지문 입력 → `streamWordbook` 호출
- **1차 결과를 먼저 보여 줍니다.** `onPartial` 로 받은 `partialEntries` 를 뿌리고,
  `done` 이 오면 `result.entries` 로 교체합니다.

```javascript
$: entries = result?.entries || partialEntries;
```

- 옵션: 숙어 포함 여부, 뜻당 동의어/반의어 개수(1~8). **난이도 옵션은 없습니다.**
- 단어/뜻/영어정의/동의어/반의어를 한 문자열로 합쳐 검색합니다.
- `핵심어만 보기` 필터(`importance === 'core'`)
- `meta.notice`(LLM 비활성)와 `meta.uncovered_candidates`(미정리 단어)를 배너로 노출합니다.
  **조용히 숨기지 마세요.** 결과가 반쪽이라는 사실이 사용자에게 보여야 합니다.
- 저장 시 제목을 지정할 수 있습니다.

### WordCard.svelte

생성 화면과 개인DB가 **같은 컴포넌트**를 씁니다. `detailed` prop 으로 밀도만 다릅니다.

| 위치 | `detailed` | 보여 주는 것 |
|---|---|---|
| `WordbookCreator` | `true` | 표제어, 지문 내 형태, 핵심/보조, CEFR, 지문에서의 뜻, 지문 예문, 뜻별 전체 |
| `WordbookLibrary` | `false` | 축약형 |

뜻마다 품사 뱃지 + 한국어 뜻 + 영어 정의 + **그 뜻에 맞는** 동의어/반의어 칩을 붙입니다.
한 단어가 명사와 동사로 모두 쓰이면 품사별로 뜻이 따로 나옵니다.

---

## 7. 개인DB

허브: `frontend/src/components/LibraryHub.svelte` (버튼 2개)

### 변형문제 — `ProblemLibrary.svelte`

- 유형 필터, 검색
- 카드 클릭 시 모달로 크게 보기 (`ProblemView.svelte` 재사용)

### 단어장 — `WordbookLibrary.svelte`

**아코디언 구조입니다.** 기본은 모두 접힌 상태로 제목 + 지문 미리보기만 보이고,
펼치면 정리된 단어가 나옵니다. 단어장 하나가 수십 단어라 접지 않으면 목록이 못 쓰게 됩니다.

`모두 펼치기` / `모두 접기` 제공, 검색, 삭제.

```javascript
// Svelte 는 Set 의 내부 변경을 감지하지 못합니다. 반드시 새 Set 으로 교체하세요.
function toggle(uid) {
  const next = new Set(expanded);
  next.has(uid) ? next.delete(uid) : next.add(uid);
  expanded = next;     // ← 이 재할당이 반응성을 일으킵니다
}
```

`expanded.add(uid)` 만 하면 화면이 갱신되지 않습니다. 같은 함정이
`ProblemSheet` 의 선택 상태에도 적용됩니다.

---

## 8. 모의고사 출제

`MockExamBuilder.svelte` 는 `examMode` 로 두 컴포넌트를 갈라 주는 30줄짜리 껍데기입니다.
출제 로직을 여기에 다시 몰아넣지 마세요.

### 문제 출제 — `exam/ProblemSheet.svelte`

- 개인DB에 저장된 문제만 사용
- 시험지 제목, 문항 수, 포함할 유형 선택
- 한국 모의고사 스타일 **2단 문제지** 레이아웃
- 왼쪽 `교체 후보 문제` 목록 — 클릭 선택 또는 **드래그앤드롭**으로 특정 문항 교체
  - `getExamUsedIds` 로 이미 쓴 문항을 후보에서 제외해 중복 출제를 막습니다
  - `canApplyReplacement` 가 교체 가능 여부를 먼저 판정합니다
- 정답표 표시 / 해설지 표시 옵션
- 브라우저 인쇄 / PDF 저장

### 단어 암기 — `exam/VocabSheet.svelte`

- 여러 단어장을 골라 합칠 수 있고, **표제어 기준으로 중복을 제거**합니다
  (`headword` 를 소문자 trim 한 값이 키)
- `vocabSheetMode`
  - `study` — 뜻이 보이는 암기장
  - `quiz` — 뜻이 빈칸인 시험지. **정답지가 별지로 함께 출력**됩니다
- 1~3단 조절, 동의어·반의어 표시 토글, 핵심어만 필터
- 인쇄 시 `.vocab-blank` 는 실선으로 바뀝니다. 화면용 점선은 인쇄하면 잘 안 보입니다.

---

## 9. 공통 렌더링 — 원문 표식 파싱

파일: `frontend/src/components/ProblemView.svelte` + `lib/problemUtils.js`

백엔드는 원문을 재작성하지 않고 **표식**만 남깁니다. 프론트가 이를 파싱해
밑줄·번호 형태로 렌더링합니다.

| 유형 | 백엔드가 주는 형태 | 프론트 처리 |
|---|---|---|
| `blank` | 원문에서 정답 span 만 `_____` | 그대로 표시 |
| `implicit` | `[[1]]...[[/1]]` | 밑줄 + 번호 (`isImplicitType`) |
| `vocab` `grammar` `reference` | 원문 내 표식 | 밑줄 + ①~⑤ (`buildPassageSegments`) |
| `insertion` | 주어진 문장 + ①~⑤ 슬롯 | `getInsertionGivenSentence` / `getInsertionBody` |
| `summary` | (A)(B) 빈칸 | `getSummaryBody` / `parseSummaryChoice` |

주요 유틸:

| 함수 | 역할 |
|---|---|
| `buildPassageSegments(type, passage, choices)` | 표식을 세그먼트로 쪼개 렌더링 가능한 형태로 |
| `toMarkerIndex` / `toMarkerDisplay` | 표식 번호 ↔ ①~⑤ 변환 |
| `usesEmbeddedChoices(type)` | 선지가 지문 안에 박혀 있는 유형인지 |
| `typeLabel` `formatDate` `previewText` `normalizePrefix` | 표시 공통 |

**표식 파싱 로직을 컴포넌트에 흩지 마세요.** `problemUtils.js` 또는
`ProblemView.svelte` 에 모읍니다. 생성 화면과 개인DB 모달이 같은 코드를 써야
한쪽만 깨지는 일이 없습니다.

---

## 10. 스타일

`frontend/src/styles/` = `index.css` + 역할별 18개.

```css
/* index.css — @import 순서가 곧 우선순위입니다 */
@import "./tokens.css";      /* 색·간격 변수 */
@import "./layout.css";
@import "./forms.css";
... 중략 ...
@import "./responsive.css";  /* 반드시 */
@import "./print.css";       /* 마지막 두 개 */
```

**순서를 바꾸면 화면이 깨집니다.** CSS 는 나중에 선언된 규칙이 이기므로,
`responsive.css` 와 `print.css` 는 반드시 마지막에 와야 합니다.
새 파일은 성격이 맞는 위치에 끼워 넣되 이 둘보다 앞에 두세요.

이 구조는 예전 단일 파일(2,421줄)을 **연속 구간 단위로** 잘라 만든 것이라
분할 전후 빌드 결과가 바이트 단위로 같았습니다. 규칙을 재배치하지 마세요.

회귀 테스트: `tests/test_styles_structure.py`

---

## 11. 실행과 빌드

```bash
./dev.sh            # 백엔드 + 프론트 동시 기동 (권장)
cd frontend && npm run dev
cd frontend && npm run build
```

- 기본 포트: 프론트 `5174`, 백엔드 `8100` (`FRONTEND_PORT` / `BACKEND_PORT`)
- `5173` 은 다른 프로젝트가 `--strictPort` 로 잡고 있어 피했습니다.
- Vite proxy 가 `/api` 를 백엔드로 넘깁니다. `vite.config.js` 가 `BACKEND_PORT` 를 따라갑니다.
- WSL + Windows 혼합 실행 시 `vite.config.js` 가 Windows host IP 를 자동 감지합니다.
- 강제 지정: `VITE_PROXY_TARGET=http://127.0.0.1:8100 npm run dev`

---

## 12. 작업 시 주의사항

- **`App.svelte` 에 기능을 다시 몰아넣지 마세요.** `components/` 아래 기능 단위로 확장합니다.
- **컴포넌트에서 `fetch` 를 직접 부르지 마세요.** `lib/api/` 를 통합니다.
- **공통 표시/파싱 로직은 `problemUtils.js` 또는 `ProblemView.svelte` 에 모으세요.**
- **`Set` / `Map` 상태는 새 객체로 교체**해야 Svelte 가 감지합니다.
- 이 프로젝트는 **Svelte 4** 입니다. `export let` / `$:` 문법을 씁니다.
  `$state` / `$props` 같은 Svelte 5 runes 는 쓰지 않습니다.
- 백엔드 계약을 바꾸면 **양쪽을 함께** 고치세요. 특히 동의어 교체 지원 유형 목록은
  `ProblemCreator.SWAP_TYPES` 와 `synonym_swapper.SUPPORTED_TYPES` 두 군데에 있습니다.

### 빌드 경고를 흘려보내지 마세요

`npm run build` 는 **컴포넌트를 import 없이 써도 경고만 내고 통과합니다.**
런타임에 가서야 화면이 죽기 때문에 빌드 로그를 안 읽으면 그대로 배포됩니다.
실제로 `WordCard` 를 별도 파일로 뽑을 때 두 소비자 모두에서 import 가 빠진 적이 있습니다.

`tests/test_frontend_components.py` 가 이제 이것을 잡습니다.
컴포넌트를 추출하거나 파일을 옮긴 뒤에는 `uv run pytest tests/test_frontend_components.py` 를 돌리세요.
