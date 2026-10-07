"""测试主菜单的 12 个上限逻辑。"""
import os
import sys

import pytest

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)
SRC_DIR = os.path.join(PROJECT_ROOT, "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from uno.mod_store.menu import MainMenu


def _make_mod(i):
    return {
        "ID": f"M{i}", "name": f"模组{i}", "author": "a",
        "author_github": "a", "version": "1.0.0", "skills": 1,
        "description": "d",
    }


class FakeIndex:
    def __init__(self, handpicked=None, official=None):
        if official is None:
            official = [
                {"id": "S1", "name": "经典赛季", "skills": 16, "builtin": True},
                {"id": "S2", "name": "被动觉醒", "skills": 8, "builtin": True},
                {"id": "S4", "name": "补丁赛季", "skills": 8, "builtin": True},
            ]
        self._official = official
        self._handpicked = handpicked or []

    def get_official(self):
        return list(self._official)

    def get_handpicked(self):
        return list(self._handpicked)


class TestMenuLimit:
    def test_over_12_only_shows_first_12(self, capsys):
        idx = FakeIndex(handpicked=[_make_mod(i) for i in range(15)])
        menu = MainMenu(idx)
        text = menu.render()
        for i in range(12):
            assert f"模组{i}" in text
        # 第 13 个不显示
        assert "模组12" not in text
        assert "模组13" not in text
        assert "模组14" not in text

    def test_over_12_prints_warning(self, capsys):
        idx = FakeIndex(handpicked=[_make_mod(i) for i in range(15)])
        MainMenu(idx)
        captured = capsys.readouterr()
        assert "警告" in captured.out
        assert "12" in captured.out
        assert "15" in captured.out

    def test_exactly_12_no_warning(self, capsys):
        idx = FakeIndex(handpicked=[_make_mod(i) for i in range(12)])
        MainMenu(idx)
        captured = capsys.readouterr()
        assert "警告" not in captured.out

    def test_under_12_no_warning(self, capsys):
        idx = FakeIndex(handpicked=[_make_mod(i) for i in range(5)])
        MainMenu(idx)
        captured = capsys.readouterr()
        assert "警告" not in captured.out

    def test_empty_handpicked_shows_placeholder(self):
        idx = FakeIndex(handpicked=[])
        menu = MainMenu(idx)
        text = menu.render()
        assert "暂无精选模组" in text

    def test_total_items_capped_at_15(self, capsys):
        """3 官方 + 12 精选 = 15。"""
        idx = FakeIndex(handpicked=[_make_mod(i) for i in range(20)])
        menu = MainMenu(idx)
        assert menu.total_items == 15