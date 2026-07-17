from pathlib import Path

from django.conf import settings


def ensure_project_directory(project_path: str) -> Path:
    """确保项目根目录存在（开发环境可自动创建）。"""
    root = Path(project_path).resolve()
    if root.is_dir():
        return root
    if getattr(settings, "PROJECT_PATH_AUTO_CREATE", True):
        root.mkdir(parents=True, exist_ok=True)
        readme = root / "README.md"
        if not readme.exists():
            readme.write_text("# Agent Loop Project\n", encoding="utf-8")
        style_dir = root / ".github"
        style_dir.mkdir(exist_ok=True)
        style_file = style_dir / "coding_style.md"
        if not style_file.exists():
            style_file.write_text("# Coding Style\n\n- 保持代码简洁可读\n", encoding="utf-8")
        return root
    raise RuntimeError(f"项目路径不存在: {root}")
