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

Difficulty control (type-specific mapping of the shared levers):
- easy: each block opens with an explicit discourse marker that fixes its position.
- mid: one marker plus one coreference dependency must be combined.
- hard: markers are absent or ambiguous. Order is fixed only by referential chains
  (a pronoun cannot precede its antecedent) and by given->new information flow.
  At least two orderings must look plausible until the referent check is applied.

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

Passage suitability (check first):
- 순서 needs THREE chunks that are each internally coherent and mutually ordered by
  something other than topic. If the passage is a flat list, any order reads fine and
  the item has no answer. Split at logical joints: claim / evidence / implication,
  or problem / mechanism / consequence.
- Each block should be 2~4 sentences. One-sentence blocks give too few cues.

Order-fixing devices (the item must rest on at least two):
- referential chain: a pronoun or definite noun phrase cannot precede its antecedent
- given→new flow: a block that opens with new information cannot follow the lead
- discourse connective that presupposes a specific prior move (However, As a result, Instead)
- lexical chain: an unexplained technical term cannot appear before its introduction

Distractor design:
- The four wrong orders must each violate exactly ONE device, so each has a nameable reason.
- Do not offer an order that violates nothing — students will defend it.

Order-specific failure modes:
- Blocks that can be read in two orders because the only cue is topical similarity.
- A block that begins with an explicit "First," — it fixes the order too cheaply.
- Rewriting the passage while splitting. Split only; never paraphrase.

Return JSON only.
