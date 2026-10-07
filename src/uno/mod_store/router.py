"""页面栈与路由。"""
import os

from uno.mod_store.render import clear_screen, draw_box
from uno.mod_store import input_handler as ih


class Action:
    QUIT = "QUIT"
    BACK = "BACK"
    SEARCH = "SEARCH"
    HELP = "HELP"
    HISTORY = "HISTORY"
    DETAIL = "DETAIL"


class MessagePage:
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
    def __init__(self, mod_index=None, mods_dir="mods", pending_dir=None,
                 history_path=None):
        self.stack = []
        self.running = True
        self.mod_index = mod_index
        self.mods_dir = mods_dir
        self.pending_dir = pending_dir or os.path.join(mods_dir, "_pending")
        self.history_path = history_path or os.path.join(mods_dir, "history.json")

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
            self.push(SearchPage(self.mod_index, self.history_path))
            return
        if action == Action.DETAIL:
            if payload is None:
                return
            from uno.mod_store.detail import DetailPage
            self.push(DetailPage(payload, self.mod_index, self.history_path))
            return
        if action == Action.HISTORY:
            from uno.mod_store.history_view import HistoryPage
            self.push(HistoryPage(self.history_path, self.mod_index))
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
        return

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
        self.push(ConfirmPage(mod, existing=existing,
                              mod_index=self.mod_index,
                              history_path=self.history_path))

    def _handle_confirm(self):
        page = self.current()
        mod = getattr(page, "mod", None)
        if mod is None:
            return
        from uno.mod_store.downloader import download_mod
        from uno.mod_store.validator import validate_download
        from uno.mod_store.enable import EnablePage
        from uno.mod_store.history import add_record
        print("正在下载...")
        ok, msg = download_mod(mod, pending_dir=self.pending_dir,
                               mods_dir=self.mods_dir)
        if not ok:
            page.error = msg
            return
        ok, err, sid = validate_download(msg, mods_dir=self.mods_dir)
        if not ok:
            page.error = err
            return
        try:
            add_record(mod, "downloaded", "pending", self.history_path)
        except ValueError as e:
            print(f"警告：无法记录历史 — {e}")
        self.push(EnablePage(sid, msg))

    def _handle_enable(self):
        page = self.current()
        sid = getattr(page, "season_id", None)
        if sid is None:
            return
        from uno.mod_store.downloader import enable_mod
        from uno.mod_store.history import add_record
        ok, msg = enable_mod(sid, mods_dir=self.mods_dir,
                             pending_dir=self.pending_dir)
        if not ok:
            page.error = msg
            return
        mod_data = None
        for p in reversed(self.stack):
            if hasattr(p, "mod"):
                mod_data = p.mod
                break
        if mod_data is not None:
            try:
                add_record(mod_data, "enabled", "enabled", self.history_path)
            except ValueError as e:
                print(f"警告：无法记录历史 — {e}")
        if self.stack:
            self.pop()
        if self.stack:
            self.pop()
        self.push(MessagePage(f"已启用，重启游戏生效。\n路径：{msg}"))

    def _handle_keep_pending(self):
        from uno.mod_store.history import add_record
        mod_data = None
        for p in reversed(self.stack):
            if hasattr(p, "mod"):
                mod_data = p.mod
                break
        if mod_data is not None:
            try:
                add_record(mod_data, "kept_pending", "pending", self.history_path)
            except ValueError as e:
                print(f"警告：无法记录历史 — {e}")
        if self.stack:
            self.pop()
        if self.stack:
            self.pop()
        self.push(MessagePage("已保留在 _pending/，未启用。"))

    def _flash(self, message):
        self.push(MessagePage(message))
