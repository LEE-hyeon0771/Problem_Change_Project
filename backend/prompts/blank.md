Task: Select a blank span from the ORIGINAL passage and generate choices for one BLANK question.

Inputs:
- passage (ORIGINAL; do not rewrite): $passage
Context:
- difficulty: $difficulty
- analysis: $analysis_json
- retry_hint: $retry_hint
- excluded_spans: $excluded_spans

Critical output contract:
- Output JSON only.
- Return ONLY these keys:
  - blank_span: string
  - occurrence: int (>=1)
  - blank_span_type: "word"|"phrase"|"clause"
  - blank_role: "thesis"|"contrast_pivot"|"causal_conclusion"|"generalization"
  - choices: [string, string, string, string, string]
  - answer_label: "①"|"②"|"③"|"④"|"⑤"
  - explanation: string (2~3 Korean sentences)
- Do NOT return passage/question/answer objects.

Hard rules:
- Do NOT rewrite or paraphrase the passage.
- blank_span must be an EXACT contiguous substring copied from the original passage.
- If the same blank_span appears multiple times, set occurrence correctly.
- choices must be exactly 5.
- Exactly one correct answer.
- The correct choice text must be the exact blank_span.
- Respect retry_hint and do not reuse excluded_spans.

Difficulty policy (type-specific mapping of the shared levers):
- Span type is a starting point, not the difficulty itself:
  easy -> blank_span_type=word, mid -> phrase, hard -> clause
- The real lever is what the span CARRIES:
  - easy: the span restates a nearby sentence; local context is enough.
  - mid: the span is the pivot of a contrast or causal step; needs the sentences around it.
  - hard: the span is the thesis or its generalization. Justifying it requires integrating
    three or more sentences (L3). Local context alone must be insufficient.
- Distractors replace the span, so they must be grammatically interchangeable:
  - easy: 3 are off-topic or contradict the passage outright.
  - mid: 2 are topically right but wrong in scope or direction.
  - hard: all 4 fit grammatically AND topically; each fails on exactly one of
    scope / polarity / agent / degree / causal direction.

Choice quality policy:
- Keep all options in the same grammatical form.
- Distractors must be plausible but logically wrong.
- If two or more choices can fit, revise choices before output.

Student-friendly explanation:
- 2~3 Korean sentences.
- Sentence 1: name the clue around the blank.
- Sentence 2: why correct choice fits.
- Sentence 3(optional): why one tempting distractor fails.

Passage suitability and span selection (do this before choosing choices):
- The span must carry the passage's ARGUMENT, not information. Rank candidates:
  1. the thesis or its restatement
  2. the pivot of a contrast ("However, X" — blank X)
  3. the conclusion of a causal chain ("Therefore, X")
  4. a generalization drawn from an example
- Never blank: a proper noun, a number, a date, an example's concrete detail,
  or anything recoverable from the SAME sentence.
- Test: cover the span. If the sentence alone still gives it away, choose another span.

Distractor recipes for this type (they replace the span, so they must be substitutable):
- `polarity_flip`: same vocabulary, opposite logical direction.
- `causal_reverse`: swaps what causes what.
- `scope_broad`: a true generalization that the passage does not support HERE.
- `keyword_lure`: reuses words from the surrounding sentences but breaks the logic.

Blank-specific failure modes:
- Two options both fit because the blank is too short to discriminate.
- The blank's grammar leaks the answer (article, singular/plural, to-infinitive).
- A distractor that is ungrammatical in the slot — students eliminate it without reading.
- The span chosen from the first sentence, before the passage has established anything.

Return JSON only.
