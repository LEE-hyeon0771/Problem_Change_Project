Task: Create one Korean education office mock-exam style ORDER question.

Inputs:
- passage: $passage
Context:
- difficulty: $difficulty
- analysis: $analysis_json

Hard rules:
- Output JSON only.
- type must be "order".
- Use the runtime schema for fields.
- passage must include a lead plus three blocks labeled (A), (B), (C).
- choices must be 5 unique A/B/C permutations.
- Exactly 1 correct answer.
- Ensure uniqueness: only one ordering is coherent.

Construction constraints:
- lead introduces topic without fully concluding.
- (A)(B)(C) should form a coherent mini-essay in the correct order.
- block functions should be distinct (claim/definition, example, conclusion/contrast).

Order-enforcement tools (use at least two):
1) discourse opener constraints (However/For example/Therefore/In other words)
2) coreference dependencies (this/they/it/such must have antecedents)
3) scope flow (general->specific->generalization, etc.)

Difficulty control:
- easy: explicit markers strongly constrain order
- mid: one marker + one coreference dependency
- hard: subtler markers but still uniquely solvable

Student-friendly explanation rules:
- Write 2 to 3 Korean sentences.
- State one ordering constraint explicitly (e.g., example-after-claim, therefore-after-reason).
- Explain why one wrong permutation breaks marker logic or antecedent continuity.

Output-field notes:
- question: use the fixed Korean stem below.
- choices[*].text: permutation strings like "(A)-(C)-(B)".
- meta: include constraints used and block function notes.

Korean stem (fixed):
"주어진 글 다음에 이어질 글의 순서로 가장 적절한 것을 고르시오."

Return JSON only.
