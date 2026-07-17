import os
import subprocess
from pathlib import Path
from typing import List, Optional

from django.conf import settings

from apps.common.util.logging_util import log_external_call, log_method


class GitClient:
    @staticmethod
    @log_method
    def _run(cwd: str, *args: str, timeout: int = 120) -> subprocess.CompletedProcess:
        cmd = ["git", *args]
        start = __import__("time").time()
        try:
            proc = subprocess.run(
                cmd,
                cwd=cwd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout,
                shell=False,
            )
            duration = int((__import__("time").time() - start) * 1000)
            log_external_call(
                "git",
                " ".join(cmd),
                {"cwd": cwd},
                (proc.stdout or proc.stderr or "")[:2000],
                duration,
                None if proc.returncode == 0 else f"exit={proc.returncode}",
            )
            return proc
        except Exception as exc:
            duration = int((__import__("time").time() - start) * 1000)
            log_external_call("git", " ".join(cmd), {"cwd": cwd}, None, duration, str(exc))
            raise

    @staticmethod
    @log_method
    def ensure_repo(project_path: str) -> bool:
        path = Path(project_path)
        if not path.is_dir():
            return False
        if (path / ".git").exists():
            return True
        if getattr(settings, "GIT_AUTO_INIT", False):
            GitClient._run(str(path), "init")
            return True
        return False

    @staticmethod
    @log_method
    def ensure_remote(project_path: str, remote_url: str) -> List[str]:
        logs = []
        if not remote_url:
            return logs
        path = str(Path(project_path).resolve())
        remotes = GitClient._run(path, "remote")
        if "origin" in (remotes.stdout or ""):
            GitClient._run(path, "remote", "set-url", "origin", remote_url)
            logs.append(f"Git remote origin 已更新: {remote_url}")
        else:
            GitClient._run(path, "remote", "add", "origin", remote_url)
            logs.append(f"Git remote origin 已添加: {remote_url}")
        return logs

    @staticmethod
    @log_method
    def commit_and_push(
        project_path: str,
        message: str,
        branch: Optional[str] = None,
        remote_url: str = "",
        push_enabled: Optional[bool] = None,
    ) -> List[str]:
        path = str(Path(project_path).resolve())
        if not GitClient.ensure_repo(path):
            raise RuntimeError(f"非 git 仓库且未开启 GIT_AUTO_INIT: {path}")

        logs = []
        if remote_url:
            logs.extend(GitClient.ensure_remote(path, remote_url))

        branch = branch or getattr(settings, "GIT_DEFAULT_BRANCH", "main")
        push_on = getattr(settings, "GIT_PUSH_ENABLED", False) if push_enabled is None else push_enabled

        status = GitClient._run(path, "status", "--porcelain")
        if not (status.stdout or "").strip():
            logs.append("Git: 无变更，跳过 commit")
            return logs

        add = GitClient._run(path, "add", "-A")
        if add.returncode != 0:
            raise RuntimeError(f"git add 失败: {(add.stderr or add.stdout or '').strip()[:500]}")

        commit = GitClient._run(path, "commit", "-m", message)
        if commit.returncode != 0:
            raise RuntimeError(f"git commit 失败: {(commit.stderr or commit.stdout or '').strip()[:500]}")
        logs.append(f"Git commit: {(commit.stdout or commit.stderr or '').strip()[:500]}")

        if push_on:
            current = GitClient._run(path, "rev-parse", "--abbrev-ref", "HEAD")
            use_branch = (current.stdout or branch).strip() or branch
            if use_branch != (current.stdout or "").strip():
                checkout = GitClient._run(path, "checkout", "-B", use_branch)
                if checkout.returncode != 0:
                    raise RuntimeError(
                        f"切换分支失败: {(checkout.stderr or checkout.stdout or '').strip()[:500]}"
                    )
            push = GitClient._run(path, "push", "-u", "origin", use_branch)
            if push.returncode != 0:
                raise RuntimeError(f"git push 失败: {(push.stderr or push.stdout or '').strip()[:800]}")
            logs.append(f"Git push origin {use_branch}: {(push.stdout or push.stderr or '').strip()[:500]}")
        else:
            logs.append("Git push 已跳过（未开启推送）")

        return logs
