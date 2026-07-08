# This module now wraps the local sandbox executor so the app no longer depends on Docker.
from config.constants import TIMEOUT_LOCAL, WORKSPACE_DIR
from config.local_utils import LocalSandboxCodeExecutor, get_local_code_executor


def getDockerCommandLineExecutor():
    """Backward-compatible factory name for the new local executor."""
    return get_local_code_executor()


async def start_docker_container(docker):
    """Compatibility shim for code that used to start a container."""
    await docker.start()


async def stop_docker_container(docker):
    """Compatibility shim for code that used to stop a container."""
    await docker.stop()
