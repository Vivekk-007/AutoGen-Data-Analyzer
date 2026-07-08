from pathlib import Path

import pandas as pd

from config.local_utils import get_local_code_executor


def test_local_executor_runs_python_and_writes_file(tmp_path):
    executor = get_local_code_executor()
    executor.work_dir = tmp_path
    executor.work_dir.mkdir(parents=True, exist_ok=True)

    code = "import pandas as pd\nfrom pathlib import Path\nPath('demo.txt').write_text(pd.__version__, encoding='utf-8')"
    result = __import__("asyncio").run(executor.execute_code_blocks([{"code": code, "language": "python"}]))

    assert result["results"][0]["exit_code"] == 0
    assert (tmp_path / "demo.txt").exists()
