from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import Any

from autogen_core.code_executor import CodeBlock
from autogen_core import CancellationToken

from config.constants import TIMEOUT_LOCAL, WORKSPACE_DIR

try:
    from autogen_ext.code_executors.local import LocalCommandLineCodeExecutor as _LocalCommandLineCodeExecutor
except Exception:  # pragma: no cover - fallback for older/newer installs
    _LocalCommandLineCodeExecutor = None


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

    async def execute_code_blocks(self, code_blocks: list[dict[str, Any]] | list[CodeBlock], cancellation_token: Any = None) -> Any:
        token = cancellation_token or CancellationToken()
        results = []
        os.environ.setdefault("MPLBACKEND", "Agg")
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
                results.append({"exit_code": 1, "stdout": "", "stderr": "Unsupported language", "script_path": None})
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
            results.append(
                {
                    "exit_code": completed.returncode,
                    "stdout": completed.stdout,
                    "stderr": completed.stderr,
                    "script_path": str(script_path),
                }
            )

        return {"results": results}


def get_local_code_executor() -> LocalSandboxCodeExecutor:
    """Create a Docker-free executor backed by the local workspace directory."""
    return LocalSandboxCodeExecutor(work_dir=WORKSPACE_DIR, timeout=TIMEOUT_LOCAL)


async def start_local_executor(executor: LocalSandboxCodeExecutor) -> None:
    await executor.start()


async def stop_local_executor(executor: LocalSandboxCodeExecutor) -> None:
    await executor.stop()
