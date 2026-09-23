import pytest

from backend.agents.synonym_swapper import SUPPORTED_TYPES, SynonymSwapper
from backend.core.config import Settings
from backend.llm.clients import MockLLMClient
from backend.toolkit.synonym_swap import (
    MAX_SWAPS,
    apply_swaps,
    rejection_reason,
    target_swap_count,
)

PASSAGE = (
    "Managers of natural resources typically face market incentives that provide financial "
    "rewards for exploitation. However, owners of forest lands have a market incentive to cut "
    "down trees rather than manage the forest for carbon capture and flood protection. "
    "These ecosystem services provide no financial benefits, and thus are unlikely to "
    "influence management decisions."
)

# 엔드포인트를 태우는 테스트용. `BaseAgent.preprocess` 가 60단어 이상을 요구합니다.
LONG_PASSAGE = PASSAGE + (
    " Public policy can correct this imbalance by rewarding landowners who preserve standing "
    "forests, so that private choices finally align with broader social value over time."
)


# ------------------------------------------------------------------ 교체 개수


def test_swap_count_scales_with_difficulty() -> None:
    easy = target_swap_count(PASSAGE, "easy")
    mid = target_swap_count(PASSAGE, "mid")
    hard = target_swap_count(PASSAGE, "hard")

    assert easy < mid < hard


def test_swap_count_is_capped() -> None:
    long_passage = "This sentence introduces a distinct academic concept. " * 100

    assert target_swap_count(long_passage, "hard") <= MAX_SWAPS


def test_swap_count_is_zero_for_empty_passage() -> None:
    assert target_swap_count("", "mid") == 0


def test_unknown_difficulty_falls_back_to_mid() -> None:
    assert target_swap_count(PASSAGE, "nonsense") == target_swap_count(PASSAGE, "mid")


# ------------------------------------------------------------------ 거부 규칙


@pytest.mark.parametrize(
    "original, replacement, expected",
    [
        ("However", "Nevertheless", "연결어/담화표지"),
        ("thus", "therefore", "연결어/담화표지"),
        ("have", "possess", "기초 어휘"),
        ("Managers", "Supervisors", None),  # 문장 첫 단어라 고유명사가 아님
        ("typically", "typically", "원본과 동일"),
        ("nonexistent", "whatever", "지문에 없음"),
        ("market", "commercial", "지문에 2번 등장(1번만 허용)"),
        ("exploitation", "exploitations", "같은 어근(변화형)"),
        ("typically", "usu4lly", "숫자 포함"),
        ("typically", "", "빈 값"),
    ],
)
def test_rejection_rules(original: str, replacement: str, expected: str | None) -> None:
    assert rejection_reason(original, replacement, PASSAGE) == expected


def test_repeated_word_is_rejected() -> None:
    """여러 번 나오는 단어를 바꾸면 '되돌리기'가 엉뚱한 곳까지 되돌립니다."""
    assert PASSAGE.count("market") > 1
    assert rejection_reason("market", "commercial", PASSAGE) is not None


def test_proper_noun_in_mid_sentence_is_rejected() -> None:
    passage = "Researchers at Stanford studied the problem carefully."

    assert rejection_reason("Stanford", "Harvard", passage) == "고유명사로 보임"


# ------------------------------------------------------------------ 적용


def test_apply_swaps_only_keeps_valid_ones() -> None:
    swapped, applied = apply_swaps(
        PASSAGE,
        [
            {"original": "typically", "replacement": "usually", "note": "부사"},
            {"original": "However", "replacement": "Nevertheless"},  # 연결어 → 거부
            {"original": "ghost", "replacement": "phantom"},  # 지문에 없음 → 거부
        ],
    )

    assert [item["original"] for item in applied] == ["typically"]
    assert "usually" in swapped
    assert "typically" not in swapped
    assert "However" in swapped, "연결어가 보존되어야 합니다."


def test_apply_swaps_preserves_everything_else() -> None:
    swapped, applied = apply_swaps(PASSAGE, [{"original": "typically", "replacement": "usually"}])

    # 교체한 단어를 되돌리면 원문과 정확히 같아야 합니다(되돌리기 기능의 근거).
    assert swapped.replace("usually", "typically") == PASSAGE


def test_apply_swaps_with_nothing_valid_returns_original() -> None:
    swapped, applied = apply_swaps(PASSAGE, [{"original": "However", "replacement": "Yet"}])

    assert swapped == PASSAGE
    assert applied == []


def test_word_boundary_is_respected() -> None:
    """'face' 를 바꿔도 'surface' / 'interface' 는 건드리면 안 됩니다."""
    passage = "The surface layer will face pressure from the interface."
    swapped, applied = apply_swaps(passage, [{"original": "face", "replacement": "confront"}])

    assert [item["original"] for item in applied] == ["face"]
    assert "will confront pressure" in swapped
    assert "surface" in swapped and "interface" in swapped, "부분 문자열이 함께 바뀌면 안 됩니다."


def test_connective_component_words_are_protected() -> None:
    """'as a result' 의 'result' 를 바꾸면 'as a outcome' 이 되어 문장이 깨집니다."""
    passage = "The policy failed. As a result, the outcome was poor for local communities."

    assert rejection_reason("result", "outcome", passage) == "연결어/담화표지"


# ------------------------------------------------------- 유형별 적용 여부


def _swapper(payload: dict | None = None) -> SynonymSwapper:
    settings = Settings(APP_ENV="test", USE_LLM_GENERATION=True, GOOGLE_API_KEY="k")
    return SynonymSwapper(
        llm_client=MockLLMClient(
            settings=settings,
            payload=payload
            if payload is not None
            else {"swaps": [{"original": "typically", "replacement": "usually", "note": ""}]},
        ),
        settings=settings,
    )


@pytest.mark.parametrize("problem_type", sorted(SUPPORTED_TYPES))
def test_supported_types_get_swapped(problem_type: str) -> None:
    swapped, applied = _swapper().swap(passage=PASSAGE, difficulty="mid", problem_type=problem_type)

    assert applied, f"{problem_type} 은(는) 교체 대상이어야 합니다."
    assert swapped != PASSAGE


@pytest.mark.parametrize("problem_type", ["vocab", "grammar", "insertion", "order", "irrelevant"])
def test_unsupported_types_are_untouched(problem_type: str) -> None:
    """어휘·어법은 정답 유일성이 깨지고, 삽입·순서·무관은 연결어 단서가 흔들립니다."""
    swapped, applied = _swapper().swap(passage=PASSAGE, difficulty="mid", problem_type=problem_type)

    assert swapped == PASSAGE
    assert applied == []


def test_swap_failure_does_not_break_generation() -> None:
    settings = Settings(APP_ENV="test", USE_LLM_GENERATION=True, GOOGLE_API_KEY="k")

    class BrokenClient(MockLLMClient):
        def generate_json(self, prompt: str, schema: dict | None = None, label: str = "-") -> dict:
            raise RuntimeError("LLM 장애")

    swapper = SynonymSwapper(llm_client=BrokenClient(settings=settings), settings=settings)
    swapped, applied = swapper.swap(passage=PASSAGE, difficulty="mid", problem_type="title")

    assert swapped == PASSAGE
    assert applied == []


def test_swap_is_skipped_when_llm_disabled() -> None:
    settings = Settings(APP_ENV="test", USE_LLM_GENERATION=False)
    swapper = SynonymSwapper(llm_client=MockLLMClient(settings=settings), settings=settings)

    swapped, applied = swapper.swap(passage=PASSAGE, difficulty="mid", problem_type="title")

    assert swapped == PASSAGE
    assert applied == []


# --------------------------------------------- 스트리밍 경로 (UI 가 쓰는 경로)


def _swap_via(url: str, monkeypatch) -> dict:
    """주어진 엔드포인트로 생성하고 최종 결과를 돌려줍니다."""
    import json as _json

    from fastapi.testclient import TestClient

    import backend.main as main_module

    from backend.apis import deps
    from backend.agents.synonym_swapper import SynonymSwapper

    settings = Settings(APP_ENV="test", USE_LLM_GENERATION=True, GOOGLE_API_KEY="k")
    swapper = SynonymSwapper(
        llm_client=MockLLMClient(
            settings=settings,
            payload={"swaps": [{"original": "typically", "replacement": "usually", "note": ""}]},
        ),
        settings=settings,
    )
    monkeypatch.setattr(deps, "synonym_swapper", swapper)

    client = TestClient(main_module.app)
    # 에이전트의 60단어 하한을 넘겨야 생성까지 갑니다.
    payload = {"passage": LONG_PASSAGE, "difficulty": "mid", "synonym_swap": True}

    if "stream" in url:
        with client.stream("POST", url, json=payload) as response:
            assert response.status_code == 200
            body = "".join(response.iter_text())
        for block in body.strip().split("\n\n"):
            if block.startswith("event: done"):
                return _json.loads(block.split("data: ", 1)[1])
        raise AssertionError("done 이벤트가 없습니다.")

    response = client.post(url, json=payload)
    assert response.status_code == 200
    return response.json()


def test_streaming_path_applies_synonym_swap(monkeypatch) -> None:
    """UI 는 /stream/ 경로만 씁니다.

    한때 `_stream_agent` 가 `_run_agent` 를 우회해 `agent.generate()` 를 직접 불러서,
    화면에서 체크박스를 켜도 교체가 조용히 무시됐습니다. 그 회귀를 막습니다.
    """
    result = _swap_via("/api/v1/stream/title", monkeypatch)

    assert "usually" in result["passage"], "스트리밍 경로에서 동의어 교체가 적용되지 않았습니다."
    assert "typically" not in result["passage"]
    assert result["meta"]["synonym_swap"]["count"] == 1


def test_both_paths_behave_the_same(monkeypatch) -> None:
    streamed = _swap_via("/api/v1/stream/title", monkeypatch)
    plain = _swap_via("/api/v1/title", monkeypatch)

    assert streamed["passage"] == plain["passage"]
    assert streamed["meta"]["synonym_swap"] == plain["meta"]["synonym_swap"]
