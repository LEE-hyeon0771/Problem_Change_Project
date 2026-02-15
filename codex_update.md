# codex_update.md — 작업 업뎃: 주제/함축의미추론 2유형 추가 + 품질/안정성 강화 지침

이 문서는 기존 `codex.md`/`codex_advanced.md` 위에 **추가 구현해야 할 변경 사항만** 정리한 “업데이트 지시서”다.  
CODEX가 그대로 보고 리팩터링/추가 구현을 진행할 수 있도록 **파일 트리 변경, 라우트/에이전트 추가, 프롬프트 추가, 스키마 변경, 검증 로직**을 명시한다.

---

## 0) 이번 업데이트 목표

1) **유형 추가 (2개)**
- 주제(Topic) 문제
- 함축의미추론(Implicit Meaning / Underlined meaning) 문제

2) **품질/안정성 강화**
- “원문 지문을 정확히 유지” 원칙 강화 (LLM이 passage를 재작성하지 못하게 설계)
- JSON 잘림(MAX_TOKENS) 및 스키마 강제 출력 안정화

참고(공식 문서):
- Gemini generateContent (Google AI for Developers) citeturn0search1
- GenerationConfig / responseSchema, responseMimeType(application/json) citeturn0search3

---

## 1) 라우트/에이전트 확장 (10 → 12)

### 1.1 신규 유형 2개 추가
| # | 유형(한글) | route | agent 클래스 | prompt |
|---|---|---|---|---|
| 11 | 주제 | `POST /api/v1/topic` | `TopicAgent` | `topic.md` |
| 12 | 함축의미추론 | `POST /api/v1/implicit` | `ImplicitAgent` | `implicit.md` |

> 기존 10개는 유지. 총 12개 endpoints.

### 1.2 파일 트리 변경(추가 파일)
```
app/
  schemas/
    topic.py
    implicit.py
  agents/
    topic_agent.py
    implicit_agent.py
  prompts/
    topic.md
    implicit.md
```

---

## 2) 공통 원칙: “원문 유지”를 코드로 강제

### 2.1 금지: LLM이 passage를 생성/패러프레이징
- title/topic/summary/… 대부분은 passage를 그대로 반환해도 되지만,
- **빈칸(blank)**, **함축(implicit)**은 “표시(빈칸/밑줄)”가 들어가야 하므로 LLM이 passage를 만들게 하면 패러프레이징이 발생한다.

### 2.2 권장: LLM은 “스팬 선택/선지 생성”만, 표시 작업은 Python이 수행
- BlankAgent: LLM 출력에 `blank_span`, `occurrence`, `blank_span_type`, `choices`, `answer_label`, `explanation`만 받는다.
  - 서버가 `build_passage_with_blank(original_passage, blank_span, occurrence)`로 `_____` 치환
- ImplicitAgent: LLM 출력에 `underlined_span`, `occurrence`(or context), `choices`, `answer_label`, `explanation`만 받는다.
  - 서버가 `apply_underline_markers(original_passage, underlined_span, occurrence)`로 표시(예: `__(...)__` 또는 `[UNDERLINE]...[/UNDERLINE]` 또는 `⟪ ⟫` 등)

> 이 패턴을 쓰면 “원문이 1바이트도 변하지 않고” 표식만 추가된다.

### 2.3 구현해야 할 공통 유틸(권장 위치: `app/toolkit/text.py`)
- `replace_nth(text: str, target: str, replacement: str, occurrence: int = 1) -> str`
- `assert_exactly_one_blank(text: str) -> None`
- `assert_span_exists(text: str, target: str) -> None`
- `normalize_newlines_only(text: str) -> str` (선택: CRLF/ LF 정규화만 수행, 단어/구문 변화 금지)

---

## 3) Gemini JSON 잘림(MAX_TOKENS) 안정화 체크

현재 로그에서 `finish_reason=MAX_TOKENS`가 매우 짧은 출력(chars ~ 280)에서도 발생하는 것은 **max output token 설정이 실제 payload에 반영되지 않을 가능성**이 높다.

### 3.1 요청 payload 점검/수정
- REST `generateContent`에서 토큰 제한은 보통 다음 키를 사용한다:
  - `generationConfig.maxOutputTokens`
- JSON schema 강제 시에는:
  - `generationConfig.responseMimeType = "application/json"`
  - `generationConfig.responseSchema = ...`
  를 함께 써야 한다. citeturn0search3

### 3.2 대응 전략 (권장 순서)
1) **payload에 `generationConfig.maxOutputTokens`가 실제로 들어가는지 로그로 확인**
2) schema=True 경로에서 자주 잘리면:
   - schema 모드를 끄고(JSON only 프롬프트 + robust JSON extractor)로 fallback을 “정상 경로”로 승격
3) JSON이 잘릴 때는:
   - 요청하는 output 키를 줄이고(meta 최소화)
   - explanation 길이를 1문장으로 제한

---

## 4) 신규 유형 11: 주제(Topic) — 전략 및 구현 스펙

### 4.1 문제 정의
- “다음 글의 주제로 가장 적절한 것은?” 5지선다
- title과 유사하지만 “멋진 제목”이 아니라 **핵심 화제/논점 범주**를 고르게 함

### 4.2 정답 생성 규칙(권장 템플릿)
- `X의 영향/효과/역할`
- `X의 필요성/중요성`
- `X의 원인/요인`
- `X의 장점/이점`
- `X에 대한 오해/잘못된 믿음`

### 4.3 오답(4개) 패턴(각 1개 이상 포함)
- too narrow (세부 예시만)
- too broad (일반론)
- polarity flip (결론 반전)
- topic drift/keyword trap (키워드 공유, 논점 이탈)

### 4.4 API 스키마(`app/schemas/topic.py`)
ProblemResponse와 동일하되 `type="topic"`.

```json
{
  "type": "topic",
  "passage": "...(원문 유지)...",
  "question": "다음 글의 주제로 가장 적절한 것은?",
  "choices": [{"label":"①","text":"..."}, ...],
  "answer": {"label":"③","text":"..."},
  "explanation": "...",
  "meta": {"difficulty":"mid","seed":123,"distractor_patterns":[...]}
}
```

### 4.5 prompt 추가: `prompts/topic.md`
- title.md와 거의 동일하지만, “title처럼 멋있게” 금지, topic noun phrase 지향
- 오답 패턴 강제

---

## 5) 신규 유형 12: 함축의미추론(Implicit Meaning) — 전략 및 구현 스펙

### 5.1 문제 정의
- 밑줄 친 표현(관용/은유/비유/뉘앙스)이 의미하는 바를 고르는 문제
- 반드시 **원문 표현을 그대로 밑줄 처리**해야 함(패러프레이징 금지)

### 5.2 밑줄 대상(underlined_span) 선정 규칙
우선순위:
1) 직역이 어색한 관용/은유 표현 (marbles, needle, lead to gold 등)
2) however/therefore 같은 담화 표지어 포함 문장
3) 평가 뉘앙스(warmer/colder 등) — hard 난이도에서 사용

### 5.3 정답 생성 규칙
- underlined_span을 **평이한 의미(paraphrase meaning)**로 변환한 문장/구를 정답으로
- 문맥에 맞는 “의도” 중심(직역 금지)

### 5.4 오답(4개) 패턴(각 1개 이상 포함)
- literal trap (직역)
- partial meaning (부분만 맞음)
- polarity flip (의미 반전)
- topic injection (지문 키워드만 끼워넣고 의미와 무관)

### 5.5 API 스키마(`app/schemas/implicit.py`)
- 응답 passage는 **원문에 밑줄 표식만 추가** (LLM이 passage 생성 금지)

```json
{
  "type": "implicit",
  "passage": ".... ⟪underlined span⟫ ....",
  "question": "밑줄 친 부분이 의미하는 바로 가장 적절한 것은?",
  "choices": [{"label":"①","text":"..."}, ...],
  "answer": {"label":"④","text":"..."},
  "explanation": "...",
  "meta": {
    "difficulty":"mid",
    "seed":123,
    "underlined_span":"...",
    "occurrence":1,
    "distractor_patterns":[...]
  }
}
```

### 5.6 prompt 추가: `prompts/implicit.md`
- 출력에는 `underlined_span`, `occurrence`, `choices`, `answer_label`, `explanation`만 포함
- 서버가 underline 마킹 적용

---

## 6) analysis.md 업데이트 포인트(신규 유형 지원)

기존 analysis.md(advanced)를 사용하되, 아래 필드를 “있으면 유리”:
- `topic`/`gist`는 이미 존재
- 함축의미용 후보:
  - `idiom_candidates`: [{sentence_index, span, type:"idiom|metaphor|nuance", reason}]
  - `tone_shift_markers`: [(sentence_index, cue)]

> 단, 즉시 구현이 어렵다면 `ImplicitAgent` 내부에서 1차 후보 선정도 가능.

---

## 7) self_check.md 업데이트 포인트(신규 유형 지원)

### 7.1 topic
- “scope/stance” 기준으로 정답 유일성 점검
- 2개 이상 맞아 보이면 `revise_choices`

### 7.2 implicit
- underlined span이 원문에 정확히 존재하는지 확인
- 정답이 직역이 아닌지 확인
- 오답에 literal trap이 포함되는지 확인

---

## 8) 테스트 추가(스모크)

### 8.1 endpoints smoke
- `/api/v1/topic`, `/api/v1/implicit` 응답 스키마 검사
- choices=5, answer=1

### 8.2 원문 유지 검사(implicit, blank)
- blank: 입력 passage와 출력 passage를 비교했을 때 변경이 `_____` 치환 위치에만 있는지
- implicit: 밑줄 표식 외 텍스트 변경이 없는지

---

## 9) CODEX 실행 지시(붙여넣기용)

아래를 CODEX에게 그대로 전달해 구현을 진행한다.

1) topic/implicit 2개 endpoint 추가 + agent/prompt/schema 추가
2) implicit/blank는 LLM이 passage를 생성하지 못하도록 “span-only 출력 → Python 치환”으로 구조 변경
3) Gemini client에서 `generationConfig.maxOutputTokens` 및 JSON schema 설정이 실제 payload에 반영되도록 수정
4) self_check 및 테스트에 신규 유형/원문 유지 검사 추가

---

끝.
