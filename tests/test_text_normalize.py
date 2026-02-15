from app.toolkit.text import normalize_text


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
