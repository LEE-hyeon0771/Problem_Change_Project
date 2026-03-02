from app.schemas.base import Choice
from app.schemas.grammar import GrammarResponse
from app.schemas.vocab import VocabResponse
from app.toolkit.vocab_grammar_normalize import normalize_vocab_grammar_problem


def _choices_with_alpha() -> list[Choice]:
    labels = ["(a)", "(b)", "(c)", "(d)", "(e)"]
    return [Choice(label=label, text=label) for label in labels]


def test_normalize_vocab_problem_converts_alpha_html_markers() -> None:
    problem = VocabResponse(
        passage=(
            "(a)<u>alpha</u> text (b)<u>beta</u> text (c)<u>gamma</u> "
            "text (d)<u>delta</u> text (e)<u>epsilon</u>."
        ),
        question="q",
        choices=_choices_with_alpha(),
        answer=Choice(label="(c)", text="(c)"),
        explanation="e",
        meta={},
    )

    normalized = normalize_vocab_grammar_problem(problem)

    assert normalized.choices[0].label == "①"
    assert normalized.choices[4].label == "⑤"
    assert normalized.answer.label == "③"
    assert "[[1]]alpha[[/1]]" in normalized.passage
    assert "[[5]]epsilon[[/5]]" in normalized.passage
    assert "(a)" not in normalized.passage
    assert "<u>" not in normalized.passage
    assert "</u>" not in normalized.passage


def test_normalize_grammar_problem_converts_alpha_bracket_markers() -> None:
    problem = GrammarResponse(
        passage="[[a]]shows[[/a]] [[b]]are[[/b]] [[c]]have[[/c]] [[d]]consider[[/d]] [[e]]remains[[/e]].",
        question="q",
        choices=_choices_with_alpha(),
        answer=Choice(label="(d)", text="(d)"),
        explanation="e",
        meta={},
    )

    normalized = normalize_vocab_grammar_problem(problem)

    assert normalized.answer.label == "④"
    assert "[[1]]shows[[/1]]" in normalized.passage
    assert "[[5]]remains[[/5]]" in normalized.passage
