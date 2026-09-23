"""코드와 문서/배포 설정이 어긋나는 것을 잡는 테스트.

기능 테스트가 아니라 정합성 테스트입니다. 설정을 선언해 놓고 안 쓰거나,
엔드포인트를 추가하고 문서를 안 고치거나, 비밀 파일이 배포물에 새는 것을 막습니다.
"""

from pathlib import Path

import pytest

from backend.core.config import Settings
from backend.main import app

ROOT = Path(__file__).resolve().parent.parent
BACKEND = ROOT / "backend"


def _backend_source() -> str:
    return "\n".join(p.read_text(encoding="utf-8") for p in BACKEND.rglob("*.py"))


def _docs() -> str:
    """개발자가 읽는 문서 전부. CLAUDE.md 가 백엔드/프론트로 쪼개져 있어 함께 봅니다."""
    names = (
        "README.md",
        "CLAUDE.md",
        "docs/CLAUDE_backend.md",
        "docs/CLAUDE_frontend.md",
    )
    return "\n".join((ROOT / name).read_text(encoding="utf-8") for name in names)


# ------------------------------------------------------------------- 죽은 설정


def test_every_setting_is_actually_read() -> None:
    """선언만 하고 아무도 안 읽는 설정은 문서를 거짓말로 만듭니다."""
    source = _backend_source()
    # property 로 감싸 읽는 설정은 그 property 이름으로 사용됩니다.
    indirect = {"llm_provider": "normalized_llm_provider"}

    unused = []
    for name in Settings.model_fields:
        needles = [f"settings.{name}", f"self.{name}", f".{name}"]
        if name in indirect:
            needles.append(indirect[name])
        if not any(needle in source for needle in needles):
            unused.append(name)

    assert not unused, f"코드에서 읽지 않는 설정: {unused}. 구현하거나 제거하세요."


def test_every_setting_is_documented() -> None:
    docs = _docs()
    missing = [
        (f.alias or name).upper()
        for name, f in Settings.model_fields.items()
        if (f.alias or name).upper() not in docs
    ]

    assert not missing, f"문서에 없는 환경변수: {missing}"


# --------------------------------------------------------------- 엔드포인트


def test_every_api_route_is_documented() -> None:
    docs = _docs()
    paths = {
        route.path
        for route in app.routes
        if getattr(route, "methods", None) and (route.path.startswith("/api") or route.path == "/health")
    }
    missing = sorted(path for path in paths if path not in docs)

    assert not missing, f"문서에 없는 엔드포인트: {missing}"


# ------------------------------------------------------------ 비밀 유출 방지


@pytest.mark.parametrize("pattern", [".env", ".env.*", "problem_log/", ".venv/", "frontend/node_modules/"])
def test_gitignore_blocks_secrets_and_artifacts(pattern: str) -> None:
    ignored = (ROOT / ".gitignore").read_text(encoding="utf-8")

    assert pattern in ignored, f".gitignore 에 {pattern} 규칙이 필요합니다."


def test_gitignore_keeps_env_example_tracked() -> None:
    ignored = (ROOT / ".gitignore").read_text(encoding="utf-8")

    # .env.* 로 전부 막으면서 템플릿은 살려 둬야 배포물에 포함됩니다.
    assert "!.env.example" in ignored


def test_package_script_excludes_every_env_file() -> None:
    """`.env.bak` 같은 백업에도 API 키가 들어 있어 배포물에서 빠져야 합니다."""
    script = (ROOT / "package.sh").read_text(encoding="utf-8")

    assert '--exclude ".env*"' in script
    assert '--include ".env.example"' in script
    # include 가 exclude 보다 앞에 와야 rsync 에서 템플릿이 살아남습니다.
    assert script.index('--include ".env.example"') < script.index('--exclude ".env*"')


def test_no_env_backup_files_left_in_repo() -> None:
    leftovers = [p.name for p in ROOT.glob(".env.*") if p.name != ".env.example"]

    assert not leftovers, f"API 키가 남아 있을 수 있는 파일: {leftovers}"


# ------------------------------------------------------------------ 배포 파일


@pytest.mark.parametrize(
    "name",
    ["dev.sh", "dev.bat", "dev.ps1", "package.sh", "START_HERE.md", ".env.example"],
)
def test_distribution_files_exist(name: str) -> None:
    assert (ROOT / name).exists(), f"배포에 필요한 {name} 이(가) 없습니다."


def test_dev_bat_is_ascii_only() -> None:
    """한글 Windows(CP949)에서 배치 파일이 깨지지 않아야 합니다."""
    raw = (ROOT / "dev.bat").read_bytes()

    assert all(byte < 128 for byte in raw), "dev.bat 은 ASCII 만 포함해야 합니다."
    assert b"\r\n" in raw, "dev.bat 은 CRLF 줄바꿈이어야 합니다."


# ------------------------------------------------------------ LLM provider 구조


def test_llm_clients_are_split_per_provider() -> None:
    clients = BACKEND / "llm" / "clients"

    for name in ["base.py", "gemini.py", "openai.py", "codex_cli.py", "mock.py", "__init__.py"]:
        assert (clients / name).exists(), f"llm/clients/{name} 이 없습니다."

    assert not (BACKEND / "llm" / "client.py").exists(), (
        "분리 전 client.py 가 남아 있으면 import 경로가 둘로 갈립니다."
    )


def test_every_provider_is_exported() -> None:
    from backend.llm import clients

    for name in ["BaseJSONLLMClient", "GeminiLLMClient", "OpenAILLMClient",
                 "CodexCliLLMClient", "MockLLMClient", "LLMClient"]:
        assert hasattr(clients, name), f"{name} 이 llm/clients 에서 노출되지 않습니다."


def test_provider_modules_stay_small() -> None:
    clients = BACKEND / "llm" / "clients"
    oversized = {
        p.name: len(p.read_text(encoding="utf-8").splitlines())
        for p in clients.glob("*.py")
        if len(p.read_text(encoding="utf-8").splitlines()) > 250
    }

    assert not oversized, f"250줄을 넘는 provider 모듈: {oversized}"


def test_only_base_module_holds_shared_retry_logic() -> None:
    """재시도/JSON 복구 로직이 provider 별로 복제되면 동작이 갈립니다."""
    clients = BACKEND / "llm" / "clients"
    offenders = [
        p.name
        for p in clients.glob("*.py")
        if p.name != "base.py" and "def generate_json" in p.read_text(encoding="utf-8")
        and p.name != "mock.py"  # mock 은 호출 없이 payload 를 돌려주려 의도적으로 오버라이드
    ]

    assert not offenders, f"generate_json 은 base.py 에만 있어야 합니다: {offenders}"


# ------------------------------------------------------- 문서가 가리키는 경로


def _doc_files() -> list[Path]:
    return [ROOT / "CLAUDE.md", ROOT / "README.md", *(ROOT / "docs").glob("*.md")]


def test_split_guides_exist_and_are_linked() -> None:
    """CLAUDE.md 는 진입점입니다. 상세 문서를 가리키지 않으면 찾을 수 없습니다."""
    index = (ROOT / "CLAUDE.md").read_text(encoding="utf-8")

    for name in ("docs/CLAUDE_backend.md", "docs/CLAUDE_frontend.md"):
        assert (ROOT / name).exists(), f"{name} 이 없습니다."
        assert name in index, f"CLAUDE.md 가 {name} 을 가리키지 않습니다."


def test_documented_paths_all_exist() -> None:
    """문서가 리팩토링 전 경로를 가리키면 읽는 사람이 헤맵니다."""
    import re

    missing = set()
    for doc in _doc_files():
        for path in re.findall(r"`((?:backend|frontend|tests|docs)/[A-Za-z0-9_./-]+)`", doc.read_text(encoding="utf-8")):
            if "*" in path:
                continue
            if not (ROOT / path).exists():
                missing.add(f"{doc.name}: {path}")

    assert not missing, f"문서가 없는 경로를 가리킵니다: {sorted(missing)}"


def test_docs_do_not_reference_removed_modules() -> None:
    """리팩토링으로 사라진 모듈명이 문서에 남으면 안 됩니다."""
    removed = ["backend/llm/client.py", "frontend/src/lib/stream.js", "frontend/src/app.css"]

    offenders = []
    for doc in _doc_files():
        text = doc.read_text(encoding="utf-8")
        for name in removed:
            # 리팩토링 이력 문서는 "이전 → 이후" 기록으로 언급할 수 있으므로,
            # 취소선(~~) 안에 있으면 통과시킵니다.
            for line in text.splitlines():
                if name in line and "~~" not in line:
                    offenders.append(f"{doc.name}: {line.strip()[:70]}")

    assert not offenders, f"사라진 모듈을 현재형으로 언급합니다: {offenders}"
