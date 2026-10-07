"""测试 mod_store.menu 与 input_handler。"""
import os
import sys
from unittest.mock import patch

import pytest

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)
SRC_DIR = os.path.join(PROJECT_ROOT, "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from uno.mod_store import input_handler as ih
from uno.mod_store.menu import MainMenu
from uno.mod_store.router import Action


class FakeModIndex:
    """固定数据的假 ModIndex。"""

    def __init__(self, official=None, handpicked=None):
        if official is None:
            official = [
                {"id": "S1", "name": "经典赛季", "skills": 16, "builtin": True},
                {"id": "S2", "name": "被动觉醒", "skills": 8, "builtin": True},
                {"id": "S4", "name": "补丁赛季", "skills": 8, "builtin": True},
            ]
        if handpicked is None:
            handpicked = [
                {"ID": "EXAMPLE", "name": "示例模组", "author": "example_author",
                 "version": "1.0.0", "skills": 3, "description": "d"},
            ]
        self._official = official
        self._handpicked = handpicked

    def get_official(self):
        return list(self._official)

    def get_handpicked(self):
        return list(self._handpicked)

    def get_all(self):
        return self.get_official() + self.get_handpicked()


def _make_menu():
    return MainMenu(FakeModIndex())


# ---------- 渲染 ----------
class TestMenuRender:
    def test_contains_official_names(self):
        text = _make_menu().render()
        assert "经典赛季" in text
        assert "被动觉醒" in text
        assert "补丁赛季" in text

    def test_contains_handpicked_name(self):
        text = _make_menu().render()
        assert "示例模组" in text
        assert "example_author" in text

    def test_contains_action_bar(self):
        text = _make_menu().render()
        assert "搜索" in text
        assert "退出" in text

    def test_empty_handpicked(self):
        menu = MainMenu(FakeModIndex(handpicked=[]))
        text = menu.render()
        assert "暂无精选模组" in text

    def test_empty_official(self):
        menu = MainMenu(FakeModIndex(official=[]))
        text = menu.render()
        assert "暂无官方模组" in text


# ---------- 选中项 ----------
class TestMenuSelection:
    def test_initial_selection_zero(self):
        assert _make_menu().selected == 0

    def test_down_moves_selection(self):
        menu = _make_menu()
        menu.handle_key(ih.KeyEvent(ih.EventType.DOWN))
        assert menu.selected == 1

    def test_up_wraps_to_bottom(self):
        menu = _make_menu()
        menu.handle_key(ih.KeyEvent(ih.EventType.UP))
        assert menu.selected == menu.total_items - 1

    def test_down_wraps_to_top(self):
        menu = _make_menu()
        for _ in range(menu.total_items):
            menu.handle_key(ih.KeyEvent(ih.EventType.DOWN))
        assert menu.selected == 0

    def test_down_never_exceeds(self):
        menu = _make_menu()
        for _ in range(100):
            menu.handle_key(ih.KeyEvent(ih.EventType.DOWN))
        assert 0 <= menu.selected < menu.total_items


# ---------- 动作 ----------
class TestMenuActions:
    def test_quit(self):
        assert _make_menu().handle_key(ih.KeyEvent(ih.EventType.QUIT)) == Action.QUIT

    def test_search(self):
        assert _make_menu().handle_key(ih.KeyEvent(ih.EventType.SEARCH)) == Action.SEARCH

    def test_help(self):
        # 阶段五：H 键现在跳转历史页
        assert _make_menu().handle_key(ih.KeyEvent(ih.EventType.HELP)) == Action.HISTORY

    def test_enter_returns_detail(self):
        result = _make_menu().handle_key(ih.KeyEvent(ih.EventType.ENTER))
        # 阶段三：返回 (Action.DETAIL, mod_data) 元组
        assert isinstance(result, tuple)
        action, payload = result
        assert action == Action.DETAIL
        assert payload is not None
        assert payload.get("id") == "S1" or payload.get("ID") == "S1"

    def test_back_returns_quit_on_main_menu(self):
        assert _make_menu().handle_key(ih.KeyEvent(ih.EventType.BACK)) == Action.QUIT


# ---------- 分页 ----------
class TestPagination:
    def _make_many(self, n):
        return [
            {"ID": f"M{i}", "name": f"模组{i}", "author": "a",
             "version": "1.0.0", "skills": 1, "description": "d"}
            for i in range(n)
        ]

    def test_more_than_12_handpicked_shows_warning(self, capsys):
        menu = MainMenu(FakeModIndex(handpicked=self._make_many(15)))
        text = menu.render()
        assert "模组0" in text
        assert "模组11" in text
        assert "模组12" not in text

    def test_total_items_capped(self):
        """3 官方 + 12 精选 = 15。"""
        menu = MainMenu(FakeModIndex(handpicked=self._make_many(20)))
        assert menu.total_items == 15


# ---------- input_handler ----------
class TestInputHandler:
    def test_map_char_letters(self):
        assert ih._map_char('u').type == ih.EventType.UP
        assert ih._map_char('U').type == ih.EventType.UP
        assert ih._map_char('d').type == ih.EventType.DOWN
        assert ih._map_char('l').type == ih.EventType.LEFT
        assert ih._map_char('r').type == ih.EventType.RIGHT

    def test_map_char_confirm_chars(self):
        for ch in ('\r', '\n', ' ', 'e', 'E'):
            assert ih._map_char(ch).type == ih.EventType.ENTER

    def test_map_char_special(self):
        assert ih._map_char('q').type == ih.EventType.QUIT
        assert ih._map_char('s').type == ih.EventType.SEARCH
        assert ih._map_char('h').type == ih.EventType.HELP
        assert ih._map_char('~').type == ih.EventType.BACK
        assert ih._map_char('x').type == ih.EventType.DELETE

    def test_map_char_unknown_returns_char(self):
        event = ih._map_char('z')
        assert event.type == ih.EventType.CHAR
        assert event.char == 'z'

    def test_read_key_returns_none_when_not_tty(self, monkeypatch):
        """非 TTY 环境返回 None，避免 CI 挂。"""
        monkeypatch.setattr(os, 'name', 'posix')
        with patch('sys.stdin') as mock_stdin:
            mock_stdin.isatty.return_value = False
            # 清掉 msvcrt 分支，强制走 unix 分支
            assert ih.read_key() is None
            assert ih.read_key() is None