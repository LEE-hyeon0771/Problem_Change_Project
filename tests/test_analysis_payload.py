"""프롬프트에 실리는 분석 페이로드 검증.

`analysis_json` 은 12개 프롬프트 전부에 통째로 들어갑니다.
여기에 지문 복제본이 섞이면 호출마다 같은 내용을 두 번 보내게 됩니다.
"""

import json

from backend.agents.title_agent import TitleAgent
from backend.schemas.base import GenerateRequest
from tests.fixtures import PASSAGE


def _analysis():
    agent = TitleAgent()
    passage = agent.preprocess(PASSAGE)
    return agent, passage, agent.analyze(passage)


def test_prompt_payload_drops_the_duplicated_passage() -> None:
    _, passage, analysis = _analysis()

    # 원본에는 지문이 문장 단위로 그대로 들어 있습니다.
    raw_sentences = [s for p in analysis.model_dump()["paragraphs"] for s in p["sentences"]]
    assert " ".join(raw_sentences).strip() == passage.strip(), "전제: sentences 는 지문의 복제본"

    payload = analysis.to_prompt_payload()

    for paragraph in payload["paragraphs"]:
        assert "sentences" not in paragraph, "지문 복제본이 프롬프트로 다시 나가면 안 됩니다."


def test_prompt_payload_keeps_markers_and_function() -> None:
    """grammar/order/reference/vocab 프롬프트가 markers 를 참조합니다.

    `paragraphs` 를 통째로 빼면 이 정보까지 날아갑니다.
    """
    _, _, analysis = _analysis()

    payload = analysis.to_prompt_payload()

    assert payload["paragraphs"], "문단 정보 자체는 남아야 합니다."
    for paragraph in payload["paragraphs"]:
        assert set(paragraph) == {"function", "markers"}

    assert any(p["markers"] for p in payload["paragraphs"]), "담화표지가 비면 안 됩니다."


def test_prompt_payload_keeps_top_level_fields() -> None:
    _, _, analysis = _analysis()

    payload = analysis.to_prompt_payload()

    for key in ("topic", "thesis_candidates", "keywords", "coreference_candidates"):
        assert key in payload


def test_prompt_payload_is_smaller_than_full_dump() -> None:
    _, _, analysis = _analysis()

    full = json.dumps(analysis.model_dump(), ensure_ascii=False)
    slim = json.dumps(analysis.to_prompt_payload(), ensure_ascii=False)

    assert len(slim) < len(full) * 0.6, "중복 제거 효과가 사라졌습니다."


def test_agent_context_uses_the_slim_payload() -> None:
    """에이전트가 실수로 model_dump() 로 되돌아가는 것을 막습니다."""
    agent, passage, analysis = _analysis()

    context = agent._prompt_context(GenerateRequest(passage=PASSAGE), passage, analysis)

    assert "sentences" not in context["analysis_json"]


def test_wordbook_agent_context_uses_the_slim_payload() -> None:
    from backend.agents.wordbook_agent import WordbookAgent
    from backend.schemas.wordbook import WordbookRequest

    agent = WordbookAgent()
    passage = agent.preprocess(PASSAGE)
    analysis = agent.analyze(passage)

    context = agent._wordbook_context(WordbookRequest(passage=PASSAGE), passage, analysis, ["evidence"])

    assert "sentences" not in context["analysis_json"]
