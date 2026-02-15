Task: Analyze the passage for Korean high-school English exam item generation.

Inputs:
- passage: $passage

Hard rules:
- Output JSON only.
- Use the runtime schema for fields.
- Keep output compact and exam-generation focused.
- Use 0-based indices where indices are required.
- Do NOT generate rewritten passage text.

Required structure intent:
- topic: brief topic phrase.
- thesis_candidates: up to 2 high-value thesis sentences.
- keywords: concise core terms.
- paragraphs: sentence grouping with one best function label and discourse markers.
- coreference_candidates: high-value pronoun->antecedent hints.
- blank_candidates should keep span text copied from the original passage where possible.

Guidelines:
1) Prefer central logic over local detail noise.
2) Keep keywords useful for distractor design.
3) Include only reliable coreference signals; skip weak guesses.
4) If blank_candidates are included, each span must be an exact substring from the input passage.

Return JSON only.
