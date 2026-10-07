"""测试详情页。"""
import os
import sys

import pytest

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)
SRC_DIR = os.path.join(PROJECT_ROOT, "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from uno.mod_store import input_handler as ih
from uno.mod_store.router import Action
from uno.mod_store.detail import DetailPage


def _make_mod(**kwargs):
    base = {
        "ID": "EXAMPLE",
        "name": "示例模组",
        "description": "这是一个示例模组。",
        "author": "example_author",
        "author_github": "example_github",
        "repo": "https://github.com/example/example",
        "license": "MIT",
        "version": "1.0.0",
        "micover": "1.0.0",
        "lacover": None,
        "skills": 3,
        "achievements": 0,
        "needs": ["core.Skill"],
        "rely_on": {},
        "reject": {},
        "only_tolerate": [],
        "tags": ["示例"],
    }
    base.update(kwargs)
    return base


class TestDetailRender:
    def test_contains_name(self):
        text = DetailPage(_make_mod()).render()
        assert "示例模组" in text

    def test_contains_author(self):
        text = DetailPage(_make_mod()).render()
        assert "example_author" in text

    def test_contains_author_github(self):
        text = DetailPage(_make_mod()).render()
        assert "example_github" in text

    def test_contains_github(self):
        text = DetailPage(_make_mod()).render()
        assert "https://github.com/example/example" in text

    def test_lacover_null_shows_any_version(self):
        text = DetailPage(_make_mod(lacover=None)).render()
        assert "任意版本" in text

    def test_lacover_set_shows_range(self):
        text = DetailPage(_make_mod(lacover="2.0.0")).render()
        assert "1.0.0 ~ 2.0.0" in text

    def test_empty_rely_on_shows_none(self):
        text = DetailPage(_make_mod(rely_on={})).render()
        assert "依赖：无" in text

    def test_empty_reject_shows_none(self):
        text = DetailPage(_make_mod(reject={})).render()
        assert "排斥：无" in text

    def test_empty_only_tolerate_shows_none(self):
        text = DetailPage(_make_mod(only_tolerate=[])).render()
        assert "白名单：无" in text

    def test_empty_needs_shows_undeclared(self):
        text = DetailPage(_make_mod(needs=[])).render()
        assert "未声明" in text

    def test_skills_count_shown(self):
        text = DetailPage(_make_mod(skills=5)).render()
        assert "共 5 个技能" in text

    def test_description_shown(self):
        text = DetailPage(_make_mod(description="测试简介")).render()
        assert "测试简介" in text

    def test_action_bar_shown(self):
        text = DetailPage(_make_mod()).render()
        assert "I 安装" in text
        assert "R 查看源码" in text
        assert "Q 返回" in text

    def test_skill_names_list_shown(self):
        text = DetailPage(_make_mod(skill_names=["火球", "冰箭"])).render()
        assert "火球" in text
        assert "冰箭" in text

    def test_no_skill_names_shows_hint(self):
        text = DetailPage(_make_mod()).render()
        assert "技能详情请查看源码" in text


class TestDetailKeys:
    def test_q_returns_back(self):
        assert DetailPage(_make_mod()).handle_key(ih.KeyEvent(ih.EventType.QUIT)) == Action.BACK

    def test_esc_returns_back(self):
        assert DetailPage(_make_mod()).handle_key(ih.KeyEvent(ih.EventType.BACK)) == Action.BACK

    def test_i_returns_install(self):
        assert DetailPage(_make_mod()).handle_key(ih.KeyEvent(ih.EventType.CHAR, 'i')) == "INSTALL"

    def test_r_returns_view_source(self):
        assert DetailPage(_make_mod()).handle_key(ih.KeyEvent(ih.EventType.CHAR, 'r')) == "VIEW_SOURCE"

    def test_other_char_returns_none(self):
        assert DetailPage(_make_mod()).handle_key(ih.KeyEvent(ih.EventType.CHAR, 'z')) is None