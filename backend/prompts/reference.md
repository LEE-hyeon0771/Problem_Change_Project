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

Difficulty control (type-specific mapping of the shared levers):
- easy: competing antecedents differ in number or animacy; the clue is grammatical.
- mid: antecedents agree grammatically; discourse tracking across one sentence is needed.
- hard: at least three antecedents agree in number and semantic class. The answer is
  settled only by thematic role continuity or by the logic of the claim being made.

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

Construction (five underlined referring expressions, exactly one differing):
- Four must point to the SAME entity; one to a different entity. The odd one out is the answer.
- All five should be the same kind of expression (all pronouns, or all demonstrative NPs).
  Mixing "it" with "the policy" makes the odd one visible by form alone.
- Every antecedent must be explicitly present in the passage. Never rely on an implied entity.

Making it discriminating:
- easy: the odd referent differs in number or animacy — grammar settles it.
- mid: all agree grammatically; the reader must track the discourse across one sentence.
- hard: at least three candidate antecedents agree in number AND semantic class, so the
  answer rests on thematic-role continuity (who keeps doing the acting) or on which
  reading makes the claim coherent.

Reference-specific failure modes:
- A genuinely ambiguous pronoun — if two readings are defensible, the item is broken.
- The odd one being the only one in a different sentence position (e.g. only subject).
- Underlining a pronoun whose antecedent sits in the same clause — too local to test.

Return JSON only.
