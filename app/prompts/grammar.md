Task: Create one Korean education office mock-exam style GRAMMAR question.
Identify the ONE underlined part that is grammatically incorrect.

Inputs:
- passage: $passage
Context:
- difficulty: $difficulty
- analysis: $analysis_json

Hard rules:
- Output JSON only.
- type must be "grammar".
- Use the runtime schema for fields.
- passage must include EXACTLY five target markers: [[1]] [[2]] [[3]] [[4]] [[5]].
- choices must be 5 labels (①~⑤), and answer must be one of them.
- Exactly ONE marked target must be grammatically incorrect.
- The other four must be grammatically correct.
- The wrong segment should stay interpretable in context.

Error types (choose one primary type):
A) subject-verb agreement
B) verb form / tense / participle
C) relative clause / pronoun case
D) parallel structure
E) misplaced modifier / dangling participle
F) preposition / complement pattern

Difficulty control:
- easy: clear agreement/tense error
- mid: common exam trap
- hard: subtle but unambiguous rule violation

Internal uniqueness test (do not output):
- verify only one marked segment is wrong.
- revise if any other segment is debatable.

Student-friendly explanation rules:
- Write 2 to 3 Korean sentences.
- Name the grammar rule first (e.g., 수일치, 시제, 관계사).
- Show the corrected form briefly and explain why one nearby option is not an error.

Output-field notes:
- question: use the fixed Korean stem below.
- choices/answer: standard label format.
- meta: include error type and short rule note.

Korean stem (fixed):
"다음 글의 밑줄 친 부분 중, 어법상 틀린 것은?"

Return JSON only.
