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
    UPDATE = "UPDATE"
    TOGGLE_ENABLE = "TOGGLE_ENABLE"
    UNINSTALL_CONFIRM = "UNINSTALL_CONFIRM"
    COLLECTION = "COLLECTION"
    INSTALL_ALL = "INSTALL_ALL"


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
                 history_path=None, enabled_path=None, collections_path=None):
        self.stack = []
        self.running = True
        self.mod_index = mod_index
        self.mods_dir = mods_dir
        self.pending_dir = pending_dir or os.path.join(mods_dir, "_pending")
        self.history_path = history_path or os.path.join(mods_dir, "history.json")
        self.enabled_path = enabled_path or os.path.join(mods_dir, "enabled.json")
        self.collections_path = collections_path or os.path.join(mods_dir, "collections.json")

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
            self.push(DetailPage(payload, self.mod_index, self.history_path,
                                 enabled_path=self.enabled_path))
            return
        if action == Action.HISTORY:
            from uno.mod_store.history_view import HistoryPage
            self.push(HistoryPage(self.history_path, self.mod_index))
            return
        if action == Action.UPDATE:
            self._handle_update(payload)
            return

        if action == Action.TOGGLE_ENABLE:
            self._handle_toggle_enable(payload)
            return

        if action == Action.UNINSTALL_CONFIRM:
            self._handle_uninstall_confirm(payload)
            return

        if action == Action.COLLECTION:
            self._handle_collection(payload)
            return

        if action == Action.INSTALL_ALL:
            self._handle_install_all(payload)
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
        self._refresh_menus()
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
        self._refresh_menus()
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
        self._refresh_menus()
        self.push(MessagePage("已保留在 _pending/，未启用。"))

    def _flash(self, message):
        self.push(MessagePage(message))


    def _refresh_menus(self):
        """让栈里所有 MainMenu 重新计算状态。"""
        for p in self.stack:
            if hasattr(p, "refresh_updates"):
                try:
                    p.refresh_updates()
                except Exception:
                    pass

    def _handle_update(self, payload):
        if not payload:
            return
        mod = payload.get("mod_data")
        if mod is None:
            return
        from uno.mod_store.downloader import check_existing
        from uno.mod_store.confirm import ConfirmPage
        existing = check_existing(
            mod.get("ID", ""),
            mods_dir=self.mods_dir,
            pending_dir=self.pending_dir,
        )
        self.push(ConfirmPage(
            mod,
            existing=existing,
            mod_index=self.mod_index,
            history_path=self.history_path,
            is_update=True,
            local_version=payload.get("local_version"),
            latest_version=payload.get("latest_version"),
        ))

    def _handle_toggle_enable(self, mod):
        if not mod:
            return
        mod_id = mod.get("ID", "")
        if not mod_id:
            return
        from uno.enabled import is_mod_enabled, set_mod_enabled
        try:
            current = is_mod_enabled(mod_id, self.enabled_path)
            set_mod_enabled(mod_id, not current, self.enabled_path)
            self._refresh_menus()
            name = mod.get("name", mod_id)
            if current:
                msg = f"已禁用 {name}，重启游戏生效"
            else:
                msg = f"已启用 {name}，重启游戏生效"
            self.push(MessagePage(msg))
        except Exception as e:
            self.push(MessagePage(f"切换失败：{e}"))

    def _handle_uninstall_confirm(self, mod):
        if not mod:
            return
        from uno.mod_store.uninstall_confirm import UninstallConfirmPage
        from uno.mod_store.context import StoreContext
        ctx = StoreContext(
            mod_index=self.mod_index,
            history_path=self.history_path,
            enabled_path=self.enabled_path,
            collections_path=os.path.join(self.mods_dir, "collections.json"),
        )
        self.push(UninstallConfirmPage(ctx, mod))


    def _handle_collection(self, coll):
        if not coll:
            return
        from uno.mod_store.context import StoreContext
        from uno.mod_store.collection_view import CollectionView
        ctx = StoreContext(
            mod_index=self.mod_index,
            history_path=self.history_path,
            enabled_path=self.enabled_path,
            collections_path=self.collections_path,
        )
        self.push(CollectionView(ctx, coll))

    def _handle_install_all(self, coll):
        if not coll:
            return
        from uno.mod_store.downloader import download_mod, enable_mod
        from uno.mod_store.validator import validate_download
        from uno.mod_store.history import add_record

        mods = coll.get("mods", [])
        total = len(mods)
        success = []
        failed = []

        for i, mod_id in enumerate(mods, 1):
            if mod_id in {"S1", "S2", "S3", "S4"}:
                continue
            try:
                mod_data = self.mod_index.get_by_id(mod_id)
            except Exception:
                mod_data = None
            if mod_data is None:
                print(f"[{i}/{total}] 跳过 {mod_id}（索引中不存在）")
                failed.append((mod_id, "索引中不存在"))
                continue

            name = mod_data.get("name", mod_id)
            print(f"[{i}/{total}] 正在安装 {name} ...")

            ok, msg = download_mod(
                mod_data, pending_dir=self.pending_dir, mods_dir=self.mods_dir)
            if not ok:
                print(f"  ✗ {name} 失败：{msg}")
                failed.append((name, msg))
                continue

            ok, err, sid = validate_download(msg, mods_dir=self.mods_dir)
            if not ok:
                print(f"  ✗ {name} 验证失败：{err}（文件保留在 _pending/）")
                failed.append((name, err))
                continue

            ok, emsg = enable_mod(sid, mods_dir=self.mods_dir,
                                  pending_dir=self.pending_dir)
            if not ok:
                print(f"  ✗ {name} 启用失败：{emsg}")
                failed.append((name, emsg))
                continue

            try:
                add_record(mod_data, "downloaded", "pending", self.history_path)
            except ValueError as e:
                print(f"  警告：无法记录历史 — {e}")
            print(f"  ✓ {name} 成功")
            success.append(name)

        self._refresh_menus()
        lines = [f"安装完成：成功 {len(success)} 个，失败 {len(failed)} 个"]
        if failed:
            lines.append("")
            lines.append("失败列表：")
            for name, reason in failed:
                lines.append(f"  - {name}：{reason}")
        self.push(MessagePage("\n".join(lines)))
