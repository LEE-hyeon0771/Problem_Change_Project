from __future__ import annotations

from app.agents.summary_agent import SummaryAgent
from app.schemas.base import Choice, GenerateRequest
from app.schemas.summary import SummaryResponse
from app.toolkit.validators import validate_summary
from tests.fixtures import PASSAGE


def _request() -> GenerateRequest:
    return GenerateRequest(
        passage=PASSAGE,
        difficulty="mid",
        seed=7,
        explain=False,
        return_korean_stem=True,
        debug=False,
    )


def test_summary_agent_normalizes_non_pair_choices(monkeypatch) -> None:
    llm_problem = SummaryResponse(
        passage="Summary Sentence: By using (A), sitcoms made progressive values more (B).",
        question="q",
        choices=[
            Choice(label="①", text="A: humor / B: acceptable"),
            Choice(label="②", text="(A) satire (B) admirable"),
            Choice(label="③", text="authority, irrational"),
            Choice(label="④", text="conflict, foolish"),
            Choice(label="⑤", text="satire, respectable"),
        ],
        answer=Choice(label="①", text="A: humor / B: acceptable"),
        explanation="e",
        meta={},
    )
    agent = SummaryAgent(llm_client=None)
    monkeypatch.setattr(agent, "_try_llm_generate", lambda **kwargs: llm_problem)

    result = agent.generate(_request())

    validate_summary(result)
    assert all(choice.text.startswith("(") and choice.text.endswith(")") for choice in result.choices)
    assert result.passage.startswith(PASSAGE)
    assert "[Summary Sentence]" in result.passage


def test_summary_agent_falls_back_when_llm_choice_is_unrepairable(monkeypatch) -> None:
    llm_problem = SummaryResponse(
        passage="Summary Sentence: By using (A), sitcoms made progressive values more (B).",
        question="q",
        choices=[
            Choice(label="①", text="A: humor / B: acceptable"),
            Choice(label="②", text="not-a-pair"),
            Choice(label="③", text="authority, irrational"),
            Choice(label="④", text="conflict, foolish"),
            Choice(label="⑤", text="satire, respectable"),
        ],
        answer=Choice(label="①", text="A: humor / B: acceptable"),
        explanation="e",
        meta={},
    )
    agent = SummaryAgent(llm_client=None)
    monkeypatch.setattr(agent, "_try_llm_generate", lambda **kwargs: llm_problem)

    result = agent.generate(_request())

    validate_summary(result)
    assert result.passage.startswith(PASSAGE)
    assert result.passage.endswith(
        "The passage explains that (A) shapes decisions and ultimately (B) in daily practice."
    )


def test_summary_agent_removes_duplicated_source_from_summary_sentence(monkeypatch) -> None:
    summary_sentence = "Overall, balancing (A) with periodic review leads to (B)."
    llm_problem = SummaryResponse(
        passage=f"{PASSAGE} {summary_sentence}",
        question="q",
        choices=[
            Choice(label="①", text="(routines, better decisions)"),
            Choice(label="②", text="(habits, blind repetition)"),
            Choice(label="③", text="(comfort, rigid outcomes)"),
            Choice(label="④", text="(evidence, random choices)"),
            Choice(label="⑤", text="(noise, stable errors)"),
        ],
        answer=Choice(label="①", text="(routines, better decisions)"),
        explanation="e",
        meta={},
    )
    agent = SummaryAgent(llm_client=None)
    monkeypatch.setattr(agent, "_try_llm_generate", lambda **kwargs: llm_problem)

    result = agent.generate(_request())

    summary_block = result.passage.split("[Summary Sentence]\n", maxsplit=1)[1]
    assert summary_block == summary_sentence
