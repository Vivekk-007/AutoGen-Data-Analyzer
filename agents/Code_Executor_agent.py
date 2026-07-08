import asyncio

from autogen_agentchat.agents import CodeExecutorAgent
from autogen_agentchat.messages import TextMessage
from autogen_core import CancellationToken

from config.local_utils import get_local_code_executor


def getCodeExecutorAgent(code_executor):
    # The agent still exposes the same interface; only the executor backend changed.
    return CodeExecutorAgent(name="CodeExecutor", code_executor=code_executor)


async def main():
    executor = get_local_code_executor()
    code_executor_agent = getCodeExecutorAgent(executor)

    task = TextMessage(
        content="""Here is the Python code to run.
```python
print('Hello Wooooooooorld')
```""",
        source="User",
    )

    try:
        await executor.start()
        res = await code_executor_agent.on_messages(messages=[task], cancellation_token=CancellationToken())
        print("result is :", res)
    except Exception as exc:
        print(exc)
    finally:
        await executor.stop()


if __name__ == "__main__":
    asyncio.run(main())