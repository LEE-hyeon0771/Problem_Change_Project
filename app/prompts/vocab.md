Task: Create one Korean education office mock-exam style VOCAB question.
Identify the ONE underlined part that is semantically inappropriate in context.

Inputs:
- passage: $passage
Context:
- difficulty: $difficulty
- analysis: $analysis_json

Hard rules:
- Output JSON only.
- type must be "vocab".
- Use the runtime schema for fields.
- passage must include EXACTLY five target markers: [[1]] [[2]] [[3]] [[4]] [[5]].
- choices must be 5 labels (①~⑤), and answer must be one of them.
- Exactly ONE target is wrong in meaning/usage.
- The other four targets must be contextually appropriate.
- Do NOT make this a grammar error.

Error pattern (choose one primary type):
A) polarity mismatch
B) logical contradiction
C) collocation/selection mismatch
D) register mismatch
E) scope mismatch

Difficulty control:
- easy: wrong word is clearly contradictory
- mid: wrong word is subtly off
- hard: near-synonym trap

Internal uniqueness test (do not output):
- confirm only one marked target is semantically wrong.
- if 2+ targets are questionable, revise.

Student-friendly explanation rules:
- Write 2 to 3 Korean sentences.
- Explain the exact meaning conflict of the wrong option in context.
- Mention one correct option contrastively (why that one is context-appropriate).

Output-field notes:
- question: use the fixed Korean stem below.
- choices/answer: standard label format.
- meta: include error pattern and short reason notes.

Korean stem (fixed):
"다음 글의 밑줄 친 부분 중, 문맥상 낱말의 쓰임이 적절하지 않은 것은?"

Return JSON only.
