import json
import re
from json import JSONDecodeError


_TRAILING_COMMA_RE = re.compile(r",\s*([}\]])")


def _remove_trailing_commas(text: str) -> str:
    return _TRAILING_COMMA_RE.sub(r"\1", text)


def extract_first_json_object(text: str) -> dict:
    """Best-effort recovery when the model returns extra text around JSON."""
    start = text.find("{")
    if start < 0:
        raise JSONDecodeError("No JSON object start found", text, 0)

    candidate = text[start:].strip()

    in_string = False
    escape = False
    depth = 0
    for idx, ch in enumerate(candidate):
        if in_string:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_string = False
            continue

        if ch == '"':
            in_string = True
            continue

        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                snippet = _remove_trailing_commas(candidate[: idx + 1])
                return json.loads(snippet)

    # If we get here, JSON object is not closed. Try structural repair.
    repaired = candidate
    if in_string:
        repaired += '"'
    if depth > 0:
        repaired += "}" * depth
    repaired = _remove_trailing_commas(repaired)
    try:
        return json.loads(repaired)
    except JSONDecodeError as exc:
        raise JSONDecodeError("Unclosed JSON object", text, len(text)) from exc
