from __future__ import annotations


def render_blank(passage: str, span: str) -> str:
    return passage.replace(span, "_____", 1)


def render_insertion_slots(sentences: list[str], slot_indices: list[int]) -> str:
    labels = ["①", "②", "③", "④", "⑤"]
    slot_map = {idx: labels[i] for i, idx in enumerate(slot_indices)}

    rendered: list[str] = []
    for i, sentence in enumerate(sentences):
        rendered.append(sentence)
        boundary = i + 1
        if boundary in slot_map:
            rendered.append(slot_map[boundary])
    return " ".join(rendered)


def render_order_blocks(intro: str, block_a: str, block_b: str, block_c: str) -> str:
    return f"{intro}\n\n(A) {block_a}\n\n(B) {block_b}\n\n(C) {block_c}"


def render_underlines(passage: str, targets: list[tuple[str, str]]) -> str:
    rendered = passage
    for label, token in targets:
        marker = f"[[{label}]]{token}[[/{label}]]"
        rendered = rendered.replace(token, marker, 1)
    return rendered
