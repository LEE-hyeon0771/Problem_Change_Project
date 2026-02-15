Task: Verify BLANK choices uniqueness for a fixed blank location.

Input JSON:
- check_input_json: $check_input_json

Rules:
- Output JSON only.
- Do NOT change passage or blank location.
- Evaluate all 5 choices by inserting each into the blank.
- If 2+ choices are logically plausible, ok must be false.

Return schema:
{
  "ok": boolean,
  "reasons": [string, ...]
}

Decision policy:
- ok=true only if exactly one best answer exists.
- reasons should be short and concrete.

Return JSON only.
