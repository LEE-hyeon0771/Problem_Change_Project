from app.schemas.base import Choice
from app.schemas.summary import SummaryResponse


def test_problem_response_preserves_choice_objects() -> None:
    choices = [
        Choice(label="①", text="(alpha, beta)"),
        Choice(label="②", text="(gamma, delta)"),
        Choice(label="③", text="(epsilon, zeta)"),
        Choice(label="④", text="(eta, theta)"),
        Choice(label="⑤", text="(iota, kappa)"),
    ]

    problem = SummaryResponse(
        type="summary",
        passage="Summary with (A) and (B).",
        question="q",
        choices=choices,
        answer=choices[2],
        explanation="e",
        meta={},
    )

    assert problem.choices[0].text == "(alpha, beta)"
    assert problem.choices[2].text == "(epsilon, zeta)"
    assert problem.answer.label == "③"
    assert problem.answer.text == "(epsilon, zeta)"
