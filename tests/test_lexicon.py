from backend.toolkit.lexicon import (
    BASIC_WORDS,
    content_word_candidates,
    lemma,
    match_key,
    missing_candidates,
)
from tests.fixtures import PASSAGE


def test_lemma_groups_inflected_forms() -> None:
    assert lemma("habits") == "habit"
    assert lemma("studies") == "study"
    assert lemma("repeated") == "repeat"
    assert lemma("processes") == "process"
    assert lemma("planned") == "plan"
    assert lemma("ones") == "one"


def test_lemma_keeps_double_s_words_intact() -> None:
    assert lemma("less") == "less"
    assert lemma("process") == "process"


def test_match_key_unifies_silent_e_stems() -> None:
    # -ing/-ed 제거 시 묵음 e가 함께 날아가므로 대조 키는 같아야 합니다.
    assert match_key("reduce") == match_key("reducing")
    assert match_key("revise") == match_key("revising")


def test_candidates_exclude_basic_vocabulary() -> None:
    candidates = content_word_candidates(PASSAGE)

    assert candidates, "지문에서 후보를 하나도 뽑지 못했습니다."
    for word in candidates:
        assert word not in BASIC_WORDS
        assert lemma(word) not in BASIC_WORDS


def test_candidates_are_deduplicated_by_lemma() -> None:
    candidates = content_word_candidates("Routines and a routine both matter when routines repeat. " * 3)
    keys = [match_key(word) for word in candidates]

    assert len(keys) == len(set(keys))


def test_candidates_cover_core_passage_vocabulary() -> None:
    candidates = {match_key(word) for word in content_word_candidates(PASSAGE)}

    for expected in ["cognitive", "assumptions", "evidence", "outcomes", "periodic"]:
        assert match_key(expected) in candidates


def test_missing_candidates_reports_uncovered_words() -> None:
    candidates = ["cognitive", "assumptions", "evidence"]

    assert missing_candidates(candidates, ["cognitive", "assumption"]) == ["evidence"]
    assert missing_candidates(candidates, []) == candidates
    assert missing_candidates(candidates, ["cognitive", "assumptions", "evidence"]) == []


def test_missing_candidates_treats_phrase_parts_as_covered() -> None:
    # "reflect on" 같은 구 표제어는 구성 단어를 커버한 것으로 봅니다.
    assert missing_candidates(["reflecting"], ["reflect on"]) == []
