import re
from pathlib import Path
from typing import List


_PLACEHOLDER_PATTERNS = (
    re.compile(r"^Added .{0,120}\.$", re.I),
    re.compile(r"^Imports and calls .{0,120}\.$", re.I),
    re.compile(r"^Implemented .{0,80}\.$", re.I),
)


def is_placeholder_content(text: str, rel_path: str = "") -> bool:
    stripped = (text or "").strip()
    name = Path(rel_path.replace("\\", "/")).name
    if name == "__init__.py":
        return False
    if not stripped:
        return True
    if len(stripped) < 30 and "\n" not in stripped:
        return True
    for pattern in _PLACEHOLDER_PATTERNS:
        if pattern.match(stripped):
            return True
    return False


def validate_code_diffs(code_diffs: List[dict]) -> List[str]:
    errors: List[str] = []
    if not code_diffs:
        errors.append("未生成任何 code_diffs")
        return errors
    for item in code_diffs:
        if not isinstance(item, dict):
            errors.append("diff 条目格式无效")
            continue
        rel = (item.get("filePath") or item.get("file_path") or "").strip()
        modified = item.get("modified")
        if not rel:
            errors.append("存在缺少 filePath 的 diff")
            continue
        if modified is None:
            errors.append(f"{rel}: 缺少 modified 字段")
            continue
        if is_placeholder_content(str(modified), rel):
            errors.append(f"{rel}: modified 为空或为占位描述，非真实代码")
    return errors
