from __future__ import annotations

from pathlib import Path
from string import Template

_PROMPT_DIR = Path(__file__).resolve().parent


def load_prompt(name: str) -> str:
    path = _PROMPT_DIR / f"{name}.md"
    return path.read_text(encoding="utf-8")


def render_prompt_with_base(base_name: str, name: str, **context: str) -> str:
    base = load_prompt(base_name)
    body = load_prompt(name)
    merged = f"{base}\n\n{body}".strip()
    template = Template(merged)
    return template.safe_substitute(**context)


def render_prompt(name: str, **context: str) -> str:
    """문항 유형용 프롬프트.

    `base_system`(출력 규칙) + `difficulty`(난이도 5지표) + 유형별 지시문 순으로 조립합니다.
    난이도를 유형마다 한 줄로 적으면 easy/mid/hard 가 구분되지 않아 공용 파일로 뺐습니다.

    단어장·동의어 교체는 문항이 아니라 이 경로를 쓰지 않습니다
    (`render_prompt_with_base` 로 각자의 base 를 씁니다).
    """
    parts = [
        load_prompt("base_system"),   # 출력 형식 규칙
        load_prompt("item_craft"),    # 공통 출제 기법(오답 레시피·유일성 증명·실패 사례)
        load_prompt("difficulty"),    # 난이도 5지표
        load_prompt(name),            # 유형별 지시문
    ]
    return Template("\n\n".join(parts).strip()).safe_substitute(**context)
