Task: Create one Korean education office mock-exam style IRRELEVANT SENTENCE question.

Inputs:
- passage: $passage
Context:
- difficulty: $difficulty
- analysis: $analysis_json

Hard rules:
- Output JSON only.
- type must be "irrelevant".
- Use the runtime schema for fields.
- passage should contain exactly 5 numbered sentences (①~⑤).
- choices must be exactly 5 labels and exactly 1 correct answer.
- Exactly one sentence must be irrelevant to the overall flow.
- Ensure uniqueness: only one best irrelevant sentence.

Construction constraints:
- 4 on-topic sentences must share one coherent topic and progression.
- 1 irrelevant sentence should be superficially related but logically off-axis.
- Avoid obviously random or stylistically mismatched noise.

Irrelevant-pattern options (pick one primary):
A) scope shift
B) mechanism shift
C) domain drift
D) example mismatch
E) timeline/actor mismatch

Difficulty control:
- easy: mismatch is clear
- mid: plausible but thesis-irrelevant
- hard: highly plausible, subtle mismatch

Student-friendly explanation rules:
- Write 2 to 3 Korean sentences.
- Sentence 1: summarize the main topic/flow of the on-topic sentences.
- Sentence 2: explain exactly why the answer sentence breaks that flow (scope/mechanism/domain).

Output-field notes:
- question: use the fixed Korean stem below.
- choices/answer: standard label format.
- meta: include topic-flow note and irrelevant pattern.

Korean stem (fixed):
"다음 글에서 전체 흐름과 관계 없는 문장은?"

Return JSON only.
