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


def _drain_stdin():
    """清空 stdin 缓冲区里残留的字节。

    主菜单用 input() 读键盘，进入商店切到 raw 模式后，
    input() 遗留的回车等字节会干扰第一次 read_key()。
    进入商店前清一次。
    """
    import sys
    import os
    try:
        import select
        fd = sys.stdin.fileno()
        # 非阻塞地读掉所有待读字节（最多读 64 个防死循环）
        for _ in range(64):
            if not select.select([fd], [], [], 0)[0]:
                break
            if not os.read(fd, 1):
                break
    except Exception:
        pass


def run_mod_store():
    """启动模组商店 CLI。"""
    _drain_stdin()          # 清残留字节，防止第一次 read_key 误触发
    mods_dir = _find_mods_dir()
    mod_index = ModIndex(mods_dir=str(mods_dir))

    router = Router(mod_index=mod_index)
    router.push(MainMenu(mod_index))
    router.run()
