from __future__ import annotations

import re
from html import unescape


_WORD_RE = re.compile(r"[A-Za-z']+")
_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")
_HTML_BREAK_TAG_RE = re.compile(r"<\s*br\s*/?\s*>", flags=re.IGNORECASE)
_HTML_BLOCK_TAG_RE = re.compile(r"</?\s*(p|div|li|ul|ol|blockquote|h[1-6])\b[^>]*>", flags=re.IGNORECASE)
_HTML_INLINE_TAG_RE = re.compile(r"</?\s*(u|b|i|em|strong|span|mark|sup|sub)\b[^>]*>", flags=re.IGNORECASE)
_GENERIC_HTML_TAG_RE = re.compile(r"</?\s*[a-z][a-z0-9:-]*\b[^>]*>", flags=re.IGNORECASE)


def normalize_text(text: str) -> str:
    # Some users paste passages with HTML markup (e.g. <u>...</u>).
    # Normalize to plain text before any downstream analysis/generation.
    text = unescape(text)
    text = _HTML_BREAK_TAG_RE.sub("\n", text)
    text = _HTML_BLOCK_TAG_RE.sub("\n", text)
    text = _HTML_INLINE_TAG_RE.sub("", text)
    text = _GENERIC_HTML_TAG_RE.sub("", text)

    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[\t ]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def word_count(text: str) -> int:
    return len(_WORD_RE.findall(text))


def split_paragraphs(text: str) -> list[str]:
    return [p.strip() for p in text.split("\n\n") if p.strip()]


def split_sentences(text: str) -> list[str]:
    raw = _SENTENCE_SPLIT_RE.split(text.strip())
    out = [s.strip() for s in raw if s.strip()]
    if out:
        return out
    return [text.strip()] if text.strip() else []


def ensure_min_sentences(text: str, min_sentences: int = 7) -> list[str]:
    sentences = split_sentences(text)
    if len(sentences) >= min_sentences:
        return sentences

    words = text.split()
    if not words:
        return []

    chunk_size = max(8, len(words) // min_sentences)
    chunks = []
    for idx in range(0, len(words), chunk_size):
        chunk = " ".join(words[idx : idx + chunk_size]).strip()
        if chunk and chunk[-1] not in ".!?":
            chunk += "."
        chunks.append(chunk)
    return chunks


def truncate_if_too_long(text: str, max_chars: int = 2500) -> str:
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 3].rstrip() + "..."


def normalize_newlines_only(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n")


def replace_nth(text: str, target: str, replacement: str, occurrence: int = 1) -> str:
    if occurrence < 1:
        raise ValueError("occurrence must be >= 1")
    if not target:
        raise ValueError("target must not be empty")

    search_start = 0
    idx = -1
    for _ in range(occurrence):
        idx = text.find(target, search_start)
        if idx < 0:
            raise ValueError("target occurrence was not found")
        search_start = idx + len(target)

    return text[:idx] + replacement + text[idx + len(target) :]


def assert_exactly_one_blank(text: str) -> None:
    if text.count("_____") != 1:
        raise ValueError("text must include exactly one blank token")


def assert_span_exists(text: str, target: str) -> None:
    if not target:
        raise ValueError("target span must not be empty")
    if target not in text:
        raise ValueError("target span does not exist in text")
