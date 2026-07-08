from pathlib import Path

WORK_DIR_DOCKER = Path(__file__).resolve().parent.parent / "temp"
WORKSPACE_DIR = Path(__file__).resolve().parent.parent / "workspace"
TIMEOUT_DOCKER = 120
TIMEOUT_LOCAL = 120