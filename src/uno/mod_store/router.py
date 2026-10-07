"""页面栈与路由。"""
import os

from uno.mod_store.render import clear_screen, draw_box
from uno.mod_store import input_handler as ih


class Action:
    QUIT = "QUIT"
    BACK = "BACK"
    SEARCH = "SEARCH"
    HELP = "HELP"
    DETAIL = "DETAIL"
    HISTORY = "HISTORY"


class MessagePage:
    """简单消息页：任意键返回。"""

    BOX_WIDTH = 74

    def __init__(self, message):
        self.message = message

    def render(self):
        lines = self.message.split("\n")
        lines.append("")
        lines.append("按任意键继续...")
        return draw_box(lines, self.BOX_WIDTH)

    def handle_key(self, key):
        return Action.BACK


class Router:
    def __init__(self, mod_index=None, mods_dir="mods", pending_dir=None):
        self.stack = []
        self.running = True
        self.mod_index = mod_index
        self.mods_dir = mods_dir
        self.pending_dir = pending_dir or os.path.join(mods_dir, "_pending")

    def push(self, page):
        self.stack.append(page)

    def pop(self):
        if self.stack:
            return self.stack.pop()
        return None

    def current(self):
        return self.stack[-1] if self.stack else None

    def run(self):
        try:
            while self.running and self.stack:
                page = self.current()
                clear_screen()
                print(page.render())

                raw = page.wants_raw_input() if hasattr(page, "wants_raw_input") else False
                event = ih.read_key(raw_input=raw)
                if event is None:
                    break

                if event.type == ih.EventType.QUIT:
                    self.running = False
                    break

                result = page.handle_key(event)
                self._dispatch(result)
        except KeyboardInterrupt:
            pass
        finally:
            clear_screen()

    # ---------- 分发 ----------
    def _dispatch(self, result):
        if result is None:
            return

        if isinstance(result, tuple):
            action, payload = result
        else:
            action, payload = result, None

        if action == Action.QUIT:
            self.running = False
            return

        if action == Action.BACK:
            self.pop()
            if not self.stack:
                self.running = False
            return

        if action == Action.SEARCH:
            if self.mod_index is None:
                self._flash("错误：模组索引未初始化，无法搜索。")
                return
            from uno.mod_store.search import SearchPage
            self.push(SearchPage(self.mod_index))
            return

        if action == Action.DETAIL:
            if payload is None:
                return
            from uno.mod_store.detail import DetailPage
            self.push(DetailPage(payload, self.mod_index))
            return

        if action == "INSTALL":
            self._handle_install()
            return

        if action == "CONFIRM":
            self._handle_confirm()
            return

        if action == "ENABLE":
            self._handle_enable()
            return

        if action == "KEEP_PENDING":
            self._handle_keep_pending()
            return

        # VIEW_SOURCE / HELP / HISTORY 未实现
        return

    # ---------- 具体流程 ----------
    def _handle_install(self):
        page = self.current()
        mod = getattr(page, "mod", None)
        if mod is None:
            return
        from uno.mod_store.downloader import check_existing
        from uno.mod_store.confirm import ConfirmPage
        existing = check_existing(
            mod.get("ID", ""),
            mods_dir=self.mods_dir,
            pending_dir=self.pending_dir,
        )
        self.push(ConfirmPage(mod, existing=existing))

    def _handle_confirm(self):
        page = self.current()
        mod = getattr(page, "mod", None)
        if mod is None:
            return

        from uno.mod_store.downloader import download_mod
        from uno.mod_store.validator import validate_download
        from uno.mod_store.enable import EnablePage

        print("正在下载...")
        ok, msg = download_mod(
            mod,
            pending_dir=self.pending_dir,
            mods_dir=self.mods_dir,
        )
        if not ok:
            page.error = msg
            return

        ok, err, sid = validate_download(msg, mods_dir=self.mods_dir)
        if not ok:
            page.error = err
            return

        self.push(EnablePage(sid, msg))

    def _handle_enable(self):
        page = self.current()
        sid = getattr(page, "season_id", None)
        if sid is None:
            return

        from uno.mod_store.downloader import enable_mod
        ok, msg = enable_mod(
            sid,
            mods_dir=self.mods_dir,
            pending_dir=self.pending_dir,
        )
        if not ok:
            page.error = msg
            return

        # 成功：弹出 EnablePage、ConfirmPage
        if len(self.stack) >= 1:
            self.pop()
        if len(self.stack) >= 1:
            self.pop()
        self.push(MessagePage(f"已启用，重启游戏生效。\n路径：{msg}"))

    def _handle_keep_pending(self):
        if len(self.stack) >= 1:
            self.pop()
        if len(self.stack) >= 1:
            self.pop()
        self.push(MessagePage("已保留在 _pending/，未启用。"))

    def _flash(self, message):
        self.push(MessagePage(message))