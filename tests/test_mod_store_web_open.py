"""测试 web_open 模块 + W 键 + OPEN_WEB 动作。"""
import os
import sys
from unittest.mock import patch, MagicMock

import pytest

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)
SRC_DIR = os.path.join(PROJECT_ROOT, "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from uno.mod_store import web_open as wo
from uno.mod_store import input_handler as ih
from uno.mod_store.router import Action, Router, MessagePage


class TestOpenWebStore:
    def test_success(self):
        with patch("webbrowser.open", return_value=True):
            ok, msg = wo.open_web_store()
        assert ok is True
        assert wo.WEB_URL in msg

    def test_returns_false(self):
        with patch("webbrowser.open", return_value=False):
            ok, msg = wo.open_web_store()
        assert ok is False
        assert wo.WEB_URL in msg

    def test_exception(self):
        with patch("webbrowser.open", side_effect=RuntimeError("boom")):
            ok, msg = wo.open_web_store()
        assert ok is False
        assert wo.WEB_URL in msg


class TestActionConstant:
    def test_open_web_exists(self):
        assert hasattr(Action, "OPEN_WEB")
        assert isinstance(Action.OPEN_WEB, str)
        assert Action.OPEN_WEB == "OPEN_WEB"


class TestMenuHandlesW:
    def _menu(self):
        from uno.mod_store.menu import MainMenu

        class Idx:
            def get_official(self):
                return []
            def get_handpicked(self):
                return []

        return MainMenu(Idx())

    def test_w_returns_open_web(self):
        result = self._menu().handle_key(ih.KeyEvent(ih.EventType.CHAR, "w"))
        assert result == Action.OPEN_WEB

    def test_uppercase_w(self):
        result = self._menu().handle_key(ih.KeyEvent(ih.EventType.CHAR, "W"))
        assert result == Action.OPEN_WEB


class TestRouterDispatchOpenWeb:
    def test_dispatch_pushes_message(self):
        r = Router(mod_index=MagicMock(), mods_dir="mods")
        with patch("uno.mod_store.web_open.open_web_store",
                   return_value=(False, "手动访问 URL")):
            r._dispatch(Action.OPEN_WEB)
        assert isinstance(r.current(), MessagePage)
