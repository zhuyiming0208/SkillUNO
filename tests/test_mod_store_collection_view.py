"""测试 CollectionView。"""
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
from uno.mod_store.collection_view import CollectionView
from uno.mod_store.router import Action
from uno.mod_store.context import StoreContext


def _coll():
    return {
        "id": "NEWBIE",
        "name": "新手包",
        "description": "入门模组集",
        "mods": ["S1", "EXAMPLE"],
    }


def _ctx(tmp_path):
    return StoreContext(
        mod_index=MagicMock(),
        history_path=str(tmp_path / "h.json"),
        enabled_path=str(tmp_path / "e.json"),
        collections_path=str(tmp_path / "c.json"),
    )


class TestRender:
    def test_name(self, tmp_path):
        text = CollectionView(_ctx(tmp_path), _coll()).render()
        assert "新手包" in text

    def test_description(self, tmp_path):
        text = CollectionView(_ctx(tmp_path), _coll()).render()
        assert "入门模组集" in text

    def test_mods_listed(self, tmp_path):
        text = CollectionView(_ctx(tmp_path), _coll()).render()
        assert "S1" in text
        assert "EXAMPLE" in text

    def test_action_bar(self, tmp_path):
        text = CollectionView(_ctx(tmp_path), _coll()).render()
        assert "一键安装全部" in text


class TestKeys:
    def test_i_returns_install_all(self, tmp_path):
        page = CollectionView(_ctx(tmp_path), _coll())
        result = page.handle_key(ih.KeyEvent(ih.EventType.CHAR, "i"))
        assert isinstance(result, tuple)
        assert result[0] == Action.INSTALL_ALL
        assert result[1]["id"] == "NEWBIE"

    def test_q_returns_back(self, tmp_path):
        page = CollectionView(_ctx(tmp_path), _coll())
        assert page.handle_key(ih.KeyEvent(ih.EventType.QUIT)) == Action.BACK

    def test_esc_returns_back(self, tmp_path):
        page = CollectionView(_ctx(tmp_path), _coll())
        assert page.handle_key(ih.KeyEvent(ih.EventType.BACK)) == Action.BACK

    def test_char_q_returns_back(self, tmp_path):
        page = CollectionView(_ctx(tmp_path), _coll())
        assert page.handle_key(ih.KeyEvent(ih.EventType.CHAR, "q")) == Action.BACK

    def test_other_char_returns_none(self, tmp_path):
        page = CollectionView(_ctx(tmp_path), _coll())
        assert page.handle_key(ih.KeyEvent(ih.EventType.CHAR, "z")) is None
