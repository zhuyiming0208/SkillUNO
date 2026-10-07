"""模组商店集成测试：router 传参 + run_mod_store 清理 stdin。"""
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


class _RawPage:
    """模拟一个要求 raw_input 的页面。"""

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
        """页面 wants_raw_input=True 时，router 传 raw_input=True 给 read_key。"""
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

        assert captured == [True], f"预期 raw_input=True，实际 {captured}"

    def test_router_passes_false_when_no_method(self, monkeypatch):
        """页面无 wants_raw_input 方法时，传 raw_input=False。"""
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
        """页面 wants_raw_input() 返回 False 时，传 raw_input=False。"""
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


class TestRunModStoreDrainsStdin:
    def test_run_mod_store_drains_stdin(self):
        """run_mod_store() 应调用 _drain_stdin()。"""
        from uno.mod_store import main as store_main

        with patch.object(store_main, "_drain_stdin") as mock_drain, \
             patch.object(store_main, "ModIndex", return_value=MagicMock()), \
             patch.object(store_main, "Router", return_value=MagicMock()), \
             patch.object(store_main, "MainMenu", return_value=MagicMock()):
            store_main.run_mod_store()

        mock_drain.assert_called_once()

    def test_drain_stdin_no_tty(self):
        """_drain_stdin 在无 TTY 环境下不崩。"""
        from uno.mod_store import main as store_main
        # 直接调用，CI 环境无残留字节，正常返回
        store_main._drain_stdin()
