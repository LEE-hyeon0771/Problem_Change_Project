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

Difficulty control (type-specific mapping of the shared levers):
- The (A)/(B) pair is the difficulty lever. Both blanks must be decided together.
- easy: (A) and (B) are near-synonyms of passage words; only one pair is coherent.
- mid: one blank tests abstraction, the other tests relation direction (cause vs result).
- hard: BOTH blanks are abstractions with no passage vocabulary, and at least two
  distractor pairs are individually plausible - only their COMBINATION fails.
  Build traps from near-synonyms that differ in scope or intensity.

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

Passage suitability (check first):
- A summary item needs a claim PLUS a qualifier (condition, contrast, cause, or limit).
  (A) usually carries the claim, (B) the qualifier. If the passage has no qualifier,
  the second blank has nothing to test — pick a different relation and note it.

Interdependence requirement (this is what makes the type work):
- Neither blank may be solvable alone. Construct so that at least two (A) candidates are
  individually plausible and are eliminated only by their (B) partner.
- Build this by pairing a correct (A) with a wrong (B) in one distractor, and the reverse
  in another. Those two are your strongest options.

Distractor recipes for this type:
- correct (A) + `polarity_flip` (B)
- `scope_broad` (A) + correct (B)
- near-synonym of (A) that shifts intensity + plausible (B)
- both wrong but topically fluent — the "reads well" trap

Summary-specific failure modes:
- (A) and (B) drawn from unrelated semantic fields; the pair reads as nonsense and is free.
- The summary sentence copying passage wording — it must be a genuine compression.
- A summary sentence so long it becomes a second passage. Keep it to one sentence.

Return JSON only.
