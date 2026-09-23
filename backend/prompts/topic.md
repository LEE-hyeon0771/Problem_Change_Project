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

Difficulty control (type-specific mapping of the shared levers):
- easy: the key restates the thesis with its own keywords; distractors differ in topic.
- mid: distractors share the topic noun but shift scope or polarity.
- hard: every option names the same topic noun. They differ only in what is CLAIMED
  about it - stance, scope, agent, or degree. The reader must compare claims, not topics.
- hard: no option may be eliminated by keyword mismatch alone (L1 = zero reuse).

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

Passage suitability (check first):
- 주제 asks what the passage ARGUES, not what it is about. If the passage is purely
  expository, state the organizing claim the exposition supports.

How 주제 differs from 제목 (do not blur them):
- 제목 may be catchy and elliptical; 주제 must be a complete proposition.
- 주제 options are noun phrases in Korean exam style: "the necessity of X for Y",
  "how A shapes B", "why A fails to B". Keep every option in the SAME frame.

Distractor recipes for this type:
- `degree_shift`: correct claim, but "always/all" where the passage says "often/many".
- `agent_swap`: correct mechanism, wrong actor (market ↔ policy, individual ↔ institution).
- `causal_reverse`: state the effect as the cause.
- `scope_narrow`: elevate one paragraph's point to the whole passage.

Topic-specific failure modes:
- Options that differ only in wording, not in claim — the student cannot discriminate.
- A distractor that is outside the passage's domain entirely (free elimination at mid/hard).
- Mixing frames (one option is "the importance of...", another is "why X happens") —
  the frame itself becomes the give-away.

Return JSON only.
