"""Svelte 컴포넌트가 import 없이 쓰이는 것을 잡습니다.

Vite 는 이것을 **경고로만** 알리고 빌드를 통과시킵니다. 런타임에 가서야
`<X> is not a valid component` 로 화면이 죽기 때문에, 빌드 로그를 안 읽으면
그대로 배포됩니다. 실제로 WordCard 를 별도 파일로 뽑을 때 두 화면 모두에서
import 가 빠진 채 커밋된 적이 있습니다.
"""

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
COMPONENTS = ROOT / "frontend" / "src"

# `<svelte:component>` 등 프레임워크 특수 태그는 import 대상이 아닙니다.
_SPECIAL = re.compile(r"^svelte:")
# 템플릿에서 쓰인 컴포넌트: 대문자로 시작하는 태그
_USED = re.compile(r"<([A-Z][A-Za-z0-9_]*)\b")
_SCRIPT = re.compile(r"<script[^>]*>(.*?)</script>", re.DOTALL)


def _svelte_files() -> list[Path]:
    return sorted(COMPONENTS.rglob("*.svelte"))


def test_there_are_svelte_files_to_check() -> None:
    """glob 이 빈 목록을 돌려주면 아래 테스트가 조용히 통과해 버립니다."""
    assert _svelte_files(), "검사할 .svelte 파일을 찾지 못했습니다."


@pytest.mark.parametrize("path", _svelte_files(), ids=lambda p: p.name)
def test_every_used_component_is_imported(path: Path) -> None:
    source = path.read_text(encoding="utf-8")

    scripts = "\n".join(_SCRIPT.findall(source))
    template = _SCRIPT.sub("", source)

    missing = sorted(
        {
            name
            for name in _USED.findall(template)
            if not _SPECIAL.match(name)
            and not re.search(rf"\bimport\s+(?:{name}\b|.*\b{name}\b.*from)", scripts)
        }
    )

    assert not missing, (
        f"{path.name} 이 import 없이 컴포넌트를 사용합니다: {missing}. "
        "Vite 는 경고만 내고 통과시키므로 런타임에 화면이 죽습니다."
    )
