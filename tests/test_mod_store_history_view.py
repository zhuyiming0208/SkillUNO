"""测试 HistoryPage。"""
import os
import sys
from unittest.mock import MagicMock

import pytest

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)
SRC_DIR = os.path.join(PROJECT_ROOT, "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from uno.mod_store import input_handler as ih
from uno.mod_store import history as hs
from uno.mod_store.history_view import HistoryPage
from uno.mod_store.router import Action


def _mod(id_="X"):
    return {"ID": id_, "name": "N", "author": "a",
            "version": "1.0.0", "repo": "r"}


class TestRender:
    def test_empty(self, tmp_path):
        p = str(tmp_path / "h.json")
        assert "暂无下载历史" in HistoryPage(p, MagicMock()).render()

    def test_with_record(self, tmp_path):
        p = str(tmp_path / "h.json")
        hs.add_record(_mod(), "downloaded", "pending", p)
        text = HistoryPage(p, MagicMock()).render()
        assert "N" in text
        assert "1.0.0" in text

    def test_status_mark(self, tmp_path):
        p = str(tmp_path / "h.json")
        hs.add_record(_mod(), "enabled", "enabled", p)
        assert "✓" in HistoryPage(p, MagicMock()).render()

    def test_action_label(self, tmp_path):
        p = str(tmp_path / "h.json")
        hs.add_record(_mod(), "downloaded", "pending", p)
        assert "下载" in HistoryPage(p, MagicMock()).render()

    def test_over_50(self, tmp_path):
        p = str(tmp_path / "h.json")
        for i in range(55):
            hs.add_record(_mod(id_=f"M{i}"), "downloaded", "pending", p)
        assert "仅显示最近 50 条" in HistoryPage(p, MagicMock()).render()

    def test_time_no_seconds(self, tmp_path):
        p = str(tmp_path / "h.json")
        hs.add_record(_mod(), "downloaded", "pending", p)
        text = HistoryPage(p, MagicMock()).render()
        import re
        assert not re.search(r"\d{2}:\d{2}:\d{2}", text)


class TestKeys:
    def test_down_moves(self, tmp_path):
        p = str(tmp_path / "h.json")
        hs.add_record(_mod(id_="A"), "downloaded", "pending", p)
        hs.add_record(_mod(id_="B"), "downloaded", "pending", p)
        page = HistoryPage(p, MagicMock())
        page.handle_key(ih.KeyEvent(ih.EventType.DOWN))
        assert page.selected == 1

    def test_q_returns_back(self, tmp_path):
        p = str(tmp_path / "h.json")
        page = HistoryPage(p, MagicMock())
        assert page.handle_key(ih.KeyEvent(ih.EventType.QUIT)) == Action.BACK

    def test_esc_returns_back(self, tmp_path):
        p = str(tmp_path / "h.json")
        page = HistoryPage(p, MagicMock())
        assert page.handle_key(ih.KeyEvent(ih.EventType.BACK)) == Action.BACK

    def test_enter_missing_mod(self, tmp_path):
        p = str(tmp_path / "h.json")
        hs.add_record(_mod(), "downloaded", "pending", p)
        idx = MagicMock()
        idx.get_by_id.return_value = None
        page = HistoryPage(p, idx)
        assert page.handle_key(ih.KeyEvent(ih.EventType.ENTER)) is None
        assert "不在索引" in page.render()

    def test_enter_exception(self, tmp_path):
        p = str(tmp_path / "h.json")
        hs.add_record(_mod(), "downloaded", "pending", p)
        idx = MagicMock()
        idx.get_by_id.side_effect = RuntimeError("boom")
        page = HistoryPage(p, idx)
        assert page.handle_key(ih.KeyEvent(ih.EventType.ENTER)) is None

    def test_enter_returns_tuple(self, tmp_path):
        p = str(tmp_path / "h.json")
        hs.add_record(_mod(), "downloaded", "pending", p)
        idx = MagicMock()
        idx.get_by_id.return_value = _mod()
        page = HistoryPage(p, idx)
        result = page.handle_key(ih.KeyEvent(ih.EventType.ENTER))
        assert isinstance(result, tuple)
        assert result[0] == Action.DETAIL
