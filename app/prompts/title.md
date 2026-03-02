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

Difficulty control:
- easy: correct title close to gist keywords, distractors clearer
- mid: distractors share strong keywords, only one matches thesis
- hard: distractors highly plausible, separated by scope/stance

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

Return JSON only.
