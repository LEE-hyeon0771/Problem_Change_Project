from backend.toolkit.text import normalize_text


def test_normalize_text_strips_html_underlines() -> None:
    raw = (
        "Despite the difference between the past and the future, "
        "(a)<u>the past</u> has always been influenced. "
        "Revolutionaries have always looked to (b)<u>it</u>."
    )

    normalized = normalize_text(raw)

    assert "<u>" not in normalized
    assert "</u>" not in normalized
    assert "(a)the past" in normalized
    assert "(b)it" in normalized


def test_normalize_text_strips_generic_html_tags() -> None:
    raw = "A <span class='k'>useful</span> point.<br>Another line."

    normalized = normalize_text(raw)

    assert "<span" not in normalized
    assert "</span>" not in normalized
    assert "<br>" not in normalized
    assert "useful" in normalized
    assert "Another line." in normalized


def test_hard_wrapped_lines_are_joined() -> None:
    """PDF/교재에서 복사한 지문은 문장 중간에 줄바꿈이 박혀 옵니다.

    이걸 남겨 두면 LLM이 돌려준 스팬이 원문과 매칭되지 않아
    빈칸/함축 생성이 통째로 로컬 폴백으로 떨어집니다.
    """
    raw = "Managers of natural resources typically face market\nincentives that provide rewards."

    assert normalize_text(raw) == "Managers of natural resources typically face market incentives that provide rewards."


def test_paragraph_breaks_survive() -> None:
    raw = "First paragraph here.\n\nSecond paragraph here."

    assert normalize_text(raw) == "First paragraph here.\n\nSecond paragraph here."


def test_wrapped_span_is_findable_after_normalize() -> None:
    raw = "Managers face market\nincentives that reward exploitation."
    span = "market incentives that reward exploitation"

    assert span not in raw, "줄바꿈 때문에 원본에서는 못 찾는 것이 정상입니다."
    assert span in normalize_text(raw), "정규화 후에는 찾을 수 있어야 합니다."
