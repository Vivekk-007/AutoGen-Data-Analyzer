from autogen_ext.code_executors.docker import DockerCommandLineCodeExecutor

from config.constants import TIMEOUT_DOCKER, WORK_DIR_DOCKER


def getDockerCommandLineExecutor():
    WORK_DIR_DOCKER.mkdir(parents=True, exist_ok=True)
    docker = DockerCommandLineCodeExecutor(
        work_dir=str(WORK_DIR_DOCKER),
        bind_dir=str(WORK_DIR_DOCKER),
        timeout=TIMEOUT_DOCKER,
        init_command="pip install --no-input pandas matplotlib numpy seaborn",
    )

    return docker


async def start_docker_container(docker):
    print("Starting Docker Container")
    await docker.start()
    print("Docker Container Started")


async def stop_docker_container(docker):
    print("Stop Docker Container")
    await docker.stop()
    print("Docker Container Stopped")
