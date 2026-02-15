Task: Create one Korean education office mock-exam style IMPLICIT MEANING (함축 의미 추론) multiple-choice question.

Inputs:
- passage: $passage
Context:
- difficulty: $difficulty
- analysis: $analysis_json

Hard rules:
- Output JSON only (no markdown, no code block).
- type must be "implicit"
- DO NOT rewrite or paraphrase the passage in output.
- Instead of returning a modified passage, return:
  - underlined_span: an EXACT substring that appears in the input passage
  - occurrence: which occurrence of that substring to mark (default 1)
  - anchor_sentence_index: the 0-based index of the sentence containing it (if available)
- Provide exactly 5 choices and exactly 1 correct answer.
- The question must ask what the underlined part implies/means in context.
- Answer uniqueness is mandatory: only ONE choice matches the contextual meaning.

Underlined span selection rules (choose ONE span):
Priority order:
1) idiom/metaphor that is awkward if taken literally (e.g., “lost our marbles”, “move the needle”)
2) figurative evaluation or stance expression (e.g., “got colder”, “on the firing line”)
3) compressed figurative phrase that summarizes a situation (e.g., “turn lead to gold”)
Constraints:
- underlined_span should be 2 to 12 words (not too short, not too long).
- It MUST be copied EXACTLY from the passage (case/punctuation preserved).
- Avoid underlining an entire sentence.

Correct answer design (plain meaning):
- The correct choice must be a plain, direct paraphrase of the underlined_span's meaning in THIS context.
- It must not be a literal translation.
- It must match the passage’s stance/polarity and intention.

Distractor rules (must include ALL 4 categories at least once among the 4 distractors):
A) literal trap: interprets the phrase literally (surface meaning)
B) partial meaning: captures only part of the intended meaning, misses key nuance
C) polarity flip: reverses implication (positive↔negative, improvement↔worsening)
D) topic injection: uses passage keywords but does not explain the underlined phrase’s meaning

Additional distractor constraints:
- Keep all choices similar in length and style (English sentences or English clauses).
- Avoid obviously silly or unrelated options.
- Ensure no distractor can reasonably fit as another correct interpretation.

Difficulty control:
- easy: common idiom/metaphor; correct paraphrase very clear
- mid: metaphor is less common; distractors are plausible near-misses
- hard: nuance-based expression (tone/attitude shift); distractors are highly plausible but subtly wrong

Uniqueness self-test (do internally):
1) For each option, ask: “If a student replaces the underlined phrase with this option, does the passage meaning stay correct?”
2) If 2+ options seem acceptable:
   - make the correct option more precise to the context,
   - revise distractors to fail by one clear dimension (literal/partial/polarity/topic injection).
Do not output until only ONE option is best.

Korean stem to use (fixed):
"밑줄 친 부분이 의미하는 바로 가장 적절한 것은?"

Output JSON schema:
{
  "type": "implicit",
  "underlined_span": string,
  "occurrence": int,
  "anchor_sentence_index": int|null,
  "question": string,
  "choices": [{"label":"①","text":string}, ...],
  "answer": {"label":"③","text":string},
  "explanation": string,                    // 1-3 sentences in Korean
  "meta": {
    "difficulty": string,
    "seed": int|null,
    "span_kind": "idiom"|"metaphor"|"nuance"|"figurative",
    "distractor_patterns": [string,...]     // must include A/B/C/D labels
  }
}

Explanation requirements (Korean, concise):
- 1 sentence: explain the contextual meaning of the underlined_span.
- 1 sentence: why one tempting distractor is wrong (literal/partial/polarity).

Return JSON only.
