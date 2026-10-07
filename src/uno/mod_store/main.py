"""模组商店入口。"""
import os
import sys
from pathlib import Path

from uno.mod_index import ModIndex
from uno.mod_store.router import Router
from uno.mod_store.menu import MainMenu


def _find_mods_dir() -> Path:
    current = Path(__file__).resolve()
    for parent in current.parents:
        candidate = parent / "mods"
        if candidate.is_dir():
            return candidate
    return Path.cwd() / "mods"


def _drain_stdin():
    """清空 stdin 缓冲区里残留的字节。

    主菜单用 input() 读键盘，进入商店切到 raw 模式后，
    input() 遗留的回车等字节会干扰第一次 read_key()。
    进入商店前清一次。
    """
    try:
        import select
        fd = sys.stdin.fileno()
        for _ in range(64):
            if not select.select([fd], [], [], 0)[0]:
                break
            if not os.read(fd, 1):
                break
    except Exception:
        pass


def run_mod_store():
    """启动模组商店 CLI。"""
    _drain_stdin()
    mods_dir = _find_mods_dir()
    pending_dir = mods_dir / "_pending"
    mod_index = ModIndex(mods_dir=str(mods_dir))

    router = Router(
        mod_index=mod_index,
        mods_dir=str(mods_dir),
        pending_dir=str(pending_dir),
    )
    router.push(MainMenu(mod_index))
    router.run()


if __name__ == "__main__":
    run_mod_store()
