Task: Create one Korean education office mock-exam style REFERENCE question.

Inputs:
- passage: $passage
Context:
- difficulty: $difficulty
- analysis: $analysis_json

Hard rules:
- Output JSON only.
- type must be "reference".
- Use the runtime schema for fields.
- passage must include exactly five marked mentions: (1), (2), (3), (4), (5).
- Each marker must attach to a referring expression.
- Exactly 5 choices and exactly 1 correct answer.
- choices should map ①~⑤ to (1)~(5).
- answer must be an object with both "label" and "text", and it must exactly match one choices item.
- Never return answer as a plain string/number.
- Ensure uniqueness: four markers share one antecedent, one marker has a different antecedent.

Construction constraints:
- Use a coherent 5~7 sentence passage.
- Keep antecedents clear but not trivial.
- Spread the four same-antecedent markers across the passage.
- The odd marker should be plausible, not obviously random.

Antecedent pattern options (choose one):
A) person vs person
B) person vs group
C) object vs idea
D) singular vs plural entity

Difficulty control:
- easy: number/gender clues are clearer
- mid: discourse tracking needed
- hard: semantically similar competing antecedents

Student-friendly explanation rules:
- Write exactly 2 Korean sentences.
- Clearly state the shared antecedent of four markers.
- Then state the odd marker's antecedent and why it differs.

Output-field notes:
- question: use the fixed Korean stem below.
- choices[*].text: "(1)"~"(5)" mapping.
- meta: include shared/odd antecedent notes and pattern.

Korean stem (fixed):
"위 글의 밑줄 친 (1)~(5) 중에서 가리키는 대상이 나머지 넷과 다른 것은?"

Return JSON only.
