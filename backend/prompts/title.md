Task: Create one Korean education office mock-exam style TITLE question from the passage.

Inputs:
- passage: $passage
Context:
- difficulty: $difficulty
- analysis: $analysis_json

Hard rules:
- Output JSON only.
- type must be "title".
- Use the runtime schema for fields.
- Exactly 5 choices and exactly 1 correct answer.
- choices[*].text must be SHORT English titles (typically 4~10 words).
- Avoid overly specific proper nouns unless the passage is mainly about that entity.
- Ensure uniqueness: only one title best matches the full gist.

Target style constraints:
- The correct title captures the MAIN CLAIM or MAIN PURPOSE, not a minor detail.
- Distractors should be plausible and similar in length/style.

Distractor patterns (all must appear at least once):
1) too narrow (minor detail only)
2) too broad (generic life lesson)
3) polarity flip (reverses stance)
4) topic drift / keyword trap

Difficulty control (type-specific mapping of the shared levers):
- Distractor patterns are NOT fixed. Choose them by level:
  - easy: too narrow / too broad / topic drift (3 of 4 are off-topic per L2)
  - mid: too broad / polarity flip / keyword trap + one scope error
  - hard: ALL four are scope-or-stance variants of the TRUE thesis.
    Forbidden at hard: topic drift and generic life lessons - free eliminations.
- Title length stays 4~10 words at every level. Difficulty comes from meaning, not length.
- hard: the key must NOT contain the passage's most frequent content word (L1).

Internal checklist (do not output):
1) Read analysis_json.topic and analysis_json.thesis_candidates.
2) Draft one thesis-faithful title.
3) Draft four distractors using the patterns above.
4) Verify only one best answer.

Student-friendly explanation rules:
- Write 2 to 3 Korean sentences for high-school learners.
- Sentence 1: explain why the correct title matches the thesis and scope.
- Sentence 2: explain why one tempting distractor fails (too broad/narrow or polarity flip).
- Avoid vague wording like "자연스럽다" without a concrete reason.

Output-field notes:
- passage: keep original or lightly normalized passage.
- question: use the fixed Korean stem below.
- choices/answer: standard 5-option multiple choice format.
- meta: include useful diagnostics such as distractor patterns used.

Korean stem (fixed):
"다음 글의 제목으로 가장 적절한 것은?"

Passage suitability (check first):
- A title item needs ONE dominant claim. If the passage merely lists or describes without
  arguing, the best title is the organizing principle of the list — say so in meta.note.
- If the passage has two competing claims, title the RESOLUTION, not either side.

Distractor recipes for this type (apply C2 transformations to the key):
- `scope_narrow`: title one example or one section as if it were the whole passage.
- `scope_broad`: turn the claim into a self-help maxim ("The Value of Hard Work").
- `polarity_flip`: keep the topic nouns, reverse what the passage concludes about them.
- `partial_truth`: name a real sub-point of the passage. Strongest distractor — use at mid/hard.
- `keyword_lure`: assemble the passage's three most memorable words into a claim it never makes.

Title-specific failure modes:
- A topic label instead of a claim ("Forests and Markets") — a title must assert something.
- A colon subtitle that restates the main clause; the subtitle must ADD, not echo.
- Using a proper noun that appears once in the passage.
- The key being the only option with a verb, or the only one with a colon — surface give-away.

Return JSON only.
