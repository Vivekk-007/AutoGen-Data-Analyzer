from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import Any

from autogen_core import CancellationToken
from autogen_core.code_executor import CodeBlock, CodeResult

from config.constants import TIMEOUT_LOCAL, WORKSPACE_DIR

try:
    from autogen_ext.code_executors.local import LocalCommandLineCodeExecutor as _LocalCommandLineCodeExecutor
except Exception:  # pragma: no cover - fallback for older/newer installs
    _LocalCommandLineCodeExecutor = None


class CompatCodeResult(CodeResult):
    """Backwards-compatible result object for both AutoGen and older call sites."""

    def __init__(self, *, exit_code: int, output: str, results: list[dict[str, Any]] | None = None):
        super().__init__(exit_code=exit_code, output=output)
        self._results = results or []

    def __getitem__(self, key: str) -> Any:
        if key == "results":
            return self._results
        raise KeyError(key)

    def get(self, key: str, default: Any = None) -> Any:
        if key == "results":
            return self._results
        return default


class LocalSandboxCodeExecutor:
    """Docker-free code executor that runs Python locally inside a workspace directory."""

    def __init__(self, work_dir: str | Path | None = None, timeout: int | None = None):
        self.work_dir = Path(work_dir or WORKSPACE_DIR)
        self.work_dir.mkdir(parents=True, exist_ok=True)
        self.timeout = timeout or TIMEOUT_LOCAL
        self._backend = None
        self._use_fallback = False

        if _LocalCommandLineCodeExecutor is not None:
            try:
                # Use the AutoGen local executor when it is available in the installed version.
                self._backend = _LocalCommandLineCodeExecutor(work_dir=str(self.work_dir), timeout=self.timeout)
            except Exception as exc:  # pragma: no cover - defensive fallback
                print(f"LocalCommandLineCodeExecutor unavailable; using subprocess fallback: {exc}")
                self._use_fallback = True
        else:
            self._use_fallback = True

    async def start(self) -> None:
        if self._backend is not None and hasattr(self._backend, "start"):
            await self._backend.start()

    async def stop(self) -> None:
        if self._backend is not None and hasattr(self._backend, "stop"):
            await self._backend.stop()

    async def execute_code_blocks(self, code_blocks: list[dict[str, Any]] | list[CodeBlock], cancellation_token: Any = None) -> CompatCodeResult:
        token = cancellation_token or CancellationToken()
        os.environ.setdefault("MPLBACKEND", "Agg")

        combined_output: list[str] = []
        exit_code = 0
        results: list[dict[str, Any]] = []

        for block in code_blocks:
            if isinstance(block, CodeBlock):
                code = block.code
                language = block.language
            elif isinstance(block, dict):
                code = block.get("code", "")
                language = block.get("language", "python")
            else:
                code = str(block)
                language = "python"

            if not code or language.lower() != "python":
                result = {
                    "exit_code": 1,
                    "stdout": "",
                    "stderr": "Unsupported language",
                    "script_path": None,
                }
                results.append(result)
                combined_output.append(result["stderr"])
                exit_code = 1
                continue

            script_path = self.work_dir / f"tmp_code_{len(results)}.py"
            script_path.write_text(code, encoding="utf-8")
            env = os.environ.copy()
            env["PYTHONPATH"] = str(self.work_dir) + os.pathsep + env.get("PYTHONPATH", "")
            completed = subprocess.run(
                [sys.executable, str(script_path)],
                cwd=str(self.work_dir),
                text=True,
                capture_output=True,
                timeout=self.timeout,
                env=env,
            )
            result = {
                "exit_code": completed.returncode,
                "stdout": completed.stdout,
                "stderr": completed.stderr,
                "script_path": str(script_path),
            }
            results.append(result)
            if completed.returncode != 0:
                exit_code = completed.returncode
            if completed.stdout:
                combined_output.append(completed.stdout)
            if completed.stderr:
                combined_output.append(completed.stderr)

        return CompatCodeResult(exit_code=exit_code, output="\n".join(combined_output), results=results)


def get_local_code_executor() -> LocalSandboxCodeExecutor:
    """Create a Docker-free executor backed by the local workspace directory."""
    return LocalSandboxCodeExecutor(work_dir=WORKSPACE_DIR, timeout=TIMEOUT_LOCAL)


async def start_local_executor(executor: LocalSandboxCodeExecutor) -> None:
    await executor.start()


async def stop_local_executor(executor: LocalSandboxCodeExecutor) -> None:
    await executor.stop()
