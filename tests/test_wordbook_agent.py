from fastapi.testclient import TestClient

from backend.agents.wordbook_agent import WordbookAgent
from backend.core.config import Settings
from backend.llm.clients import MockLLMClient
from backend.main import app
from backend.schemas.wordbook import WordbookRequest
from backend.toolkit.lexicon import content_word_candidates
from tests.fixtures import PASSAGE


client = TestClient(app)


def _llm_settings() -> Settings:
    return Settings(
        APP_ENV="test",
        USE_LLM_GENERATION=True,
        GOOGLE_API_KEY="test-key",
        ENABLE_PROBLEM_PERSISTENCE=False,
        ENABLE_DB_PERSISTENCE=False,
    )


def _entry(headword: str, *, senses: list[dict] | None = None) -> dict:
    return {
        "headword": headword,
        "surface_form": headword,
        "importance": "core",
        "cefr": "B2",
        "passage_meaning_ko": f"{headword}의 지문 내 뜻",
        "example_sentence": "",
        "senses": senses
        if senses is not None
        else [
            {
                "pos": "noun",
                "meaning_ko": f"{headword} 뜻",
                "meaning_en": f"definition of {headword}",
                "synonyms": [{"word": "alpha", "meaning_ko": "동의어", "pos": "noun"}],
                "antonyms": [],
            }
        ],
    }


def test_wordbook_endpoint_returns_candidates_without_llm() -> None:
    response = client.post("/api/v1/wordbook", json={"passage": PASSAGE})

    assert response.status_code == 200
    data = response.json()
    assert data["type"] == "wordbook"
    assert data["meta"]["generation_mode"] == "local_fallback"
    assert data["meta"]["notice"]
    assert len(data["entries"]) == data["meta"]["candidate_count"] > 0


def test_wordbook_endpoint_rejects_short_passage() -> None:
    response = client.post("/api/v1/wordbook", json={"passage": "Too short."})

    assert response.status_code == 422


def test_agent_fills_pos_ko_and_example_sentence() -> None:
    settings = _llm_settings()
    agent = WordbookAgent(
        llm_client=MockLLMClient(settings=settings, payload={"entries": [_entry("cognitive")]}),
        settings=settings,
    )

    result = agent.generate(WordbookRequest(passage=PASSAGE))

    entry = result.entries[0]
    assert entry.senses[0].pos_ko == "명사"
    # 프롬프트가 example_sentence를 비워 보내도 서버가 지문 문장으로 채웁니다.
    assert "cognitive" in entry.example_sentence


def test_agent_deduplicates_repeated_headwords() -> None:
    settings = _llm_settings()
    payload = {"entries": [_entry("evidence"), _entry("evidence"), _entry("outcomes")]}
    agent = WordbookAgent(llm_client=MockLLMClient(settings=settings, payload=payload), settings=settings)

    result = agent.generate(WordbookRequest(passage=PASSAGE))

    headwords = [entry.headword for entry in result.entries]
    assert headwords.count("evidence") == 1
    assert "outcomes" in headwords


def test_agent_reports_uncovered_candidates() -> None:
    settings = _llm_settings()
    # 후보 대비 한 항목만 돌려주면 나머지는 보강 패스 후에도 미커버로 남습니다.
    agent = WordbookAgent(
        llm_client=MockLLMClient(settings=settings, payload={"entries": [_entry("cognitive")]}),
        settings=settings,
    )

    result = agent.generate(WordbookRequest(passage=PASSAGE))

    candidates = content_word_candidates(PASSAGE)
    assert result.meta["generation_mode"] == "llm"
    assert result.meta["candidate_count"] == len(candidates)
    assert len(result.meta["uncovered_candidates"]) == len(candidates) - 1


def test_agent_falls_back_when_llm_returns_no_entries() -> None:
    settings = _llm_settings()
    agent = WordbookAgent(llm_client=MockLLMClient(settings=settings, payload={"entries": []}), settings=settings)

    result = agent.generate(WordbookRequest(passage=PASSAGE))

    assert result.meta["generation_mode"] == "local_fallback"
    assert result.entries
