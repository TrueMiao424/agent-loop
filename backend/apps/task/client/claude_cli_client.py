import shutil
import subprocess
from pathlib import Path
from typing import List, Optional, Tuple

from django.conf import settings

from apps.common.util.logging_util import log_external_call, log_method


class ClaudeCliClient:
    """本机 Claude Code CLI（claude 命令）在项目目录内执行。"""

    @staticmethod
    def is_available() -> bool:
        if not getattr(settings, "CLAUDE_CLI_ENABLED", True):
            return False
        return shutil.which("claude") is not None

    @staticmethod
    @log_method
    def run_in_project(project_path: str, prompt: str, timeout: int = 600) -> Tuple[str, bool]:
        root = Path(project_path).resolve()
        if not root.is_dir():
            raise RuntimeError(f"项目路径不存在: {root}")

        cmd = [
            "claude",
            "-p",
            prompt,
            "--dangerously-skip-permissions",
        ]
        start = __import__("time").time()
        try:
            proc = subprocess.run(
                cmd,
                cwd=str(root),
                capture_output=True,
                text=True,
                timeout=timeout,
                shell=False,
            )
            duration = int((__import__("time").time() - start) * 1000)
            out = (proc.stdout or "") + (proc.stderr or "")
            log_external_call(
                "claude-cli",
                " ".join(cmd[:3]) + " ...",
                {"cwd": str(root), "prompt_len": len(prompt)},
                out[:2000],
                duration,
                None if proc.returncode == 0 else f"exit={proc.returncode}",
            )
            return out.strip(), proc.returncode == 0
        except subprocess.TimeoutExpired as exc:
            duration = int((__import__("time").time() - start) * 1000)
            log_external_call("claude-cli", "claude", {"cwd": str(root)}, None, duration, "timeout")
            raise RuntimeError(f"Claude CLI 超时 ({timeout}s)") from exc
        except FileNotFoundError as exc:
            raise RuntimeError("未找到 claude 命令，请安装 Claude Code CLI 或配置 API Key") from exc

    @staticmethod
    @log_method
    def collect_diffs_from_git(project_path: str, scope_files: Optional[List[str]] = None) -> List[dict]:
        """从 git 工作区收集真实变更，供 Review 2 展示。"""
        root = Path(project_path).resolve()
        diffs: List[dict] = []

        status = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=str(root),
            capture_output=True,
            text=True,
            shell=False,
        )
        changed: List[str] = []
        if status.returncode == 0 and status.stdout.strip():
            for line in status.stdout.splitlines():
                path = line[3:].strip().replace("\\", "/")
                if path:
                    changed.append(path)

        if scope_files:
            for rel in scope_files:
                rel = rel.replace("\\", "/")
                if rel not in changed:
                    target = root / rel
                    if target.is_file() and rel not in changed:
                        changed.append(rel)

        seen = set()
        for rel in changed:
            if rel in seen:
                continue
            seen.add(rel)
            if scope_files and rel not in scope_files:
                continue

            diff_proc = subprocess.run(
                ["git", "diff", "--", rel],
                cwd=str(root),
                capture_output=True,
                text=True,
                shell=False,
            )
            diff_text = (diff_proc.stdout or "").strip()
            original = ""
            modified = ""
            target = root / rel
            if target.is_file():
                try:
                    modified = target.read_text(encoding="utf-8")
                except OSError:
                    modified = ""
            diffs.append(
                {
                    "filePath": rel,
                    "original": original,
                    "modified": modified,
                    "diffText": diff_text or f"(new/updated file, {len(modified)} bytes)",
                }
            )
        return diffs
