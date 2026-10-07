"""路径工具。"""
from pathlib import Path


def find_mods_dir() -> Path:
    """从当前文件向上查找 mods/ 目录。"""
    current = Path(__file__).resolve()
    for parent in current.parents:
        candidate = parent / "mods"
        if candidate.is_dir():
            return candidate
    return Path.cwd() / "mods"
