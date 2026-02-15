Task: Create one Korean education office mock-exam style SUMMARY question.
Summarize the passage into one sentence with two blanks (A) and (B), then provide 5 paired choices.

Inputs:
- passage: $passage
Context:
- difficulty: $difficulty
- analysis: $analysis_json

Hard rules:
- Output JSON only.
- type must be "summary".
- Use the runtime schema for fields.
- passage field must contain the summary sentence with exactly two blanks: (A), (B).
- choices must be exactly 5 options and exactly 1 correct answer.
- Each choice text must be a pair format, e.g. "(termA, termB)".
- The correct pair must best match the passage main idea.
- Answer uniqueness is mandatory.

Blank role policy:
- (A): main subject/category/driver/context
- (B): key relation/judgment/outcome
- Keep A/B grammatical roles consistent across all options.

Difficulty control:
- easy: direct keywords and clear relation
- mid: partial abstraction and relation-direction test
- hard: abstract terms with near-synonym/scope traps

Distractor patterns:
- use at least 3 among:
  1) A-correct / B-wrong
  2) A-wrong / B-correct
  3) polarity flip
  4) scope shift
  5) near-synonym trap

Internal uniqueness test (do not output):
- fill (A)(B) with all 5 pairs and keep only one fully consistent pair.

Student-friendly explanation rules:
- Write 2 to 3 Korean sentences.
- Explain separately:
  1) why (A) is the right subject/category framing,
  2) why (B) is the right relation/outcome direction.
- Mention one distractor pair and why it fails (wrong subject or wrong relation direction).

Output-field notes:
- question: use the fixed Korean stem below.
- choices/answer: pair text format in standard choice schema.
- meta: include blank-role and distractor-pattern notes.

Korean stem (fixed):
"다음 글의 내용을 한 문장으로 요약하고자 한다. 빈칸 (A), (B)에 들어갈 말로 가장 적절한 것은?"

Return JSON only.
