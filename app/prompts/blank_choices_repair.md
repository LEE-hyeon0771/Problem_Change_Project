Task: Regenerate ONLY choices/answer/explanation for a fixed BLANK item.

Input JSON:
- repair_input_json: $repair_input_json

Rules:
- Output JSON only.
- Do NOT rewrite passage.
- Keep blank location fixed.
- choices must be exactly 5 strings.
- answer_label must be one of ①~⑤.
- The answer choice text must equal blank_span exactly.
- Ensure uniqueness: only one best answer.

Student-friendly explanation:
- 2~3 Korean sentences with concrete reasoning.

Return schema:
{
  "choices": [string, string, string, string, string],
  "answer_label": "①"|"②"|"③"|"④"|"⑤",
  "explanation": string
}

Return JSON only.
