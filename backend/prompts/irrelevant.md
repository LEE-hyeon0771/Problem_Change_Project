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

Difficulty control (type-specific mapping of the shared levers):
- The irrelevant sentence is always grammatical and topically related - never random.
- easy: it contradicts the thesis or changes the subject visibly.
- mid: it is true and on-topic but supports a DIFFERENT claim than the paragraph's.
- hard: it is true, on-topic, uses the paragraph's own vocabulary, and would fit an
  adjacent paragraph - it fails only because it breaks the local logical chain
  (e.g. supplies an example for a claim that was never made).

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

Passage suitability (check first):
- 무관문장 needs a paragraph developing ONE claim. If the paragraph already shifts topic,
  there is no single intruder to find.

Intruder sentence design (this is the whole item):
- It must be TRUE, grammatical, on-topic, and use the paragraph's vocabulary.
  An off-topic or false sentence is a free elimination.
- It must fail on the LOGICAL CHAIN, not the subject matter. Working patterns:
  - supplies an example for a claim the paragraph never makes
  - states a related fact that neither supports nor advances the claim
  - jumps to a consequence the paragraph has not yet earned
  - restates an earlier sentence without advancing (redundancy, not contradiction)
- Test: delete the sentence. The paragraph must read BETTER — tighter, not thinner.
  If deleting it loses information the paragraph needs, it is not the intruder.

Irrelevant-specific failure modes:
- An intruder that contradicts the passage — that is a different skill (사실 확인).
- An intruder placed first or last, where flow cues are weakest for everyone.
- Marking a sentence that is merely a digression the author clearly intended.

Return JSON only.
