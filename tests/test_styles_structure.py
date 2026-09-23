"""CSS 분리 구조 검증.

CSS 는 나중에 선언된 규칙이 이깁니다. 분리한 파일의 import 순서가 틀어지면
빌드는 성공하는데 화면만 조용히 깨집니다. 그 회귀를 막습니다.
"""

import re
from pathlib import Path

import pytest

STYLES = Path(__file__).resolve().parent.parent / "frontend" / "src" / "styles"
INDEX = STYLES / "index.css"


def _imported_files() -> list[str]:
    return re.findall(r'@import\s+"\./([^"]+)"', INDEX.read_text(encoding="utf-8"))


def test_entry_point_exists() -> None:
    assert INDEX.exists(), "styles/index.css 가 없으면 스타일이 전혀 로드되지 않습니다."


def test_main_js_imports_the_entry_point() -> None:
    main_js = (STYLES.parent / "main.js").read_text(encoding="utf-8")

    assert "./styles/index.css" in main_js
    assert "./app.css" not in main_js, "분리 전 파일을 아직 참조하고 있습니다."


def test_every_style_file_is_imported() -> None:
    on_disk = {p.name for p in STYLES.glob("*.css")} - {"index.css"}

    assert on_disk == set(_imported_files()), "index.css 에 등록되지 않은 스타일 파일이 있습니다."


def test_every_import_target_exists() -> None:
    missing = [name for name in _imported_files() if not (STYLES / name).exists()]

    assert not missing, f"index.css 가 없는 파일을 import 합니다: {missing}"


def test_tokens_come_first() -> None:
    """CSS 변수(--ink 등)는 쓰이기 전에 정의돼야 합니다."""
    assert _imported_files()[0] == "tokens.css"


@pytest.mark.parametrize("name", ["responsive.css", "print.css"])
def test_overrides_come_last(name: str) -> None:
    """반응형과 인쇄는 앞선 규칙을 덮어쓰므로 반드시 뒤에 와야 합니다."""
    order = _imported_files()

    assert order.index(name) >= len(order) - 2, f"{name} 은(는) 맨 뒤 두 자리에 있어야 합니다."


def test_print_comes_after_responsive() -> None:
    order = _imported_files()

    assert order.index("print.css") > order.index("responsive.css")


def test_no_file_is_oversized() -> None:
    """한 파일이 너무 커지면 분리한 의미가 없어집니다."""
    oversized = {
        p.name: len(p.read_text(encoding="utf-8").splitlines())
        for p in STYLES.glob("*.css")
        if len(p.read_text(encoding="utf-8").splitlines()) > 400
    }

    assert not oversized, f"400줄을 넘는 스타일 파일: {oversized}"


def test_media_queries_live_only_in_override_files() -> None:
    """반응형/인쇄 규칙이 컴포넌트 파일에 흩어지면 우선순위를 추적할 수 없습니다."""
    strays = []
    for path in STYLES.glob("*.css"):
        if path.name in {"index.css", "responsive.css", "print.css"}:
            continue
        if "@media" in path.read_text(encoding="utf-8"):
            strays.append(path.name)

    assert not strays, f"@media 는 responsive.css / print.css 에만 두세요: {strays}"


# --------------------------------------------------- 컴포넌트 크기/분리 구조

COMPONENTS = STYLES.parent / "components"


def test_exam_builder_is_a_thin_shell() -> None:
    """831줄짜리 한 파일로 되돌아가는 것을 막습니다."""
    shell = (COMPONENTS / "MockExamBuilder.svelte").read_text(encoding="utf-8")

    assert len(shell.splitlines()) < 60, "MockExamBuilder 는 모드 전환만 하는 껍데기여야 합니다."
    assert "ProblemSheet" in shell and "VocabSheet" in shell


@pytest.mark.parametrize("name", ["exam/ProblemSheet.svelte", "exam/VocabSheet.svelte"])
def test_split_sheets_exist(name: str) -> None:
    assert (COMPONENTS / name).exists()


def test_no_component_is_oversized() -> None:
    oversized = {
        p.relative_to(COMPONENTS).as_posix(): len(p.read_text(encoding="utf-8").splitlines())
        for p in COMPONENTS.rglob("*.svelte")
        if len(p.read_text(encoding="utf-8").splitlines()) > 600
    }

    assert not oversized, f"600줄을 넘는 컴포넌트: {oversized}"


# ----------------------------------------------------- API 레이어 / 공용 컴포넌트

SRC = STYLES.parent


def test_components_never_call_fetch_directly() -> None:
    """에러 파싱이 파일마다 복제되는 것을 막습니다. API 는 lib/api/ 를 거칩니다."""
    offenders = [
        p.relative_to(SRC).as_posix()
        for p in [*SRC.glob("*.svelte"), *(SRC / "components").rglob("*.svelte")]
        if "fetch(" in p.read_text(encoding="utf-8")
    ]

    assert not offenders, f"컴포넌트에서 fetch 직접 호출: {offenders}"


def test_api_layer_exists() -> None:
    api = SRC / "lib" / "api"

    for name in ["client.js", "problems.js", "wordbooks.js", "generation.js", "stream.js", "index.js"]:
        assert (api / name).exists(), f"lib/api/{name} 이 없습니다."


def test_only_client_module_parses_error_responses() -> None:
    """에러 본문 파싱은 client.js 한 곳에만 있어야 합니다."""
    offenders = [
        p.relative_to(SRC).as_posix()
        for p in SRC.rglob("*.js")
        if p.name != "client.js" and "response.status`" in p.read_text(encoding="utf-8")
    ]
    offenders += [
        p.relative_to(SRC).as_posix()
        for p in [*SRC.glob("*.svelte"), *(SRC / "components").rglob("*.svelte")]
        if "response.status`" in p.read_text(encoding="utf-8")
    ]

    assert not offenders, f"에러 파싱이 흩어져 있습니다: {offenders}"


def test_word_card_markup_is_not_duplicated() -> None:
    """단어 카드는 WordCard.svelte 하나만 그립니다."""
    drawers = [
        p.relative_to(SRC).as_posix()
        for p in (SRC / "components").rglob("*.svelte")
        if "relation-chip" in p.read_text(encoding="utf-8")
    ]

    assert drawers == ["components/wordbook/WordCard.svelte"], f"단어 카드 마크업 중복: {drawers}"
