from __future__ import annotations

from pathlib import Path
from string import Template

_PROMPT_DIR = Path(__file__).resolve().parent


def load_prompt(name: str) -> str:
    path = _PROMPT_DIR / f"{name}.md"
    return path.read_text(encoding="utf-8")


def render_prompt(name: str, **context: str) -> str:
    base = load_prompt("base_system")
    body = load_prompt(name)
    merged = f"{base}\n\n{body}".strip()
    template = Template(merged)
    return template.safe_substitute(**context)
