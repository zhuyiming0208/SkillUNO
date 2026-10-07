"""测试卸载确认页。"""
import os
import sys
from unittest.mock import MagicMock

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)
SRC_DIR = os.path.join(PROJECT_ROOT, "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from uno.mod_store import input_handler as ih
from uno.mod_store.uninstall_confirm import UninstallConfirmPage
from uno.mod_store.context import StoreContext


def _mod():
    return {"ID": "X", "name": "测试", "version": "1.0.0",
            "author": "a", "repo": "r"}


def _ctx(tmp_path):
    return StoreContext(
        mod_index=MagicMock(),
        history_path=str(tmp_path / "h.json"),
        enabled_path=str(tmp_path / "e.json"),
        collections_path=str(tmp_path / "c.json"),
    )


class TestRender:
    def test_name(self, tmp_path):
        text = UninstallConfirmPage(_ctx(tmp_path), _mod()).render()
        assert "测试" in text

    def test_version(self, tmp_path):
        text = UninstallConfirmPage(_ctx(tmp_path), _mod()).render()
        assert "1.0.0" in text

    def test_paths(self, tmp_path):
        text = UninstallConfirmPage(_ctx(tmp_path), _mod()).render()
        assert "X.py" in text
        assert "_pending" in text

    def test_security_message(self, tmp_path):
        text = UninstallConfirmPage(_ctx(tmp_path), _mod()).render()
        assert "卸载后" in text

    def test_history_kept(self, tmp_path):
        text = UninstallConfirmPage(_ctx(tmp_path), _mod()).render()
        assert "历史记录保留" in text


class TestKeys:
    def test_y(self, tmp_path):
        page = UninstallConfirmPage(_ctx(tmp_path), _mod())
        assert page.handle_key(ih.KeyEvent(ih.EventType.CHAR, "y")) == "CONFIRM"

    def test_n(self, tmp_path):
        page = UninstallConfirmPage(_ctx(tmp_path), _mod())
        assert page.handle_key(ih.KeyEvent(ih.EventType.CHAR, "n")) == "BACK"

    def test_esc(self, tmp_path):
        page = UninstallConfirmPage(_ctx(tmp_path), _mod())
        assert page.handle_key(ih.KeyEvent(ih.EventType.BACK)) == "BACK"
