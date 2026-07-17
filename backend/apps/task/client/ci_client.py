import importlib.util
import logging
import subprocess
from pathlib import Path
from typing import List

from django.conf import settings

from apps.common.util.logging_util import log_method

logger = logging.getLogger("apps")


class CiClient:
    @staticmethod
    @log_method
    def run_tests(project_path: str) -> List[str]:
        """在项目目录运行测试（npm test / pytest）。"""
        root = Path(project_path).resolve()
        logs: List[str] = []

        if not root.is_dir():
            logs.append(f"CI: 项目路径不存在 {root}")
            return logs

        if (root / "package.json").exists():
            logs.extend(CiClient._run_cmd(root, ["npm", "test", "--if-present"], "npm test"))
            return logs

        has_py_tests = (
            (root / "pyproject.toml").exists()
            or (root / "pytest.ini").exists()
            or list(root.glob("**/test_*.py"))
        )
        if has_py_tests:
            if importlib.util.find_spec("pytest") is None:
                logs.append("CI: 未安装 pytest，跳过自测")
                return logs
            logs.extend(CiClient._run_cmd(root, ["python", "-m", "pytest", "-q", "--tb=short"], "pytest"))
            return logs

        logs.append("CI: 未检测到 npm/pytest，跳过自测")
        return logs

    @staticmethod
    def _run_cmd(cwd: Path, cmd: List[str], label: str) -> List[str]:
        logs = [f"CI: 运行 {label} ..."]
        strict = getattr(settings, "CI_STRICT", not settings.DEBUG)
        try:
            proc = subprocess.run(
                cmd,
                cwd=str(cwd),
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=300,
                shell=False,
            )
            out = (proc.stdout or proc.stderr or "").strip()
            if out:
                logs.append(out[:3000])
            if proc.returncode != 0:
                if not strict and proc.returncode in (1, 2, 5):
                    logs.append(f"CI: {label} 未通过 (exit={proc.returncode})，开发环境继续发布")
                    return logs
                raise RuntimeError(f"{label} 失败 exit={proc.returncode}")
            logs.append(f"CI: {label} 通过")
        except FileNotFoundError:
            logs.append(f"CI: 未找到命令 {cmd[0]}，跳过")
        except subprocess.TimeoutExpired:
            raise RuntimeError(f"{label} 超时")
        return logs
