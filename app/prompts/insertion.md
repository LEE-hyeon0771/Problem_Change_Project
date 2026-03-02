Task: Create one Korean education office mock-exam style INSERTION question.

Inputs:
- passage: $passage
Context:
- difficulty: $difficulty
- analysis: $analysis_json

Hard rules:
- Output JSON only.
- type must be "insertion".
- Use the runtime schema for fields.
- The passage must show exactly five insertion slots labeled ① ② ③ ④ ⑤.
- Exactly 5 choices (labels ①~⑤) and exactly 1 correct answer.
- Ensure uniqueness: only one slot is clearly best.

Formatting rule for passage field:
- Include both the given sentence and slot passage inside the single passage field.
- Recommended format:
  - "[Given sentence] ..."
  - "[Passage] ... ① ... ② ... ③ ... ④ ... ⑤ ..."

Construction constraints:
- given sentence should be extracted or lightly paraphrased from the passage logic.
- Passage without the given sentence should still be coherent.
- Uniqueness must rely on both:
  1) discourse relation fit
  2) coreference continuity

Use at least two cue types:
- contrast / cause-effect / example / addition / clarification

Difficulty control:
- easy: explicit cue + obvious slot
- mid: cue + antecedent tracking together
- hard: subtle cues, still uniquely solvable

Student-friendly explanation rules:
- Write 2 to 3 Korean sentences.
- Identify one concrete discourse cue or coreference clue that fixes the correct slot.
- Explain why at least one nearby slot fails (wrong transition or missing antecedent).

Output-field notes:
- question: use the fixed Korean stem below.
- choices/answer: standard slot-label format.
- meta: include given_sentence, answer_position(1..5), cue notes.

Korean stem (fixed):
"글의 흐름으로 보아, 주어진 문장이 들어가기에 가장 적절한 곳을 고르시오."

Return JSON only.
