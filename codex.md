# codex.md — FastAPI 기반 “영어 지문 → 유형별 문제 변형” 서비스 스펙 (10 Agents / 10 APIs, 고급 설계 포함)

이 문서는 **CODEX(바이브 코딩)** 가 그대로 보고 구현할 수 있도록 만든 “구현 지시서 + 스캐폴딩 설계 + 프롬프트/스키마 + 품질(고급) 전략” 문서다.  
목표는 **완전한 서비스화**가 아니라, **FastAPI 레벨에서 입력 영어 지문을 10개 유형 중 하나로 변형하여 문제 JSON을 반환**하는 것.

> 핵심 원칙: “문제 생성”은 쉽지만, **학평 스타일의 ‘그럴듯한 오답’ + ‘정답 유일성’**을 보장하는 게 어렵다.  
> 따라서 본 문서는 각 유형별로 **생성 전략 + 오답 생성 규칙 + 검증/재생성 조건**까지 포함한다.

---

## 0) 핵심 요구사항 요약

- **Model**: `gemini-3-flash-preview`
- **Backend**: `FastAPI`
- **유형별 Agent 10개** + **유형별 API 10개**
- 입력: 영어 지문 1개 (`passage`)
- 출력: 해당 유형 문제 JSON (지문/문항/선지/정답/해설)
- 스타일 목표: **교육청 학력평가(고2) 스타일**(문항 지시문/선지 형식/정답 1개)

---

## 1) 10개 유형 정의 (route ↔ agent 매핑)

| # | 유형(한글) | route | agent 클래스 |
|---|---|---|---|
| 1 | 제목 | `POST /api/v1/title` | `TitleAgent` |
| 2 | 장문(세트형) | `POST /api/v1/long` | `LongAgent` |
| 3 | 요약문 | `POST /api/v1/summary` | `SummaryAgent` |
| 4 | 삽입 | `POST /api/v1/insertion` | `InsertionAgent` |
| 5 | 순서 | `POST /api/v1/order` | `OrderAgent` |
| 6 | 무관 | `POST /api/v1/irrelevant` | `IrrelevantAgent` |
| 7 | 빈칸 | `POST /api/v1/blank` | `BlankAgent` |
| 8 | 지칭 | `POST /api/v1/reference` | `ReferenceAgent` |
| 9 | 어휘 | `POST /api/v1/vocab` | `VocabAgent` |
| 10 | 어법 | `POST /api/v1/grammar` | `GrammarAgent` |

> 구현 포인트: **route 당 agent 1개**를 유지하되, `LongAgent`는 내부적으로 다른 agent를 “조합”할 수 있다(세트형이므로).

---

## 2) 최상위 아키텍처 (고급 설계 포함)

### 2.1 공통 처리 흐름(모든 agent 공통)

1) **입력 정규화**  
- 공백/줄바꿈 정리, 비영문 제거는 하지 않되 과도한 공백은 축약  
- 너무 짧은 지문 reject (예: 60단어 미만이면 422)

2) **구조 분석(analysis pass)**  
- 문단/문장 분할
- 담화 표지어(대조/인과/예시/추가) 위치 탐지
- 핵심 주장(thesis) 후보 탐지(1~2개)
- 주요 개체/대명사 후보(he/they/this/that 등) 탐지

3) **유형 변형(generation pass)**  
- 유형별 전략으로 문제를 생성(LLM 1회 권장)
- 오답 생성 규칙을 반드시 준수

4) **정답 유일성 검증(validation pass)**  
- 로컬 validator로 스키마/형식 검증  
- **Self-check(옵션)**: “정답이 유일한지” LLM에게 재검증 → 실패 시 1회 재생성

5) **최종 반환**  
- `ProblemResponse` 또는 `ProblemSetResponse`

---

### 2.2 “고급 품질”을 위한 3-패스 구조(권장)

- **Pass A: Analysis JSON** (짧게)  
  - 지문을 유형 공통 분석 JSON으로 요약해 downstream 안정화
- **Pass B: Generation JSON**  
  - 실제 문제 JSON 생성
- **Pass C: Self-check JSON** *(ENABLE_SELF_CHECK=true 일 때만)*  
  - “정답 유일성”과 “오답 그럴듯함” 점검  
  - 실패 시 1회 재생성(temperature↓)

> MVP는 Pass B만으로도 가능하나, 실제 품질은 Pass C가 크게 끌어올린다.

---

## 3) 프로젝트 파일 트리(권장)

```
app/
  main.py
  core/
    config.py
    logging.py
    errors.py
  llm/
    client.py
    json.py
    schema.py
  schemas/
    base.py
    analysis.py
    title.py
    long.py
    summary.py
    insertion.py
    order.py
    irrelevant.py
    blank.py
    reference.py
    vocab.py
    grammar.py
  agents/
    base.py
    title_agent.py
    long_agent.py
    summary_agent.py
    insertion_agent.py
    order_agent.py
    irrelevant_agent.py
    blank_agent.py
    reference_agent.py
    vocab_agent.py
    grammar_agent.py
  prompts/
    base_system.md
    analysis.md
    title.md
    long.md
    summary.md
    insertion.md
    order.md
    irrelevant.md
    blank.md
    reference.md
    vocab.md
    grammar.md
    self_check.md
  toolkit/
    text.py
    discourse.py
    labels.py
    render.py
    validators.py
    difficulty.py
tests/
  test_health.py
  test_endpoints_smoke.py
  fixtures.py
pyproject.toml
README.md
```

---

## 4) 환경설정(.env / ENV)

`app/core/config.py`에서 pydantic-settings로 로딩.

필수:
- `GOOGLE_API_KEY=...`
- `GEMINI_MODEL=gemini-3-flash-preview`

선택:
- `APP_ENV=dev|prod|test`
- `LOG_LEVEL=INFO`
- `DEFAULT_TEMPERATURE=0.6`
- `DEFAULT_MAX_OUTPUT_TOKENS=20000`
- `ENABLE_SELF_CHECK=true|false`
- `SELF_CHECK_MAX_RETRY=1`

---

## 5) 공통 Request/Response 스키마 (Pydantic)

### 5.1 공통 Request (`GenerateRequest`)
필드 권장:
- `passage: str` (영어 지문 원문)
- `difficulty: Literal["easy","mid","hard"] = "mid"`
- `choices: int = 5` (항상 5 유지)
- `seed: int | None = None` (재현성 옵션; 완전 결정적이진 않지만 prompt에 포함)
- `style: Literal["edu_office"] = "edu_office"` (학평 스타일)
- `explain: bool = True` (해설 포함 여부)
- `return_korean_stem: bool = True` (문항 지시문 한국어)
- `debug: bool = False` (True면 meta.debug에 analysis 일부 포함)

### 5.2 공통 Choice 모델
```json
{ "label": "①", "text": "..." }
```

### 5.3 공통 Response (`ProblemResponse`)
최소 공통 형태:
```json
{
  "type": "blank",
  "passage": "....",               // 문제에 쓰일 지문(가공된 버전)
  "question": "....",              // 지시문/질문
  "choices": [{"label":"①","text":"..."}, ...],
  "answer": {"label":"③","text":"..."},
  "explanation": "....",
  "meta": { "difficulty":"mid", "seed": 123 }
}
```

### 5.4 장문 Response (`ProblemSetResponse`)
```json
{
  "type": "long",
  "passage": "원문 지문",
  "items": [ {ProblemResponse}, {ProblemResponse}, {ProblemResponse} ],
  "meta": { "set_type": "title_vocab", "difficulty":"mid" }
}
```

### 5.5 Analysis JSON (`PassageAnalysis`) — 고급 품질을 위한 공통 분석 스키마(권장)
(필수는 아니지만, CODEX 구현 시 품질이 안정됨)
```json
{
  "topic": "one short phrase",
  "thesis_candidates": ["...", "..."],
  "keywords": ["...", "...", "..."],
  "paragraphs": [
    {
      "sentences": ["...", "..."],
      "function": "claim|example|contrast|conclusion|definition|expansion",
      "markers": ["however", "therefore"]
    }
  ],
  "coreference_candidates": [
    {"mention": "they", "sentence_index": 3, "likely_antecedent": "..." }
  ]
}
```

---

## 6) LLM Client 설계 (Gemini 래퍼)

### 6.1 요구사항
- 출력은 **반드시 JSON**(스키마 적합)
- JSON 파싱 실패 시:
  1) `extract_first_json_object()`로 복구
  2) 그래도 실패하면 1회 재호출(temperature 낮춤)

### 6.2 인터페이스 예시
- `LLMClient.generate_json(prompt: str, schema: dict | None = None) -> dict`
- `LLMClient.generate_text(prompt: str) -> str` (디버깅용)

### 6.3 구현 메모
- 가능하면 “JSON schema 기반 구조화 출력”을 사용한다(지원 여부/SDK 방식은 구현 환경에 따라 다를 수 있음).
- 지원이 불명확하면: “출력은 JSON만” 규칙 + 후처리 파서로 충분.

---

## 7) 공통 Toolkit (텍스트/담화/렌더링/검증/난이도)

### 7.1 `toolkit/text.py`
- `normalize_text(text) -> str`
- `word_count(text) -> int`
- `split_paragraphs(text) -> list[str]`
- `split_sentences(text) -> list[str]` (rule-based로 시작)
- `truncate_if_too_long(text, max_chars=2500)`

### 7.2 `toolkit/discourse.py`
- 담화 표지어 리스트:
  - contrast: `however, but, yet, nevertheless, on the contrary`
  - cause/effect: `therefore, thus, as a result, consequently`
  - example: `for example, for instance, such as`
  - addition: `moreover, furthermore, in addition`
- 함수:
  - `find_markers(sentence) -> list[str]`
  - `tag_paragraph_function(paragraph) -> Literal["claim","example","contrast","conclusion","definition","expansion"]`
  - `score_insertion_fit(given_sentence, prev, next) -> float` *(MVP는 heuristic, v1은 LLM score)*

### 7.3 `toolkit/labels.py`
- `choice_labels(n=5) -> ["①","②","③","④","⑤"]`
- `slot_labels(n=5) -> ["①","②","③","④","⑤"]`
- `ref_labels(n=5) -> ["(a)","(b)","(c)","(d)","(e)"]`

### 7.4 `toolkit/render.py`
- `render_blank(passage, span) -> passage_with_blank` (blank는 `_____` 1회만)
- `render_insertion_slots(sentences, slot_indices) -> passage_with_①~⑤`
- `render_order_blocks(intro, blocksA,B,C) -> passage_parts`
- `render_underlines(passage, targets) -> passage_with_markers`
  - 밑줄 표현은 HTML/Markdown 혼합 대신, 안전한 마커 권장:
    - 예: `[[①]]word[[/①]]`

### 7.5 `toolkit/difficulty.py` (난이도 조절 룰)
- difficulty가 agent마다 다른 “레버”를 움직이게 한다.
  - blank: word → phrase → clause
  - insertion: 단서(연결어/지시어) 명확도 조절
  - order: 연결어 강도(명시적/암시적) 조절
  - vocab: 오답의 미묘함(반의어 vs 준동의어) 조절
  - grammar: 오류의 흔함/미묘함(수일치 vs 병렬/분사구문) 조절

### 7.6 `toolkit/validators.py`
- 공통 검증:
  - choices 5개인지
  - answer label이 choices 안에 있는지
  - passage/question 비어있지 않은지
- 유형별 검증(예시):
  - blank: `_____` 정확히 1회
  - insertion: answer_position 1..5
  - order: 보기 5개가 모두 서로 다른 배열인지
  - vocab/grammar: 밑줄 5개 표시가 존재하는지(또는 meta에 targets 5개)

---

## 8) “오답(선지) 생성” 공통 고급 규칙 라이브러리

모든 유형(특히 빈칸/요약/제목/어휘)에 적용 가능한 **오답 패턴**:

1) **Too Broad / Too Narrow**  
2) **Polarity Flip** (긍↔부정, 강화↔완화, 원인↔결과 뒤집기)  
3) **Same Domain, Wrong Mechanism** (주제는 같은데 설명 축이 다름)  
4) **Near-Synonym Trap** (유사어지만 지문 맥락에서는 부적합)  
5) **Scope Shift** (개인↔사회, 단기↔장기, 일부↔전체)  
6) **Collocation Trap** (단어는 맞는데 결합이 어색)  
7) **Category Swap** (정답이 process인데 오답은 outcome 등)

> **중요:** 오답은 “완전히 다른 이야기”가 아니라 “비슷해 보이되 틀린” 것이어야 학평 스타일이 된다.

---

## 9) 유형별 Agent 전략(고급) + 프롬프트 요구사항

원칙: 각 agent는 내부적으로 다음을 가진다.

- `analyze(passage) -> PassageAnalysis | dict`
- `generate(passage, analysis) -> ProblemResponse | ProblemSetResponse`
- `validate(problem) -> ok | raise`
- `self_check(problem) -> ok | regenerate` *(옵션)*

재시도 정책:
- 로컬 validation 실패 → 즉시 1회 regenerate
- self-check 실패 → 1회 regenerate (temperature↓)

---

### 9.1 TitleAgent (제목)

**출력 형태**
- 지시문(한글): `다음 글의 제목으로 가장 적절한 것은?`
- 선지 5개(영문 제목), 정답 1개

**고급 전략**
- 정답 제목은 “topic + stance(주장/교훈)”를 포함하게 한다.
- 오답 4개는 아래 패턴을 반드시 섞는다:
  - too narrow
  - too broad
  - polarity flip
  - 소재는 맞는데 요지/주장과 무관

**검증**
- 정답이 지문 전체를 포괄하는지(부분 소재만이면 실패)
- 오답이 너무 노골적(전혀 무관)인 경우 실패

---

### 9.2 LongAgent (장문 세트형)

**출력 형태**
- `items`에 2~3문항.
- MVP 세트 템플릿(우선 구현):
  1) `title + vocab`
  2) `order + reference`
  3) `title + blank`

**고급 전략**
- 세트형은 “한 지문으로 여러 능력 평가”가 목적이므로,
  - 각 문항이 서로 다른 포인트를 타게 한다(중복 금지).
- `set_type`를 meta에 기록.

**검증**
- items 길이 2~3
- 각 item.type이 set_type의 기대 조합과 일치

---

### 9.3 SummaryAgent (요약문) — (A)(B) 2블랭크 + “쌍 선택”

**출력 형태**
- 요약문 템플릿 1문장에 (A)(B) 두 빈칸.
- 보기 5개는 (A,B) 쌍.

**고급 설계**
- A/B 역할을 고정:
  - (A) = 핵심 범주/대상/원인(대개 명사/명사구)
  - (B) = 결론/평가/효과(대개 형용/동사구)
- 오답쌍 4개 생성 규칙(최소 3개 이상 적용):
  1) A만 맞고 B 틀림
  2) B만 맞고 A 틀림
  3) 둘 다 범주 유사하지만 지문 축과 다름(메커니즘 이동)
  4) polarity flip (결론 방향 반전)

**검증**
- 요약문에서 (A)(B) 각각 1회만 등장
- 정답쌍이 가장 자연스럽고, 다른 쌍이 동률 수준이면 실패

---

### 9.4 InsertionAgent (삽입) — “주어진 문장” + ①~⑤ 위치

**출력 형태**
- given_sentence 1개
- 본문에 ①~⑤ 위치 표시
- 선택지 ①~⑤, 정답 위치 1개

**고급 설계(강력 권장: ‘발췌 기반’)**
- 입력 지문에서 **문장 1개를 ‘뽑아내어’ given_sentence로 사용**하는 방식이 품질이 가장 안정적.
  - 이유: 원래 있었던 자리(정답)가 명확하고, 문장/내용 일관성이 높다.
- given_sentence로 적합한 문장 조건:
  - 지시어/대명사(this/they/these/that) 포함
  - 연결어(however/therefore/for example) 포함
  - “예시/전환/결론” 기능이 뚜렷

**슬롯 구성**
- 남은 문장들 사이 경계에서 5개 슬롯을 만든다.
- 정답 슬롯은 “원래 위치”로 설정.
- 나머지 슬롯은 표면상 유사하지만 논리 연결이 깨지게 설계.

**검증**
- 정답 슬롯에 넣었을 때만 지시어 antecedent가 자연스럽다.
- 다른 슬롯에 넣으면 antecedent가 없거나 논리 표지어가 부자연.

---

### 9.5 OrderAgent (순서) — 주어진 글 + (A)(B)(C) 배열

**출력 형태**
- 주어진 글 1개 + (A)(B)(C) 3문단
- 보기 5개: 배열 조합(예: A-B-C)

**고급 설계**
- 문단 기능 태깅 기반으로 구성:
  - A: expansion/definition
  - B: example/evidence
  - C: conclusion/contrast
  (실제는 상황에 따라 변형하되 “역할 차이”를 두는 게 중요)
- 연결 단서:
  - 지시어(These/This/Such), 대명사, 반복 어휘
  - contrast marker는 앞에 “기대”를 만들어야 함
- 오답 4개는 “한 스왑만 바꾼” 근접 오답을 우선 포함(학평 스타일)

**검증**
- 정답 외에 2개 이상이 자연스럽다는 self-check가 뜨면 실패

---

### 9.6 IrrelevantAgent (무관) — ①~⑤ 중 흐름과 무관한 문장

**출력 형태**
- 문장 5개를 ①~⑤로 번호 부여
- “흐름과 무관한 문장” 1개 선택

**고급 설계**
- 4문장: 동일 topic vector + 동일 논리 축
- 1문장: 표면상 관련 있어 보이지만 “축 이탈”
  - 예: 같은 분야 단어를 쓰되 원인/결과 축이 다르거나, 결론과 무관한 배경설명으로 흐름을 끊음

**오답(무관문) 만들기 패턴**
1) Same domain, wrong axis (정책 ↔ 개인 경험)
2) Example mismatch (예시가 주제 범주 밖)
3) Time/Scope mismatch (역사/미래로 갑자기 이동)

**검증**
- 무관문이 너무 노골적으로 튀면 실패(주제 어휘 일부 공유시키기)

---

### 9.7 BlankAgent (빈칸) — 고급 설계 핵심(가장 중요)

**출력 형태**
- 지문 1곳을 `_____`로 비움
- 보기 5개(정답 1 + 오답 4)

**정답 형태는 3종 모두 가능**
- **Word**(단어): 주로 추상 명사/형용
- **Phrase**(구): 명사구/동사구/전치사구(2~7단어)
- **Clause**(절): 종속절/that절/조건절

> 권장 난이도 레버:
- easy: word 중심  
- mid: phrase 중심(가장 학평스럽고 안정적)  
- hard: clause 가능(단, self-check 필수)

---

#### 9.7.1 빈칸 후보 문장 선택(핵심)
“아무거나 뚫기” 금지. 다음 후보를 우선한다.

- thesis marker 포함 문장: therefore/thus/in short/overall
- contrast 이후 결론 문장: however/but/yet 다음 문장
- 문단 첫 문장(Topic sentence) 또는 문단 결론 문장
- 평가/규범/권고 문장: should/need to/important

---

#### 9.7.2 빈칸 스팬(span) 추출 규칙
- word: 핵심 개념(추상명사/핵심형용)을 하나
- phrase: 핵심 개념을 담는 짧은 구(2~7단어)
- clause: 핵심 결론이 담긴 종속절(단, 지나치게 길면 실패)

**스팬 제약**
- 빈칸은 지문에 **정확히 1회**만
- 정답 스팬이 지문 다른 곳에 그대로 반복되면 실패(정답 노출)

---

#### 9.7.3 오답(선지) 4개 생성 규칙(학평 스타일)
오답은 반드시 아래 중 3개 이상을 섞어 구성한다.

1) **Polarity Flip**  
   - 결론 방향 반전(benefit ↔ harm, increase ↔ decrease)
2) **Same Domain, Wrong Mechanism**  
   - 같은 주제지만 설명 축을 바꿈(개인심리 ↔ 사회제도)
3) **Near-Synonym Trap**  
   - 유사 의미지만 지문에서 요구하는 “정확한 뉘앙스”와 불일치
4) **Scope Shift**  
   - 일부↔전체, 단기↔장기, 원인↔결과
5) **Collocation Trap(선택)**  
   - 문법/품사 맞지만 결합이 미묘하게 어색

**형식 제약**
- 정답과 오답은 **품사/추상성/길이**를 최대한 맞춘다.
  - word형이면 모두 word형으로
  - phrase형이면 길이 범위를 비슷하게

---

#### 9.7.4 정답 유일성(Self-check) — BlankAgent는 강력 권장
Self-check 질문(LLM에게 JSON으로):
- “5개 선지 중 정답 외에 들어가도 자연스러운 것이 있는가?”
- “정답이 유일하지 않다면 이유는 무엇인가? (동의어/문맥부족/빈칸위치부적절 등)”

실패 조건:
- “정답 외 1개 이상도 가능”  
→ 오답 재생성 또는 빈칸 위치 변경 후 1회 재생성

---

### 9.8 ReferenceAgent (지칭)

**출력 형태**
- 지문 내 (a)(b)(c)(d)(e) 5개 지칭 표현 표시
- 질문: “(a)~(e) 중 가리키는 대상이 나머지 넷과 다른 것은?”
- 보기 5개: (a)…(e)

**고급 설계**
- 안정적으로 만들려면 “대상 2개(주대상1 + 부대상1)”를 명시적으로 등장시켜야 한다.
- 4개는 주대상을 가리키게, 1개만 부대상을 가리키게 설계.

**검증**
- 지칭표현(대명사/지시어)와 antecedent가 너무 멀면 난이도 과상승 → hard에서만 허용

---

### 9.9 VocabAgent (어휘)

**출력 형태**
- 밑줄 ①~⑤ 어휘(표현) 5개
- 질문: “문맥상 낱말의 쓰임이 적절하지 않은 것은?”
- 정답 1개

**고급 설계**
- 오답(틀린 어휘)은 3패턴 중 하나를 선택:
  1) polarity mismatch (긍/부정 충돌)
  2) selectional restriction 위반 (주어/목적어와 의미 결합 불가)
  3) collocation mismatch

**검증**
- 틀린 어휘가 “문법적으로”는 맞는데 “문맥상 의미”만 틀리게 만드는 것이 이상적
- 너무 쉬운 반의어(beautiful ↔ ugly 같은 노골)만 쓰면 easy로 내려감

---

### 9.10 GrammarAgent (어법)

**출력 형태**
- 밑줄 ①~⑤ 5개
- 질문: “어법상 틀린 것은?”
- 정답 1개

**고급 설계**
- 오류는 1개만(나머지 4개는 정상)
- 흔한 오류 패턴 라이브러리:
  - 수일치 / 시제 / 관계사 / 병렬 / 분사구문 / 대명사 격 / 동사 형태
- “의미는 통하지만 문법이 틀린” 수준으로

**검증**
- self-check로 “다른 밑줄도 어색할 여지가 있는지” 확인
- 2개 이상 문제 있으면 재생성

---

## 10) 프롬프트 템플릿(초안 + 고급 설계)

> 실제 구현에서는 `app/prompts/*.md`로 저장하고, `{passage}`, `{difficulty}`, `{seed}`, `{style}` 같은 변수로 포맷.

### 10.1 base_system.md (공통 system)
- 너는 “한국 고등학교 학력평가 영어 문제 출제자”다.
- 출력은 **오직 JSON**이어야 한다(코드블록/주석/설명 금지).
- 반드시:
  - choices는 정확히 5개
  - answer는 하나
  - explanation은 짧고 명확(1~3문장)

### 10.2 analysis.md (공통 분석)
- 출력 JSON: `PassageAnalysis` 스키마 준수
- 길게 쓰지 말고 핵심만

### 10.3 self_check.md (공통 self-check)
- 입력: 생성된 문제 JSON
- 출력: `{ "ok": true|false, "reasons": [...], "suggested_fix": "..." }`

### 10.4 blank.md (고급)
요구 JSON 키:
- type, passage, question, choices, answer, explanation, meta
- meta에 `blank_span_type: "word|phrase|clause"` 권장

프롬프트 핵심 지시:
- “지문에서 가장 핵심 논리(주장/결론/대조/인과)를 담는 구(phrase)를 선택해 빈칸으로 만든다.”
- “정답과 품사/추상성이 유사한 오답 4개를 만든다.”
- “오답은 최소 3가지 오답 패턴을 섞는다(Polarity Flip, Wrong Mechanism, Near-Synonym, Scope Shift, Collocation Trap).”
- “정답 유일성이 보장되도록 빈칸 위치와 오답을 조정한다.”

---

## 11) API 구현 디테일

### 11.1 main.py
- `FastAPI(title="Exam Item Generator", version="0.1.0")`
- `/health` GET
- `/api/v1/*` 라우터 포함

### 11.2 라우터
- 각 라우터 파일에서:
  - request 모델 import
  - agent 인스턴스 생성(의존성 주입 가능)
  - `response_model=` 지정

### 11.3 에러 처리
- 입력 텍스트 너무 짧음/너무 김: 422
- LLM JSON 파싱 실패: 502
- Validation 실패(재시도 후): 500

---

## 12) 테스트(최소)

- `tests/test_endpoints_smoke.py`:
  - 각 endpoint에 fixture passage로 POST
  - status_code == 200
  - response schema key 존재 확인
  - choices 길이 == 5 확인

> LLM 실 호출 대신, 테스트 모드에서는 `MockLLMClient`로 고정 JSON 반환하도록 설계 권장.  
> (ENV: `APP_ENV=test`일 때 mock 사용)

---

## 13) 구현 완료 기준(Definition of Done)

### 공통 DoD
- [ ] 10개 endpoint 동작
- [ ] 각 endpoint가 해당 type JSON 반환
- [ ] choices 5개/answer 1개/해설 포함
- [ ] 스키마 검증 및 self-check 옵션 동작(옵션)
- [ ] 스모크 테스트 통과

### 품질 DoD(1차 목표)
- [ ] 빈칸: 빈칸이 “핵심 논리”에 위치 + 오답이 그럴듯
- [ ] 삽입: 지시어/연결어 기반으로 정답 위치가 유일
- [ ] 순서: 문단 기능 태깅이 자연스러움
- [ ] 어휘/어법: 오답(오류) 1개만 실제로 틀리게 설계

---

## 14) 샘플 요청/응답

### Request
`POST /api/v1/blank`
```json
{
  "passage": "Humans rely on habits because ...",
  "difficulty": "mid",
  "seed": 123,
  "debug": true
}
```

### Response(형태 예시)
```json
{
  "type": "blank",
  "passage": "Humans rely on habits because _____ . ...",
  "question": "다음 빈칸에 들어갈 말로 가장 적절한 것은?",
  "choices": [
    {"label":"①","text":"..."},
    {"label":"②","text":"..."},
    {"label":"③","text":"..."},
    {"label":"④","text":"..."},
    {"label":"⑤","text":"..."}
  ],
  "answer": {"label":"③","text":"..."},
  "explanation": "본문에서 ... 때문에 ...가 가장 적절하다.",
  "meta": {
    "difficulty":"mid",
    "seed":123,
    "blank_span_type":"phrase",
    "debug": { "topic":"...", "thesis_candidates":["..."] }
  }
}
```

---

## 15) 구현 팁(코덱스용)

- 먼저 “스캐폴딩 + mock llm + 10 endpoints + validators + tests”까지 완성한다.
- 이후 프롬프트 튜닝 + self-check를 붙인다.
- 실제 품질은 **프롬프트 파일만 교체**해서 개선 가능하게 만든다(핵심).
- **BlankAgent는 self-check를 기본 ON으로 시작**하는 것을 권장한다(가장 품질 민감).

---

끝.
