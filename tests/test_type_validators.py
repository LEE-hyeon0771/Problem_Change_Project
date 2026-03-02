import pytest

from app.core.errors import GenerationError
from app.schemas.base import Choice
from app.schemas.implicit import ImplicitResponse
from app.schemas.insertion import InsertionResponse
from app.schemas.order import OrderResponse
from app.schemas.summary import SummaryResponse
from app.toolkit.validators import (
    validate_implicit,
    validate_implicit_from_original,
    validate_insertion,
    validate_order,
    validate_summary,
)


def test_validate_summary_accepts_ab_pair_format() -> None:
    choices = [
        Choice(label="①", text="(a, b)"),
        Choice(label="②", text="(c, d)"),
        Choice(label="③", text="(e, f)"),
        Choice(label="④", text="(g, h)"),
        Choice(label="⑤", text="(i, j)"),
    ]
    problem = SummaryResponse(
        passage="One-line summary with (A) and (B).",
        question="q",
        choices=choices,
        answer=choices[0],
        explanation="e",
        meta={},
    )

    validate_summary(problem)


def test_validate_summary_rejects_missing_blanks() -> None:
    choices = [
        Choice(label="①", text="(a, b)"),
        Choice(label="②", text="(c, d)"),
        Choice(label="③", text="(e, f)"),
        Choice(label="④", text="(g, h)"),
        Choice(label="⑤", text="(i, j)"),
    ]
    problem = SummaryResponse(
        passage="One-line summary without required markers.",
        question="q",
        choices=choices,
        answer=choices[0],
        explanation="e",
        meta={},
    )

    with pytest.raises(GenerationError):
        validate_summary(problem)


def test_validate_summary_uses_summary_section_when_header_exists() -> None:
    choices = [
        Choice(label="①", text="(a, b)"),
        Choice(label="②", text="(c, d)"),
        Choice(label="③", text="(e, f)"),
        Choice(label="④", text="(g, h)"),
        Choice(label="⑤", text="(i, j)"),
    ]
    problem = SummaryResponse(
        passage=(
            "Body text with labels (A) and (B) that should be ignored.\n\n"
            "[Summary Sentence]\nOne-line summary with (A) and (B)."
        ),
        question="q",
        choices=choices,
        answer=choices[0],
        explanation="e",
        meta={},
    )

    validate_summary(problem)


def test_validate_order_rejects_non_permutation_choice() -> None:
    choices = [
        Choice(label="①", text="A-B-C"),
        Choice(label="②", text="A-C-B"),
        Choice(label="③", text="B-A-C"),
        Choice(label="④", text="B-C-A"),
        Choice(label="⑤", text="A-A-B"),
    ]
    problem = OrderResponse(
        passage="Lead text.\n\n(A) Block A.\n\n(B) Block B.\n\n(C) Block C.",
        question="q",
        choices=choices,
        answer=choices[0],
        explanation="e",
        meta={},
    )

    with pytest.raises(GenerationError):
        validate_order(problem)


def test_validate_insertion_requires_slot_labels_and_markers() -> None:
    choices = [
        Choice(label="①", text="①"),
        Choice(label="②", text="②"),
        Choice(label="③", text="③"),
        Choice(label="④", text="④"),
        Choice(label="⑤", text="⑤"),
    ]
    problem = InsertionResponse(
        passage="S1 ① S2 ② S3 ③ S4 ④ S5 ⑤ S6",
        question="q",
        choices=choices,
        answer=choices[2],
        explanation="e",
        meta={"answer_position": 3},
    )

    validate_insertion(problem)


def test_validate_implicit_accepts_single_underlined_span() -> None:
    choices = [
        Choice(label="①", text="A"),
        Choice(label="②", text="B"),
        Choice(label="③", text="C"),
        Choice(label="④", text="D"),
        Choice(label="⑤", text="E"),
    ]
    problem = ImplicitResponse(
        passage="The claim [[1]]in this way[[/1]] helps readers follow the logic.",
        question="q",
        choices=choices,
        answer=choices[0],
        explanation="e",
        meta={},
    )

    validate_implicit(problem)


def test_validate_implicit_from_original_checks_restore() -> None:
    original = "The claim in this way helps readers follow the logic."
    choices = [
        Choice(label="①", text="A"),
        Choice(label="②", text="B"),
        Choice(label="③", text="C"),
        Choice(label="④", text="D"),
        Choice(label="⑤", text="E"),
    ]
    problem = ImplicitResponse(
        passage="The claim [[1]]in this way[[/1]] helps readers follow the logic.",
        question="q",
        choices=choices,
        answer=choices[0],
        explanation="e",
        meta={},
    )

    validate_implicit_from_original(problem, original)
