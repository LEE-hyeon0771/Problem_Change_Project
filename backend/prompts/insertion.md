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

Difficulty control (type-specific mapping of the shared levers):
- easy: the given sentence carries an explicit connective and a unique referent.
- mid: the connective is present but the referent requires tracking across one sentence.
- hard: the given sentence has NO explicit connective. Placement is decided by referential
  chains and given->new information flow alone. At least two slots must read acceptably on
  a first pass, and be excluded only by pronoun/article continuity.

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

Given-sentence design (this determines whether the item is solvable):
- The sentence MUST carry a cohesive tie back to its slot. Use at least two of:
  a discourse connective, a definite article referring to something just introduced,
  a demonstrative (this/these/such), a pronoun with one clear antecedent,
  or a comparative that presupposes an earlier term.
- The sentence must also carry NEW information forward, so the following sentence
  depends on it. A sentence that only looks backward can sit in several slots.
- Remove the sentence from the passage and reread: exactly one slot must leave a gap
  in the referential chain. If two slots read fine, redesign the sentence.

Slot design:
- Place the five markers so that at least two are locally plausible at easy/mid,
  three or more at hard. Markers at paragraph boundaries are usually too easy.

Insertion-specific failure modes:
- A given sentence with no anaphora — it fits anywhere.
- The correct slot being the only one where the sentence is grammatical.
- Placing the answer at ① or ⑤ where students guess by position habit.

Return JSON only.
