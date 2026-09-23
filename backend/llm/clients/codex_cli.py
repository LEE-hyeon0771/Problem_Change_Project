"""로컬 Codex CLI provider(실험용). 요청마다 subprocess 를 띄웁니다."""

from __future__ import annotations

import json
import logging
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

from backend.core.errors import GenerationError
from backend.llm.clients.base import BaseJSONLLMClient

logger = logging.getLogger(__name__)


class CodexCliLLMClient(BaseJSONLLMClient):
    """Experimental local provider that shells out to the logged-in Codex CLI."""

    provider_label = "Codex CLI"

    def _build_prompt(self, prompt: str, schema: dict | None, json_mode: bool) -> str:
        guardrail = (
            "You are being used as a pure JSON generation backend for an exam-item service.\n"
            "Do not edit files, do not inspect local files, and do not run shell commands.\n"
            "Return only the requested final answer.\n\n"
        )
        if schema or json_mode:
            guardrail += "The final answer must be one complete JSON object with no markdown fence.\n\n"
        return f"{guardrail}{prompt}"

    def _generate_raw(
        self,
        prompt: str,
        schema: dict | None = None,
        temperature: float | None = None,
        json_mode: bool = True,
        label: str = "-",
    ) -> str:
        command = self.settings.codex_cli_command
        executable = shutil.which(command)
        if not executable:
            raise GenerationError(f"Codex CLI command not found: {command}")

        started = time.monotonic()
        with tempfile.TemporaryDirectory(prefix="problem-change-codex-") as temp_dir:
            temp_path = Path(temp_dir)
            output_path = temp_path / "last-message.txt"
            cmd = [
                executable,
                "exec",
                "--ephemeral",
                "--skip-git-repo-check",
                "--ignore-rules",
                "--sandbox",
                "read-only",
                "--ask-for-approval",
                "never",
                "--cd",
                temp_dir,
                "--color",
                "never",
                "-o",
                str(output_path),
            ]
            if self.settings.codex_cli_model:
                cmd.extend(["--model", self.settings.codex_cli_model])
            if schema:
                schema_path = temp_path / "schema.json"
                schema_path.write_text(json.dumps(schema), encoding="utf-8")
                cmd.extend(["--output-schema", str(schema_path)])
            cmd.append("-")

            logger.info(
                "Codex CLI request start (model=%s, schema=%s, timeout=%ss).",
                self.settings.codex_cli_model or "default",
                bool(schema),
                self.settings.codex_cli_timeout_seconds,
            )
            try:
                result = subprocess.run(
                    cmd,
                    input=self._build_prompt(prompt=prompt, schema=schema, json_mode=json_mode),
                    text=True,
                    capture_output=True,
                    timeout=self.settings.codex_cli_timeout_seconds,
                    check=False,
                )
            except subprocess.TimeoutExpired as exc:
                raise GenerationError("Codex CLI request timed out.") from exc

            if result.returncode != 0:
                stderr = (result.stderr or result.stdout or "").strip()
                raise GenerationError(f"Codex CLI failed ({result.returncode}): {stderr[:500]}")

            if output_path.exists():
                text = output_path.read_text(encoding="utf-8").strip()
            else:
                text = result.stdout.strip()
            if not text:
                raise GenerationError("Codex CLI returned empty text response.")

            elapsed = (time.monotonic() - started) * 1000
            # Codex CLI는 토큰 사용량을 돌려주지 않습니다. 호출 사실만 남기고 비용은 비웁니다.
            self._record_usage(
                model=self.settings.codex_cli_model or "codex-cli-default",
                label=label,
                input_tokens=None,
                output_tokens=None,
                elapsed_ms=elapsed,
            )
            logger.info("Codex CLI response received (chars=%s, elapsed_ms=%.1f).", len(text), elapsed)
            return text
