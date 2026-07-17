import logging
from pathlib import Path
from typing import List

from apps.common.util.logging_util import log_method

logger = logging.getLogger("apps")


class DiffApplyService:
    @staticmethod
    @log_method
    def apply_diffs(project_path: str, code_diffs: list) -> List[str]:
        """将 Review 2 通过的 code_diffs 写入项目目录。"""
        root = Path(project_path).resolve()
        if not root.is_dir():
            raise RuntimeError(f"项目路径不存在: {root}（请在项目管理中配置有效路径）")

        logs: List[str] = []
        for item in code_diffs or []:
            if not isinstance(item, dict):
                continue
            rel = (item.get("filePath") or item.get("file_path") or "").strip()
            if not rel:
                continue
            target = (root / rel).resolve()
            if not str(target).startswith(str(root)):
                logs.append(f"跳过越权路径: {rel}")
                continue

            content = item.get("modified")
            if content is None:
                content = DiffApplyService._apply_diff_text(item.get("original") or "", item.get("diffText") or "")

            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
            logs.append(f"已写入: {rel} ({len(content)} bytes)")

        if not logs:
            logs.append("无有效 diff 可应用")
        return logs

    @staticmethod
    def _apply_diff_text(original: str, diff_text: str) -> str:
        if not diff_text:
            return original
        lines = original.splitlines(keepends=True)
        if not lines and original:
            lines = [original]
        out = list(lines)
        for raw in diff_text.splitlines():
            if raw.startswith("+") and not raw.startswith("+++"):
                out.append(raw[1:] + ("\n" if not raw[1:].endswith("\n") else ""))
            elif raw.startswith("-") and not raw.startswith("---"):
                line = raw[1:]
                if line in [l.rstrip("\n") for l in out]:
                    for i, existing in enumerate(out):
                        if existing.rstrip("\n") == line:
                            out.pop(i)
                            break
        return "".join(out)
