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

Difficulty control (type-specific mapping of the shared levers):
- easy: the wrong word contradicts the sentence's own logic (polarity clash).
- mid: the wrong word is topically fine but breaks a collocation or shifts scope.
- hard: the wrong word is a NEAR-SYNONYM of the right one, differing only in connotation,
  register, or the type of object it takes. The other four targets must be words a student
  might also doubt - but each is defensible in context.
- At every level exactly one target may be wrong. Never create a second defensible answer.

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

Construction (five marked words, exactly one contextually wrong):
- All five targets must be words a student could plausibly doubt. If four are obviously
  fine, the item is a one-step elimination.
- The wrong word must be wrong SEMANTICALLY, never grammatically. If replacing it fixes
  a grammar problem, you have written a 어법 item by mistake.
- The wrong word must have a clear intended replacement — you should be able to name the
  word that belongs there. If you cannot, the error is too vague to defend.

Error patterns, strongest first:
- `polarity`: the word reverses the sentence's logic (increase where the passage reduces)
- `collocation`: the word does not take this object/preposition in academic English
- `register`: a casual word in an academic argument, or vice versa
- `scope`: a word that over- or under-states the claim's range
- `near_synonym`: correct domain, wrong nuance — reserve this for hard

Vocab-specific failure modes:
- A "wrong" word that a careful reader can defend — the single most common rejection.
- Choosing a word so rare that the item tests vocabulary knowledge, not contextual reading.
- Marking two words that both look off, creating a second defensible answer.

Return JSON only.
