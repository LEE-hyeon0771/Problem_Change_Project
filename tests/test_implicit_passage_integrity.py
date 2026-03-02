from app.agents.implicit_agent import ImplicitAgent
from app.schemas.base import GenerateRequest
from app.toolkit.validators import validate_implicit_from_original
from tests.fixtures import PASSAGE


def test_implicit_passage_integrity_local_fallback() -> None:
    agent = ImplicitAgent(llm_client=None)
    request = GenerateRequest(
        passage=PASSAGE,
        difficulty="mid",
        seed=17,
        return_korean_stem=True,
        explain=True,
        debug=False,
    )

    problem = agent.generate(request)

    assert problem.type == "implicit"
    assert problem.passage.count("[[1]]") == 1
    assert problem.passage.count("[[/1]]") == 1
    assert "밑줄 친 부분" in problem.question
    assert str(problem.meta.get("underlined_span", "")) in problem.question
    assert all(not choice.text.strip().startswith(("①", "②", "③", "④", "⑤")) for choice in problem.choices)
    validate_implicit_from_original(problem, PASSAGE)


def test_implicit_choice_normalization_removes_leading_labels() -> None:
    agent = ImplicitAgent(llm_client=None)
    choices = agent._build_choices(
        [
            "① physically reduced in size",
            "2) socially undermined and humiliated",
            "③ directly praised by the audience",
            "(4) persuaded by formal logic",
            "⑤ selected for a starring role",
        ]
    )

    assert choices[0].text == "physically reduced in size"
    assert choices[1].text == "socially undermined and humiliated"
    assert choices[2].text == "directly praised by the audience"
    assert choices[3].text == "persuaded by formal logic"
    assert choices[4].text == "selected for a starring role"
