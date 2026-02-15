Task: Create one Korean education office mock-exam style TOPIC (주제) multiple-choice question from the passage.

Inputs:
- passage: $passage
Context:
- difficulty: $difficulty
- analysis: $analysis_json

Hard rules:
- Output JSON only (no markdown, no code block).
- type must be "topic"
- Exactly 5 choices.
- Exactly 1 correct answer.
- The correct choice must express the MAIN TOPIC (what the passage is mainly about), not a catchy title.
- Choices must be written in English.
- Each choice should be 5~12 words and primarily a noun-phrase style (not a full sentence).
- Avoid overly specific proper nouns unless the entire passage is centered on them.

Topic framing templates (use one of these for the correct answer):
Choose ONE best frame for this passage:
1) "Effects/Impact of X on Y"
2) "Reasons/Causes of X"
3) "Importance/Need for X"
4) "Misconceptions/Myths about X"
5) "Benefits/Advantages of X"
6) "How X influences decision-making/behavior" (if passage is psych/behavioral)

Correct-answer requirements:
- Must match analysis_json.gist and thesis_candidates (prefer thesis_candidates[0]).
- Must match the passage scope (not too broad, not too narrow).
- Must align with stance/polarity (do not invert the implication).

Distractor rules (must cover ALL 4 categories at least once across the 4 distractors):
A) Too narrow: focuses on a minor example/detail only
B) Too broad: generic life lesson, overly general
C) Polarity flip: reverses the passage’s implication (benefit↔harm, increase↔decrease)
D) Topic drift / keyword trap: uses 1-2 key terms from passage but misses the core claim

Additional distractor constraints:
- Keep the same style/length as the correct answer.
- Make distractors plausible: share at least one keyword or domain concept.
- Avoid obviously unrelated or silly distractors.
- Ensure no distractor is arguably equally correct.

Difficulty control:
- easy:
  - Correct topic closely matches passage keywords
  - Distractors are clearly wrong by scope or polarity
- mid:
  - Distractors share 1-2 strong keywords and sound plausible
  - Only one matches thesis + scope + stance
- hard:
  - Distractors are highly plausible near-misses
  - Differences hinge on scope (who/what is included) or stance (what the passage concludes)

Uniqueness self-test (do internally):
1) Check each option against the gist:
   - Does it cover the full passage, not just one part?
   - Does it preserve stance/polarity?
2) If 2+ options seem correct:
   - tighten the correct option to better reflect the thesis,
   - revise distractors to be wrong by one clear dimension (scope/polarity/mechanism).
Do not output until only ONE option is best.

Korean stem to use (fixed):
"다음 글의 주제로 가장 적절한 것은?"

Output JSON schema (standard fields):
{
  "type": "topic",
  "passage": string,                       // keep the input passage; do not paraphrase
  "question": string,
  "choices": [{"label":"①","text":string}, ...],
  "answer": {"label":"③","text":string},
  "explanation": string,                   // 1-3 sentences in Korean
  "meta": {
    "difficulty": string,
    "seed": int|null,
    "topic_frame": string,                 // one of the framing templates
    "distractor_patterns": [string,...]    // include A/B/C/D mapping used
  }
}

Explanation requirements (Korean, concise):
- 1 sentence: why the correct topic captures the whole gist.
- 1 sentence: why one tempting distractor fails (scope or polarity).

Return JSON only.
