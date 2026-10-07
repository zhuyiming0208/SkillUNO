"""模组商店集成测试：router 传参 + run_mod_store 清理 stdin + 安装流程。"""
import os
import sys
from unittest.mock import patch, MagicMock

import pytest

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)
SRC_DIR = os.path.join(PROJECT_ROOT, "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from uno.mod_store import input_handler as ih
from uno.mod_store import router as router_module
from uno.mod_store.router import Router, Action


# ==================== Router 传参 ====================
class _RawPage:
    def __init__(self):
        self.calls = []

    def wants_raw_input(self):
        return True

    def render(self):
        return "raw page"

    def handle_key(self, key):
        self.calls.append(key)
        if key.type == ih.EventType.QUIT:
            return Action.QUIT
        return None


class TestRouterPassesRawInput:
    def test_router_passes_raw_input_to_read_key(self, monkeypatch):
        captured = []

        def fake_read_key(raw_input=False):
            captured.append(raw_input)
            return ih.KeyEvent(ih.EventType.QUIT)

        monkeypatch.setattr(router_module.ih, "read_key", fake_read_key)

        page = _RawPage()
        r = Router()
        r.push(page)

        with patch("uno.mod_store.render.clear_screen"):
            r.run()

        assert captured == [True]

    def test_router_passes_false_when_no_method(self, monkeypatch):
        captured = []

        def fake_read_key(raw_input=False):
            captured.append(raw_input)
            return ih.KeyEvent(ih.EventType.QUIT)

        monkeypatch.setattr(router_module.ih, "read_key", fake_read_key)

        class _PlainPage:
            def render(self):
                return "plain"

            def handle_key(self, key):
                if key.type == ih.EventType.QUIT:
                    return Action.QUIT
                return None

        r = Router()
        r.push(_PlainPage())

        with patch("uno.mod_store.render.clear_screen"):
            r.run()

        assert captured == [False]

    def test_router_passes_false_when_wants_raw_false(self, monkeypatch):
        captured = []

        def fake_read_key(raw_input=False):
            captured.append(raw_input)
            return ih.KeyEvent(ih.EventType.QUIT)

        monkeypatch.setattr(router_module.ih, "read_key", fake_read_key)

        class _ResultsPage:
            def wants_raw_input(self):
                return False

            def render(self):
                return "results"

            def handle_key(self, key):
                if key.type == ih.EventType.QUIT:
                    return Action.QUIT
                return None

        r = Router()
        r.push(_ResultsPage())

        with patch("uno.mod_store.render.clear_screen"):
            r.run()

        assert captured == [False]


# ==================== run_mod_store 清理 stdin ====================
class TestRunModStoreDrainsStdin:
    def test_run_mod_store_drains_stdin(self):
        from uno.mod_store import main as store_main

        with patch.object(store_main, "_drain_stdin") as mock_drain, \
             patch.object(store_main, "ModIndex", return_value=MagicMock()), \
             patch.object(store_main, "Router", return_value=MagicMock()), \
             patch.object(store_main, "MainMenu", return_value=MagicMock()):
            store_main.run_mod_store()

        mock_drain.assert_called_once()

    def test_drain_stdin_no_tty(self):
        from uno.mod_store import main as store_main
        store_main._drain_stdin()


# ==================== 安装流程 ====================
class TestRouterInstallFlow:
    def _router(self, monkeypatch):
        r = Router(mod_index=MagicMock(), mods_dir="mods",
                   pending_dir="mods/_pending")
        monkeypatch.setattr(router_module.ih, "read_key",
                            lambda **kw: ih.KeyEvent(ih.EventType.QUIT))
        return r

    def test_detail_install_pushes_confirm(self, monkeypatch):
        from uno.mod_store.detail import DetailPage
        from uno.mod_store.confirm import ConfirmPage
        r = self._router(monkeypatch)
        page = DetailPage({"ID": "X", "name": "X"})
        r.push(page)
        with patch("uno.mod_store.downloader.check_existing",
                   return_value=None):
            r._dispatch("INSTALL")
        assert isinstance(r.current(), ConfirmPage)

    def test_confirm_success_pushes_enable(self, monkeypatch):
        from uno.mod_store.confirm import ConfirmPage
        from uno.mod_store.enable import EnablePage
        r = self._router(monkeypatch)
        page = ConfirmPage({"ID": "X", "name": "X"})
        r.push(page)
        with patch("uno.mod_store.downloader.download_mod",
                   return_value=(True, "mods/_pending/X.py")), \
             patch("uno.mod_store.validator.validate_download",
                   return_value=(True, "", "X")):
            r._dispatch("CONFIRM")
        assert isinstance(r.current(), EnablePage)

    def test_confirm_download_fail_sets_error(self, monkeypatch):
        from uno.mod_store.confirm import ConfirmPage
        r = self._router(monkeypatch)
        page = ConfirmPage({"ID": "X", "name": "X"})
        r.push(page)
        with patch("uno.mod_store.downloader.download_mod",
                   return_value=(False, "网络失败")):
            r._dispatch("CONFIRM")
        assert page.error == "网络失败"
        assert r.current() is page

    def test_confirm_validate_fail_sets_error(self, monkeypatch):
        from uno.mod_store.confirm import ConfirmPage
        r = self._router(monkeypatch)
        page = ConfirmPage({"ID": "X", "name": "X"})
        r.push(page)
        with patch("uno.mod_store.downloader.download_mod",
                   return_value=(True, "p")), \
             patch("uno.mod_store.validator.validate_download",
                   return_value=(False, "语法错误", None)):
            r._dispatch("CONFIRM")
        assert page.error == "语法错误"
        assert r.current() is page

    def test_enable_success_pops_and_shows_message(self, monkeypatch):
        from uno.mod_store.detail import DetailPage
        from uno.mod_store.confirm import ConfirmPage
        from uno.mod_store.enable import EnablePage
        from uno.mod_store.router import MessagePage
        r = self._router(monkeypatch)
        d = DetailPage({"ID": "X", "name": "X"})
        c = ConfirmPage({"ID": "X", "name": "X"})
        e = EnablePage("X", "mods/_pending/X.py")
        r.push(d)
        r.push(c)
        r.push(e)
        with patch("uno.mod_store.downloader.enable_mod",
                   return_value=(True, "mods/X.py")):
            r._dispatch("ENABLE")
        assert isinstance(r.current(), MessagePage)
        assert "已启用" in r.current().message

    def test_keep_pending_pops_and_shows_message(self, monkeypatch):
        from uno.mod_store.detail import DetailPage
        from uno.mod_store.confirm import ConfirmPage
        from uno.mod_store.enable import EnablePage
        from uno.mod_store.router import MessagePage
        r = self._router(monkeypatch)
        d = DetailPage({"ID": "X", "name": "X"})
        c = ConfirmPage({"ID": "X", "name": "X"})
        e = EnablePage("X", "p")
        r.push(d)
        r.push(c)
        r.push(e)
        r._dispatch("KEEP_PENDING")
        assert isinstance(r.current(), MessagePage)
        assert "保留" in r.current().message

    def test_enable_fail_sets_error(self, monkeypatch):
        from uno.mod_store.detail import DetailPage
        from uno.mod_store.confirm import ConfirmPage
        from uno.mod_store.enable import EnablePage
        r = self._router(monkeypatch)
        d = DetailPage({"ID": "X", "name": "X"})
        c = ConfirmPage({"ID": "X", "name": "X"})
        e = EnablePage("X", "p")
        r.push(d)
        r.push(c)
        r.push(e)
        with patch("uno.mod_store.downloader.enable_mod",
                   return_value=(False, "备份失败")):
            r._dispatch("ENABLE")
        assert e.error == "备份失败"
        assert r.current() is e


# ==================== MessagePage ====================
class TestMessagePage:
    def test_render(self):
        from uno.mod_store.router import MessagePage
        text = MessagePage("测试消息").render()
        assert "测试消息" in text

    def test_any_key_returns_back(self):
        from uno.mod_store.router import MessagePage
        page = MessagePage("X")
        assert page.handle_key(ih.KeyEvent(ih.EventType.CHAR, "z")) == Action.BACK