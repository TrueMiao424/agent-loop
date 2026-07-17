from pathlib import Path
from typing import List, Optional, Tuple

MAX_FILE_CHARS = 12000


def read_convention(project_path: str, convention_rel: str = "") -> str:
    if not convention_rel:
        return ""
    path = Path(project_path).resolve() / convention_rel
    if not path.is_file():
        return ""
    try:
        return path.read_text(encoding="utf-8")[:MAX_FILE_CHARS]
    except OSError:
        return ""


def read_workspace_file(project_path: str, rel_path: str) -> Optional[str]:
    root = Path(project_path).resolve()
    target = (root / rel_path).resolve()
    if not str(target).startswith(str(root)) or not target.is_file():
        return None
    try:
        return target.read_text(encoding="utf-8")
    except OSError:
        return None


def build_file_context(project_path: str, file_paths: List[str]) -> str:
    blocks: List[str] = []
    for rel in file_paths or []:
        rel = (rel or "").strip()
        if not rel:
            continue
        content = read_workspace_file(project_path, rel)
        if content is None:
            blocks.append(f"### {rel}\n(文件不存在，将新建)\n")
        else:
            snippet = content[:MAX_FILE_CHARS]
            suffix = "\n...(truncated)" if len(content) > MAX_FILE_CHARS else ""
            blocks.append(f"### {rel}\n```\n{snippet}{suffix}\n```\n")
    return "\n".join(blocks)


def list_existing_files(project_path: str, limit: int = 40) -> List[str]:
    root = Path(project_path).resolve()
    if not root.is_dir():
        return []
    ignore = {".git", "node_modules", ".venv", "__pycache__", ".pytest_cache"}
    found: List[str] = []
    for path in sorted(root.rglob("*")):
        if any(part in ignore for part in path.parts):
            continue
        if path.is_file():
            found.append(str(path.relative_to(root)).replace("\\", "/"))
        if len(found) >= limit:
            break
    return found
