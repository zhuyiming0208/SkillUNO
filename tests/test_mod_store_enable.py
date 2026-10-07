"""测试 EnablePage。"""
import os
import sys

import pytest

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)
SRC_DIR = os.path.join(PROJECT_ROOT, "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from uno.mod_store import input_handler as ih
from uno.mod_store.enable import EnablePage


class TestEnableRender:
    def test_basic(self):
        text = EnablePage("X", "mods/_pending/X.py").render()
        assert "mods/_pending/X.py" in text
        assert "X" in text

    def test_season_id_shown(self):
        text = EnablePage("MYMOD", "mods/_pending/MYMOD.py").render()
        assert "MYMOD" in text

    def test_security_message(self):
        text = EnablePage("X", "mods/_pending/X.py").render()
        assert "启用后，模组代码将在游戏下次启动时执行" in text
        assert "请确认作者可信" in text

    def test_restart_hint(self):
        text = EnablePage("X", "mods/_pending/X.py").render()
        assert "重启" in text

    def test_error_shown(self):
        page = EnablePage("X", "p")
        page.error = "移动失败"
        text = page.render()
        assert "移动失败" in text
        assert "按任意键" in text


class TestEnableKeys:
    def test_y_returns_enable(self):
        page = EnablePage("X", "p")
        assert page.handle_key(ih.KeyEvent(ih.EventType.CHAR, "y")) == "ENABLE"

    def test_uppercase_y(self):
        page = EnablePage("X", "p")
        assert page.handle_key(ih.KeyEvent(ih.EventType.CHAR, "Y")) == "ENABLE"

    def test_n_returns_keep_pending(self):
        page = EnablePage("X", "p")
        assert page.handle_key(ih.KeyEvent(ih.EventType.CHAR, "n")) == "KEEP_PENDING"

    def test_esc_returns_keep_pending(self):
        page = EnablePage("X", "p")
        assert page.handle_key(ih.KeyEvent(ih.EventType.BACK)) == "KEEP_PENDING"

    def test_quit_returns_keep_pending(self):
        page = EnablePage("X", "p")
        assert page.handle_key(ih.KeyEvent(ih.EventType.QUIT)) == "KEEP_PENDING"

    def test_other_char_returns_none(self):
        page = EnablePage("X", "p")
        assert page.handle_key(ih.KeyEvent(ih.EventType.CHAR, "z")) is None

    def test_error_clears_on_any_key(self):
        page = EnablePage("X", "p")
        page.error = "boom"
        page.handle_key(ih.KeyEvent(ih.EventType.CHAR, "z"))
        assert page.error is None