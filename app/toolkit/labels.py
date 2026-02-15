def choice_labels(n: int = 5) -> list[str]:
    base = ["①", "②", "③", "④", "⑤"]
    if n <= len(base):
        return base[:n]
    return [str(i + 1) for i in range(n)]


def slot_labels(n: int = 5) -> list[str]:
    return choice_labels(n)


def ref_labels(n: int = 5) -> list[str]:
    base = ["(1)", "(2)", "(3)", "(4)", "(5)"]
    if n <= len(base):
        return base[:n]
    return [f"({i + 1})" for i in range(n)]
