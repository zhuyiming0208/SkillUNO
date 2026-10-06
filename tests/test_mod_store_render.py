"""测试 mod_store.render。"""
import os
import sys
from unittest.mock import patch

import pytest

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)
SRC_DIR = os.path.join(PROJECT_ROOT, "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from uno.mod_store import render


# ---------- display_width ----------
class TestDisplayWidth:
    def test_ascii(self):
        assert render.display_width("hello") == 5

    def test_chinese(self):
        assert render.display_width("你好") == 4

    def test_mixed(self):
        assert render.display_width("a你b") == 4

    def test_empty(self):
        assert render.display_width("") == 0

    def test_ignores_ansi(self, monkeypatch):
        monkeypatch.setenv("FORCE_COLOR", "1")
        text = "\x1b[31mhi\x1b[0m"
        assert render.display_width(text) == 2


# ---------- pad_text ----------
class TestPadText:
    def test_left_align(self):
        assert render.pad_text("hi", 5, "left") == "hi   "

    def test_right_align(self):
        assert render.pad_text("hi", 5, "right") == "   hi"

    def test_center_align(self):
        # 5-2=3 → 左 1 右 2
        assert render.pad_text("hi", 5, "center") == " hi  "

    def test_chinese_width(self):
        # "中文" 宽 4，pad 到 6 → 补 2 空格
        assert render.pad_text("中文", 6, "left") == "中文  "

    def test_no_padding_when_equal(self):
        assert render.pad_text("abc", 3) == "abc"

    def test_no_padding_when_larger(self):
        assert render.pad_text("abcdef", 3) == "abcdef"

    def test_default_align_left(self):
        assert render.pad_text("hi", 4) == "hi  "


# ---------- draw_box ----------
class TestDrawBox:
    def test_simple_box(self):
        box = render.draw_box(["hello"], 10)
        lines = box.split("\n")
        assert lines[0] == "╔" + "═" * 10 + "╗"
        assert lines[1] == "║hello     ║"
        assert lines[2] == "╚" + "═" * 10 + "╝"

    def test_box_with_title(self):
        box = render.draw_box([], 10, title="T")
        first_line = box.split("\n")[0]
        assert first_line.startswith("╔")
        assert first_line.endswith("╗")
        assert "T" in first_line

    def test_box_lines_uniform_width(self):
        box = render.draw_box(["hello", "hi"], 10)
        for line in box.split("\n"):
            assert render.display_width(line) == 12  # 10 + 两侧竖线

    def test_box_with_chinese_content(self):
        box = render.draw_box(["你好"], 10)
        # 每行显示宽度一致
        for line in box.split("\n"):
            assert render.display_width(line) == 12


# ---------- colorize ----------
class TestColorize:
    def test_no_color_env(self, monkeypatch):
        monkeypatch.setenv("NO_COLOR", "1")
        monkeypatch.delenv("FORCE_COLOR", raising=False)
        assert render.colorize("hi", "red") == "hi"

    def test_force_color(self, monkeypatch):
        monkeypatch.delenv("NO_COLOR", raising=False)
        monkeypatch.setenv("FORCE_COLOR", "1")
        result = render.colorize("hi", "red")
        assert "\x1b[" in result
        assert "hi" in result

    def test_unknown_color(self, monkeypatch):
        monkeypatch.setenv("FORCE_COLOR", "1")
        monkeypatch.delenv("NO_COLOR", raising=False)
        assert render.colorize("hi", "not_a_color") == "hi"

    def test_supports_color_no_color_env(self, monkeypatch):
        monkeypatch.setenv("NO_COLOR", "1")
        assert render.supports_color() is False


# ---------- 清屏 / 光标 ----------
class TestScreenControl:
    def test_clear_screen_does_not_raise(self):
        with patch('sys.stdout'):
            render.clear_screen()

    def test_move_cursor_does_not_raise(self):
        with patch('sys.stdout'):
            render.move_cursor(1, 1)