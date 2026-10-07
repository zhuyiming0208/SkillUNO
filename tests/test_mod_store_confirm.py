"""测试 ConfirmPage。"""
import os
import sys

import pytest

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)
SRC_DIR = os.path.join(PROJECT_ROOT, "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from uno.mod_store import input_handler as ih
from uno.mod_store.confirm import ConfirmPage


def _mod():
    return {
        "ID": "X", "name": "测试模组", "author": "alice",
        "author_github": "alice", "version": "1.0.0",
        "repo": "https://github.com/alice/x",
        "skills": 3, "achievements": 1,
        "needs": ["core.Skill"],
        "rely_on": {}, "reject": {}, "only_tolerate": [],
    }


class TestConfirmRender:
    def test_basic(self):
        text = ConfirmPage(_mod()).render()
        assert "测试模组" in text
        assert "alice" in text
        assert "1.0.0" in text

    def test_skills_and_achievements(self):
        text = ConfirmPage(_mod()).render()
        assert "3" in text
        assert "1" in text

    def test_needs(self):
        text = ConfirmPage(_mod()).render()
        assert "core.Skill" in text

    def test_needs_empty_shows_undeclared(self):
        mod = _mod()
        mod["needs"] = []
        text = ConfirmPage(mod).render()
        assert "未声明" in text

    def test_security_message(self):
        text = ConfirmPage(_mod()).render()
        assert "启用后，模组代码将在游戏下次启动时执行" in text
        assert "请确认作者可信" in text

    def test_installed_warning(self):
        existing = {"location": "installed", "path": "mods/X.py"}
        text = ConfirmPage(_mod(), existing=existing).render()
        assert "覆盖已安装版本" in text
        assert "mods/X.py" in text

    def test_pending_warning(self):
        existing = {"location": "pending", "path": "mods/_pending/X.py"}
        text = ConfirmPage(_mod(), existing=existing).render()
        assert "重新下载并覆盖" in text

    def test_error_shown(self):
        page = ConfirmPage(_mod())
        page.error = "网络连接失败"
        text = page.render()
        assert "网络连接失败" in text
        assert "按任意键" in text

    def test_rely_on_dict(self):
        mod = _mod()
        mod["rely_on"] = {"S1": "需要经典赛季"}
        text = ConfirmPage(mod).render()
        assert "S1" in text

    def test_only_tolerate_list(self):
        mod = _mod()
        mod["only_tolerate"] = ["S1", "S4"]
        text = ConfirmPage(mod).render()
        assert "S1" in text and "S4" in text

    def test_empty_relations_show_none(self):
        text = ConfirmPage(_mod()).render()
        # 依赖 / 排斥 / 白名单 都为空 → 至少 3 个"无"
        assert text.count("无") >= 3


class TestConfirmKeys:
    def test_y_returns_confirm(self):
        page = ConfirmPage(_mod())
        assert page.handle_key(ih.KeyEvent(ih.EventType.CHAR, "y")) == "CONFIRM"

    def test_uppercase_y(self):
        page = ConfirmPage(_mod())
        assert page.handle_key(ih.KeyEvent(ih.EventType.CHAR, "Y")) == "CONFIRM"

    def test_n_returns_back(self):
        page = ConfirmPage(_mod())
        assert page.handle_key(ih.KeyEvent(ih.EventType.CHAR, "n")) == "BACK"

    def test_esc_returns_back(self):
        page = ConfirmPage(_mod())
        assert page.handle_key(ih.KeyEvent(ih.EventType.BACK)) == "BACK"

    def test_quit_returns_back(self):
        page = ConfirmPage(_mod())
        assert page.handle_key(ih.KeyEvent(ih.EventType.QUIT)) == "BACK"

    def test_other_char_returns_none(self):
        page = ConfirmPage(_mod())
        assert page.handle_key(ih.KeyEvent(ih.EventType.CHAR, "z")) is None

    def test_error_clears_on_any_key(self):
        page = ConfirmPage(_mod())
        page.error = "boom"
        page.handle_key(ih.KeyEvent(ih.EventType.CHAR, "z"))
        assert page.error is None