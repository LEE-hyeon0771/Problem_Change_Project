"""난이도 명세가 실제로 프롬프트에 실리는지 검증.

한때 `git checkout -- backend/prompts/` 가 같은 디렉터리의 `loader.py` 까지 되돌려
공용 난이도 명세가 조용히 빠진 적이 있습니다. 프롬프트는 깨져도 테스트가 통과하고
생성도 "그�럴듯하게" 되기 때문에 배선 자체를 고정합니다.
"""

import pytest

from backend.prompts.loader import load_prompt, render_prompt, render_prompt_with_base

ITEM_TYPES = [
    "title", "topic", "summary", "blank", "implicit", "insertion",
    "order", "irrelevant", "reference", "vocab", "grammar",
]
LEVELS = ["easy", "mid", "hard"]


def _render(item_type: str, difficulty: str) -> str:
    return render_prompt(
        item_type,
        passage="X",
        difficulty=difficulty,
        analysis_json="{}",
        style="edu_office",
        seed="",
        explain="true",
        return_korean_stem="true",
        choices="5",
        retry_hint="",
        excluded_spans="",
    )


@pytest.mark.parametrize("item_type", ITEM_TYPES)
def test_shared_difficulty_spec_is_included(item_type: str) -> None:
    """유형별로 난이도를 한 줄씩 적으면 easy/mid/hard 가 구분되지 않습니다."""
    prompt = _render(item_type, "hard")

    assert "DIFFICULTY SPECIFICATION" in prompt, f"{item_type}: 공용 난이도 명세가 빠졌습니다."


@pytest.mark.parametrize("item_type", ITEM_TYPES)
@pytest.mark.parametrize("level", LEVELS)
def test_level_is_substituted(item_type: str, level: str) -> None:
    prompt = _render(item_type, level)

    assert f"Current level: **{level}**" in prompt
    assert "$difficulty" not in prompt, "치환되지 않은 변수가 남았습니다."


@pytest.mark.parametrize("item_type", ITEM_TYPES)
def test_each_type_maps_the_shared_levers(item_type: str) -> None:
    """공용 지표를 그 유형의 기계로 번역하는 블록이 있어야 합니다."""
    body = load_prompt(item_type)

    assert "type-specific mapping of the shared levers" in body, (
        f"{item_type}.md 의 난이도 블록이 옛 한 줄짜리로 되돌아갔습니다."
    )
    for level in LEVELS:
        assert f"{level}:" in body, f"{item_type}: {level} 지시가 없습니다."


def test_difficulty_spec_defines_all_five_levers() -> None:
    spec = load_prompt("difficulty")

    for lever in ["L1.", "L2.", "L3.", "L4.", "L5."]:
        assert lever in spec, f"난이도 지표 {lever} 가 없습니다."
    for level in LEVELS:
        assert spec.count(f"**{level}**") >= 5, f"{level} 이 5개 지표 전부에 정의되지 않았습니다."


@pytest.mark.parametrize("item_type", ITEM_TYPES)
def test_type_prompts_keep_their_own_sections(item_type: str) -> None:
    """난이도 블록을 갈아끼우다 다른 섹션(한국어 지시문 등)을 날리지 않았는지."""
    body = load_prompt(item_type)

    assert body.rstrip().endswith("Return JSON only."), f"{item_type}.md 끝이 잘렸습니다."
    if item_type != "blank":  # blank 는 서버가 지시문을 만듭니다
        assert "Korean stem" in body, f"{item_type}.md 의 한국어 지시문이 사라졌습니다."


# --------------------------------------------------------------- 동의어 교체


@pytest.mark.parametrize("level", LEVELS)
def test_synonym_swap_receives_difficulty(level: str) -> None:
    prompt = render_prompt_with_base(
        "synonym_swap_system", "synonym_swap", passage="X", difficulty=level, swap_count="3"
    )

    assert "$difficulty" not in prompt
    assert "Word SELECTION" in prompt, "어떤 단어를 고를지 기준이 없습니다."
    assert "REPLACEMENT choice" in prompt, "무엇으로 바꿀지 기준이 없습니다."


def test_synonym_swap_defines_every_level_for_both_axes() -> None:
    body = load_prompt("synonym_swap")
    selection, replacement = body.split("REPLACEMENT choice")

    for level in LEVELS:
        assert f"{level}:" in selection, f"단어 선별 기준에 {level} 이 없습니다."
        assert f"{level}:" in replacement, f"대체어 기준에 {level} 이 없습니다."


def test_wordbook_does_not_get_item_difficulty_spec() -> None:
    """단어장은 난이도 개념을 없앴습니다. 문항용 명세가 섞이면 안 됩니다."""
    prompt = render_prompt_with_base(
        "wordbook_system", "wordbook", passage="X", analysis_json="{}",
        include_phrases="true", max_related="4", candidate_words="a", min_entries="8",
    )

    assert "DIFFICULTY SPECIFICATION" not in prompt


# --------------------------------------------------------- 공통 출제 기법

CRAFT_SECTIONS = ["C1.", "C2.", "C3.", "C4.", "C5.", "C6."]
TRANSFORMATIONS = [
    "scope_narrow", "scope_broad", "polarity_flip", "agent_swap",
    "degree_shift", "causal_reverse", "partial_truth", "keyword_lure",
]


@pytest.mark.parametrize("item_type", ITEM_TYPES)
def test_item_craft_is_included(item_type: str) -> None:
    """오답 레시피·유일성 증명·실패 사례가 빠지면 모델이 알아서 적당히 만듭니다."""
    prompt = _render(item_type, "mid")

    assert "ITEM-WRITING CRAFT" in prompt, f"{item_type}: 공통 출제 기법이 빠졌습니다."


def test_craft_defines_all_sections() -> None:
    craft = load_prompt("item_craft")

    for section in CRAFT_SECTIONS:
        assert section in craft, f"출제 기법 {section} 누락"


def test_craft_defines_named_distractor_recipes() -> None:
    """오답 패턴은 '이름'만 있으면 안 되고 만드는 방법이 있어야 합니다."""
    craft = load_prompt("item_craft")

    for name in TRANSFORMATIONS:
        assert f"`{name}`" in craft, f"오답 변형 {name} 이 정의되지 않았습니다."


@pytest.mark.parametrize("item_type", ITEM_TYPES)
def test_each_type_has_suitability_and_failure_modes(item_type: str) -> None:  # noqa: D103
    """유형별로 '이 지문이 이 유형에 맞는가'와 '무엇이 흔한 실패인가'가 있어야 합니다."""
    body = load_prompt(item_type)

    # 유형마다 이름은 다르지만, "무엇을 대상으로 삼을지" 정하는 절이 반드시 있어야 합니다.
    lowered = body.lower()
    has_selection = any(
        key in lowered for key in ("suitability", "selection", "construction", "design")
    )
    assert has_selection, f"{item_type}.md: 지문 적합성/대상 선정 기준이 없습니다."
    assert "failure modes" in body.lower(), f"{item_type}.md: 실패 사례가 없습니다."


# 선지가 "글"인 유형 — 정답을 변형해 오답을 만듭니다(C2 레시피 적용).
PARAPHRASE_TYPES = ["title", "topic", "summary", "blank", "implicit"]
# 선지가 "위치·표식(①~⑤)"인 유형 — 변형 대신 자체 오류 분류표를 씁니다.
MARKER_TYPES = ["insertion", "order", "irrelevant", "reference", "vocab", "grammar"]


@pytest.mark.parametrize("item_type", PARAPHRASE_TYPES)
def test_paraphrase_types_name_concrete_recipes(item_type: str) -> None:
    """선지가 글인 유형은 공통 변형 중 최소 2개를 자기 유형에 맞게 지정해야 합니다."""
    body = load_prompt(item_type)
    used = [t for t in TRANSFORMATIONS if t in body]

    assert len(used) >= 2, f"{item_type}.md: 오답 레시피가 {used} 뿐입니다."


@pytest.mark.parametrize("item_type", MARKER_TYPES)
def test_marker_types_have_their_own_taxonomy(item_type: str) -> None:
    """선지가 표식인 유형은 '무엇을 근거로 정답이 하나로 정해지는가'를 명시해야 합니다."""
    body = load_prompt(item_type).lower()
    # 유형마다 이름은 달라도 "판별 장치"에 해당하는 목록이 있어야 합니다.
    markers = ["devices", "patterns", "rule families", "cue", "error pattern",
               "antecedent", "construction", "design"]

    assert any(m in body for m in markers), f"{item_type}.md: 판별 근거 분류표가 없습니다."


def test_prompt_assembly_order_is_stable() -> None:
    """규칙 → 기법 → 난이도 → 유형 순서. 뒤가 앞을 구체화하므로 순서가 중요합니다."""
    prompt = _render("title", "hard")

    base = prompt.index("Global output rules")
    craft = prompt.index("ITEM-WRITING CRAFT")
    diff = prompt.index("DIFFICULTY SPECIFICATION")
    body = prompt.index("Korean stem")

    assert base < craft < diff < body


# --------------------------------------------------------- 프롬프트 파일 관리

# 코드가 실제로 로드하는 프롬프트. 새 프롬프트를 만들면 여기에도 등록하세요.
LOADED_PROMPTS = {
    # render_prompt 가 모든 문항에 붙이는 층
    "base_system", "item_craft", "difficulty",
    # 11개 유형 (agent.prompt_name)
    *ITEM_TYPES,
    # 보조 프롬프트 (직접 render_prompt 호출)
    "self_check", "blank_uniqueness_check", "blank_choices_repair",
    # 단어장 / 동의어 교체 (render_prompt_with_base)
    "wordbook_system", "wordbook", "wordbook_expand",
    "synonym_swap_system", "synonym_swap",
}


def _prompt_dir():
    from backend.prompts import loader

    return __import__("pathlib").Path(loader.__file__).parent


def test_no_unused_prompt_files() -> None:
    """쓰지 않는 프롬프트가 남아 있으면 어느 것이 진짜인지 헷갈립니다."""
    on_disk = {p.stem for p in _prompt_dir().glob("*.md")}

    assert not (on_disk - LOADED_PROMPTS), f"사용되지 않는 프롬프트: {sorted(on_disk - LOADED_PROMPTS)}"


def test_every_loaded_prompt_exists() -> None:
    on_disk = {p.stem for p in _prompt_dir().glob("*.md")}

    assert not (LOADED_PROMPTS - on_disk), f"코드가 찾는데 없는 프롬프트: {sorted(LOADED_PROMPTS - on_disk)}"


def test_every_prompt_actually_renders() -> None:
    """변수 치환이 깨진 프롬프트를 배포 전에 잡습니다."""
    context = dict(
        passage="X", difficulty="hard", analysis_json="{}", style="edu_office", seed="",
        explain="true", return_korean_stem="true", choices="5", retry_hint="",
        excluded_spans="", problem_json="{}", check_input_json="{}", repair_input_json="{}",
        include_phrases="true", max_related="4", candidate_words="a", min_entries="8",
        covered_words="a", missing_words="b", swap_count="3",
    )
    for name in [*ITEM_TYPES, "self_check", "blank_uniqueness_check", "blank_choices_repair"]:
        assert render_prompt(name, **context)
    for base, body in [
        ("wordbook_system", "wordbook"),
        ("wordbook_system", "wordbook_expand"),
        ("synonym_swap_system", "synonym_swap"),
    ]:
        assert render_prompt_with_base(base, body, **context)
