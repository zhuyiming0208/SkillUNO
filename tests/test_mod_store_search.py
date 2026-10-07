"""测试搜索页。"""
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
from uno.mod_store.search import SearchPage


def _mod(id_, name, author, github="", tags=None):
    return {
        "ID": id_, "name": name, "author": author,
        "author_github": github, "version": "1.0.0", "skills": 1,
        "description": "d", "tags": tags or [],
    }


class FakeIndex:
    def __init__(self, mods=None):
        self.mods = mods or [
            _mod("EXAMPLE", "示例模组", "example_author", "example_author", ["示例"]),
            _mod("LUCKY", "幸运模组", "lucky_author", "lucky_gh", ["幸运", "赌"]),
        ]

    def search(self, keyword, limit=None):
        keyword = (keyword or "").strip().lower()
        if not keyword:
            return []
        result = []
        for m in self.mods:
            haystacks = [
                str(m.get("ID", "")).lower(),
                str(m.get("name", "")).lower(),
                str(m.get("author", "")).lower(),
                str(m.get("author_github", "")).lower(),
            ]
            for t in m.get("tags", []):
                haystacks.append(str(t).lower())
            if any(keyword in h for h in haystacks):
                result.append(m)
        if limit is not None:
            result = result[:limit]
        return result


def _type_text(page, text):
    for ch in text:
        page.handle_key(ih.KeyEvent(ih.EventType.CHAR, ch))


def _press_enter(page):
    page.handle_key(ih.KeyEvent(ih.EventType.ENTER, '\r'))


class TestSearchInput:
    def test_initial_state_is_input(self):
        assert SearchPage(FakeIndex()).state == "INPUT"

    def test_type_chars_appends_query(self):
        page = SearchPage(FakeIndex())
        _type_text(page, "exam")
        assert page.query == "exam"

    def test_backspace_removes_last_char(self):
        page = SearchPage(FakeIndex())
        _type_text(page, "exam")
        page.handle_key(ih.KeyEvent(ih.EventType.BACKSPACE))
        assert page.query == "exa"

    def test_backspace_on_empty_does_nothing(self):
        page = SearchPage(FakeIndex())
        page.handle_key(ih.KeyEvent(ih.EventType.BACKSPACE))
        assert page.query == ""

    def test_backspace_removes_chinese_char(self):
        """中文一次删一个字符（不是字节）。"""
        page = SearchPage(FakeIndex())
        _type_text(page, "示例")
        assert page.query == "示例"
        page.handle_key(ih.KeyEvent(ih.EventType.BACKSPACE))
        assert page.query == "示"

    def test_esc_returns_back(self):
        page = SearchPage(FakeIndex())
        assert page.handle_key(ih.KeyEvent(ih.EventType.BACK)) == Action.BACK

    def test_enter_triggers_search(self):
        page = SearchPage(FakeIndex())
        _type_text(page, "example")
        _press_enter(page)
        assert page.state == "RESULTS"
        assert len(page.results) >= 1


class TestSearchResults:
    def test_finds_by_id(self):
        page = SearchPage(FakeIndex())
        _type_text(page, "EXAMPLE")
        _press_enter(page)
        assert any(m["ID"] == "EXAMPLE" for m in page.results)

    def test_finds_by_name(self):
        page = SearchPage(FakeIndex())
        _type_text(page, "示例")
        _press_enter(page)
        assert any(m["ID"] == "EXAMPLE" for m in page.results)

    def test_finds_by_author(self):
        page = SearchPage(FakeIndex())
        _type_text(page, "lucky_author")
        _press_enter(page)
        assert any(m["ID"] == "LUCKY" for m in page.results)

    def test_finds_by_github(self):
        page = SearchPage(FakeIndex())
        _type_text(page, "lucky_gh")
        _press_enter(page)
        assert any(m["ID"] == "LUCKY" for m in page.results)

    def test_finds_by_tag(self):
        page = SearchPage(FakeIndex())
        _type_text(page, "赌")
        _press_enter(page)
        assert any(m["ID"] == "LUCKY" for m in page.results)

    def test_case_insensitive(self):
        page1 = SearchPage(FakeIndex())
        _type_text(page1, "example")
        _press_enter(page1)
        page2 = SearchPage(FakeIndex())
        _type_text(page2, "EXAMPLE")
        _press_enter(page2)
        assert [m["ID"] for m in page1.results] == [m["ID"] for m in page2.results]

    def test_no_match_returns_empty(self):
        page = SearchPage(FakeIndex())
        _type_text(page, "xyz不存在")
        _press_enter(page)
        assert page.results == []

    def test_limit_20_results(self):
        mods = [_mod(f"MOD{i}", f"测试{i}", "a") for i in range(30)]
        page = SearchPage(FakeIndex(mods=mods))
        _type_text(page, "测试")
        _press_enter(page)
        assert len(page.results) == 20


class TestSearchNavigation:
    def test_up_down_navigates(self):
        page = SearchPage(FakeIndex())
        _type_text(page, "模组")
        _press_enter(page)
        assert len(page.results) >= 2
        assert page.selected == 0
        page.handle_key(ih.KeyEvent(ih.EventType.DOWN))
        assert page.selected == 1
        page.handle_key(ih.KeyEvent(ih.EventType.UP))
        assert page.selected == 0

    def test_enter_on_result_returns_detail_tuple(self):
        page = SearchPage(FakeIndex())
        _type_text(page, "example")
        _press_enter(page)
        result = page.handle_key(ih.KeyEvent(ih.EventType.ENTER, '\r'))
        assert isinstance(result, tuple)
        action, payload = result
        assert action == Action.DETAIL
        assert payload["ID"] == "EXAMPLE"

    def test_esc_from_results_returns_to_input(self):
        page = SearchPage(FakeIndex())
        _type_text(page, "example")
        _press_enter(page)
        assert page.state == "RESULTS"
        page.handle_key(ih.KeyEvent(ih.EventType.BACK))
        assert page.state == "INPUT"


class TestSearchRender:
    def test_render_input_contains_prompt(self):
        text = SearchPage(FakeIndex()).render()
        assert "搜索" in text

    def test_render_results_contains_mod_name(self):
        page = SearchPage(FakeIndex())
        _type_text(page, "example")
        _press_enter(page)
        text = page.render()
        assert "示例模组" in text

    def test_render_empty_results_shows_hint(self):
        page = SearchPage(FakeIndex())
        _type_text(page, "xyz不存在")
        _press_enter(page)
        text = page.render()
        assert "未找到匹配的模组" in text