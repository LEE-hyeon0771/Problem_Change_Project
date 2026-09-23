from __future__ import annotations

import re

_TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z'-]*")

# 학습자가 이미 아는 것으로 보는 기초 어휘(기능어 + 최기초 내용어).
# 핵심단어장 후보에서 제외해 "core word"만 남기는 용도입니다.
BASIC_WORDS: frozenset[str] = frozenset(
    """
    a an the this that these those there here it its itself they them their theirs
    he him his she her hers we us our ours you your yours i me my mine who whom whose
    which what where when why how all any both each few more most other some such
    no nor not only own same so than too very s t can will just don should now
    and or but if then else because as until while of at by for with about against
    between into through during before after above below to from up down in out on off
    over under again further once
    am is are was were be been being have has had having do does did doing
    would could shall might must may let
    one two three four five six seven eight nine ten first second third last next
    good bad big small large little long short high low new old young
    man woman people person child children friend family home house school work job
    day night year month week time hour minute today tomorrow yesterday
    way thing things part place world life water food money book word words name
    make made makes making take takes took taken get gets got give gives gave given
    go goes went gone come comes came see sees saw seen look looks looked
    know knows knew known think thinks thought want wants wanted need needs needed
    use uses used using find finds found tell tells told say says said ask asks asked
    feel feels felt try tries tried call calls called keep keeps kept put puts
    mean means meant leave leaves left work works worked seem seems seemed
    help helps helped show shows showed shown turn turns turned start starts started
    talk talks talked play plays played run runs ran move moves moved like likes liked
    live lives lived believe believes believed hold holds held bring brings brought
    happen happens happened write writes wrote written sit sits sat stand stands stood
    lose loses lost pay pays paid meet meets met include includes included
    continue continues continued set sets learn learns learned change changes changed
    lead leads led understand understands understood watch watches watched follow follows
    stop stops stopped create creates created speak speaks spoke read reads
    spend spends spent grow grows grew open opens opened walk walks walked win wins won
    offer offers offered remember remembers remembered love loves loved
    consider considers considered appear appears appeared buy buys bought wait waits
    serve serves served die dies died send sends sent build builds built stay stays
    fall falls fell cut cuts reach reaches reached kill kills killed remain remains
    also even still yet however therefore thus about many much every something anything
    nothing everything someone anyone everyone nobody always never often sometimes
    again ever back down out up around away together almost enough quite rather
    really actually probably maybe perhaps well better best worse worst
    less least simple simply easy easily hard hardly sure
    able another others sorry
    """.split()
)

_IRREGULAR_LEMMA: dict[str, str] = {
    "children": "child",
    "people": "person",
    "men": "man",
    "women": "woman",
    "feet": "foot",
    "teeth": "tooth",
    "mice": "mouse",
    "criteria": "criterion",
    "phenomena": "phenomenon",
    "analyses": "analysis",
    "hypotheses": "hypothesis",
    "theses": "thesis",
    "data": "datum",
}


def lemma(word: str) -> str:
    """형태소 분석기 없이 어미만 벗겨내는 얕은 표제어 추출.

    핵심단어 후보를 묶는 용도이므로 정확한 원형이 아니어도 됩니다.
    같은 단어의 변화형이 중복 후보로 잡히지 않게 하는 것이 목적입니다.
    """
    token = word.lower().strip("'-")
    if not token:
        return ""
    if token in _IRREGULAR_LEMMA:
        return _IRREGULAR_LEMMA[token]

    # 규칙 순서가 곧 우선순위입니다. min_stem은 "잘라낸 뒤 남을 최소 길이".
    rules: tuple[tuple[str, str, int], ...] = (
        ("ies", "y", 3),  # studies -> study
        ("ied", "y", 3),  # applied -> apply
        ("iest", "y", 3),  # easiest -> easy
        ("ier", "y", 3),  # easier -> easy
        ("sses", "ss", 3),  # passes -> pass
        ("ches", "ch", 3),  # watches -> watch
        ("shes", "sh", 3),  # dishes -> dish
        ("xes", "x", 3),  # boxes -> box
        ("ing", "", 3),  # reducing -> reduc
        ("edly", "", 4),  # repeatedly -> repeat
        ("ed", "", 3),  # repeated -> repeat
        ("ly", "", 4),  # periodically -> periodical
        # 일반 "es" 규칙은 두지 않습니다. 치찰음 뒤 -es는 위 sses/ches/shes/xes가 처리하고,
        # 그 외 "-es"는 e가 어간의 일부입니다("routines"는 "routin"이 아니라 "routine").
        ("s", "", 3),  # habits -> habit, routines -> routine, ones -> one
    )

    for suffix, replacement, min_stem in rules:
        if not token.endswith(suffix):
            continue
        if suffix == "s" and token.endswith("ss"):
            continue
        stem = token[: -len(suffix)] + replacement
        if len(stem) >= min_stem:
            return _collapse_double_consonant(stem)

    return token


def _collapse_double_consonant(stem: str) -> str:
    # "planned" -> "plann" -> "plan", "running" -> "runn" -> "run"
    if len(stem) >= 4 and stem[-1] == stem[-2] and stem[-1] not in "aeiouls":
        return stem[:-1]
    return stem


def content_word_candidates(passage: str, *, min_length: int = 3) -> list[str]:
    """지문에서 핵심단어 후보(기초어휘를 뺀 내용어)를 등장 순서대로 반환합니다.

    같은 표제어로 묶이는 변화형은 첫 등장 형태 하나만 남깁니다.
    """
    seen: set[str] = set()
    candidates: list[str] = []

    for raw in _TOKEN_RE.findall(passage):
        token = raw.lower().strip("'-")
        if len(token) < min_length or token in BASIC_WORDS:
            continue
        if lemma(token) in BASIC_WORDS:
            continue
        # 커버리지 대조와 같은 키로 묶어야 후보 목록과 미커버 계산이 어긋나지 않습니다.
        key = match_key(token)
        if not key or key in seen:
            continue
        seen.add(key)
        candidates.append(token)

    return candidates


def match_key(word: str) -> str:
    """항목 커버리지 비교에 쓰는 정규화 키.

    `lemma`보다 한 단계 더 뭉갭니다. -ing/-ed를 떼면 묵음 e가 함께 날아가므로
    ("reducing" -> "reduc") 끝의 e를 없애 "reduce"와 같은 키로 맞춥니다.
    표시용이 아니라 대조용 키라서 과하게 뭉개져도 괜찮습니다.
    """
    key = lemma(re.sub(r"[^A-Za-z'-]+", "", word or ""))
    if len(key) >= 4 and key.endswith("e"):
        return key[:-1]
    return key


def missing_candidates(candidates: list[str], covered_words: list[str]) -> list[str]:
    """후보 중 아직 단어장 항목으로 다뤄지지 않은 것만 남깁니다."""
    covered: set[str] = set()
    for word in covered_words:
        # 구(phrase) 표제어는 구성 단어 전부를 커버한 것으로 봅니다.
        for part in _TOKEN_RE.findall(word or ""):
            key = match_key(part)
            if key:
                covered.add(key)

    return [word for word in candidates if match_key(word) not in covered]
