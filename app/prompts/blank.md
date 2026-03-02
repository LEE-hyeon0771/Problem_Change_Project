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

Difficulty policy:
- easy -> blank_span_type=word preferred
- mid -> blank_span_type=phrase preferred
- hard -> blank_span_type=clause preferred

Choice quality policy:
- Keep all options in the same grammatical form.
- Distractors must be plausible but logically wrong.
- If two or more choices can fit, revise choices before output.

Student-friendly explanation:
- 2~3 Korean sentences.
- Sentence 1: name the clue around the blank.
- Sentence 2: why correct choice fits.
- Sentence 3(optional): why one tempting distractor fails.

Return JSON only.
