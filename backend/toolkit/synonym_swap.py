from __future__ import annotations

import logging
import re

from backend.toolkit.discourse import MARKERS
from backend.toolkit.lexicon import BASIC_WORDS, match_key
from backend.toolkit.text import split_sentences

logger = logging.getLogger(__name__)

# 난이도별 문장당 교체 개수.
# 문장당 1개 미만이면 안 바뀐 문장이 많아 학생이 "봤던 지문"으로 인식합니다.
# 2개를 넘으면 지문이 부자연스러워지고 난이도가 어휘 때문에 엉뚱하게 올라갑니다.
SWAPS_PER_SENTENCE: dict[str, float] = {
    "easy": 0.7,
    "mid": 1.0,
    "hard": 1.5,
}

# 지문이 길어도 과하게 바꾸지 않도록 하는 상한.
MAX_SWAPS = 12

# 연결어는 순서/삽입/무관문장 문제의 정답 근거라 절대 건드리면 안 됩니다.
PROTECTED_PHRASES: frozenset[str] = frozenset(
    marker for group in MARKERS.values() for marker in group
)
# 위 목록의 구성 단어도 단독으로 교체되면 안 됩니다.
PROTECTED_WORDS: frozenset[str] = frozenset(
    word for phrase in PROTECTED_PHRASES for word in phrase.split()
) | {
    "first",
    "second",
    "third",
    "finally",
    "instead",
    "although",
    "though",
    "while",
    "whereas",
    "because",
    "since",
    "unless",
    "if",
    "then",
    "also",
    "not",
    "no",
    "never",
    "always",
}

_WORD_RE = re.compile(r"[A-Za-z][A-Za-z'-]*")


def target_swap_count(passage: str, difficulty: str) -> int:
    """지문 길이와 난이도로 목표 교체 개수를 정합니다."""
    sentences = split_sentences(passage)
    if not sentences:
        return 0
    per_sentence = SWAPS_PER_SENTENCE.get(difficulty, SWAPS_PER_SENTENCE["mid"])
    return max(1, min(MAX_SWAPS, round(len(sentences) * per_sentence)))


def _sentence_start_words(passage: str) -> set[str]:
    """문장 첫 단어 집합. 여기 있는 대문자는 고유명사가 아닐 수 있습니다."""
    starts: set[str] = set()
    for sentence in split_sentences(passage):
        match = _WORD_RE.search(sentence)
        if match:
            starts.add(match.group(0))
    return starts


def rejection_reason(original: str, replacement: str, passage: str) -> str | None:
    """교체를 거부할 이유. 문제없으면 None.

    LLM 제안을 그대로 믿지 않고 서버가 다시 거릅니다.
    """
    original = (original or "").strip()
    replacement = (replacement or "").strip()

    if not original or not replacement:
        return "빈 값"
    if original == replacement:
        return "원본과 동일"
    if not _WORD_RE.fullmatch(original.replace(" ", "a")):
        return "단어 형태가 아님"
    if any(char.isdigit() for char in original + replacement):
        return "숫자 포함"

    # 지문에 정확히 한 번만 나오는 단어만 교체합니다.
    # 여러 번 나오면 "되돌리기"가 원치 않는 곳까지 되돌리게 됩니다.
    occurrences = len(re.findall(rf"\b{re.escape(original)}\b", passage))
    if occurrences == 0:
        return "지문에 없음"
    if occurrences > 1:
        return f"지문에 {occurrences}번 등장(1번만 허용)"

    lowered = original.lower()
    if lowered in PROTECTED_WORDS or lowered in PROTECTED_PHRASES:
        return "연결어/담화표지"
    if lowered in BASIC_WORDS:
        return "기초 어휘"
    if match_key(original) == match_key(replacement):
        return "같은 어근(변화형)"

    # 문장 중간의 대문자 = 고유명사로 보고 건드리지 않습니다.
    if original[0].isupper() and original not in _sentence_start_words(passage):
        return "고유명사로 보임"

    return None


def apply_swaps(passage: str, swaps: list[dict]) -> tuple[str, list[dict]]:
    """검증을 통과한 교체만 지문에 적용합니다.

    Returns: (교체된 지문, 실제 적용된 교체 목록)
    """
    result = passage
    applied: list[dict] = []

    for swap in swaps:
        original = (swap.get("original") or "").strip()
        replacement = (swap.get("replacement") or "").strip()

        reason = rejection_reason(original, replacement, result)
        if reason is not None:
            logger.info("Synonym swap rejected (%s -> %s): %s", original, replacement, reason)
            continue

        pattern = rf"\b{re.escape(original)}\b"
        new_result, count = re.subn(pattern, replacement, result, count=1)
        if count != 1:
            logger.info("Synonym swap skipped (%s): 치환 실패", original)
            continue

        result = new_result
        applied.append(
            {
                "original": original,
                "replacement": replacement,
                "note": (swap.get("note") or "").strip(),
            }
        )

    return result, applied
