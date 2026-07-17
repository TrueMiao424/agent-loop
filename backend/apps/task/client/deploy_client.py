import os
import subprocess
from pathlib import Path
from typing import List

from django.conf import settings

from apps.common.util.logging_util import log_method


class DeployClient:
    @staticmethod
    @log_method
    def deploy(project_path: str, task_id: int, title: str) -> List[str]:
        script = (getattr(settings, "DEPLOY_HOOK_SCRIPT", "") or "").strip()
        if not script:
            return ["Deploy: 未配置 DEPLOY_HOOK_SCRIPT，本地 commit 已完成（无远程发布）"]

        root = Path(project_path).resolve()
        env = os.environ.copy()
        env["AGENT_LOOP_TASK_ID"] = str(task_id)
        env["AGENT_LOOP_PROJECT_PATH"] = str(root)
        env["AGENT_LOOP_TASK_TITLE"] = title

        logs = [f"Deploy: 执行发布脚本 ..."]
        try:
            proc = subprocess.run(
                script,
                cwd=str(root),
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=int(getattr(settings, "DEPLOY_HOOK_TIMEOUT", 300)),
                shell=True,
                env=env,
            )
            out = (proc.stdout or proc.stderr or "").strip()
            if out:
                logs.append(out[:3000])
            if proc.returncode != 0:
                raise RuntimeError(f"发布脚本失败 exit={proc.returncode}")
            logs.append("Deploy: 发布脚本执行成功")
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError("发布脚本超时") from exc
        return logs
