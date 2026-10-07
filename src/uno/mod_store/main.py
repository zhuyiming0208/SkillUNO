"""模组商店入口。"""
from pathlib import Path

from uno.mod_index import ModIndex
from uno.mod_store.router import Router
from uno.mod_store.menu import MainMenu


def _find_mods_dir() -> Path:
    """从当前文件向上查找 mods/ 目录。

    避免硬编码 "mods" 相对路径，在 CI 和本地行为一致。
    """
    current = Path(__file__).resolve()
    for parent in current.parents:
        candidate = parent / "mods"
        if candidate.is_dir():
            return candidate
    # 兜底：当前工作目录下的 mods
    return Path.cwd() / "mods"


def run_mod_store():
    """启动模组商店 CLI。"""
    mods_dir = _find_mods_dir()
    mod_index = ModIndex(mods_dir=str(mods_dir))

    router = Router(mod_index=mod_index)     # ← 传进去
    router.push(MainMenu(mod_index))
    router.run()


if __name__ == "__main__":
    run_mod_store()