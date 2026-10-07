"""阶段三覆盖率补充测试：router / input_handler / main。

重点覆盖：
- Router 主循环、_dispatch 各分支
- input_handler 的 UTF-8 多字节、Ctrl+C、非 TTY
- main._find_mods_dir 的路径查找
- 各页面遗漏的渲染分支
"""
import os
import sys
from unittest.mock import patch, MagicMock

import pytest

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)
SRC_DIR = os.path.join(PROJECT_ROOT, "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from uno.mod_store import input_handler as ih
from uno.mod_store import router as router_module
from uno.mod_store.router import Router, Action


# ==================== Router 主循环 ====================
class _FakePage:
    """测试用假页面。识别 QUIT / BACK 事件以避免死循环。"""

    def __init__(self, actions=None):
        self.actions = list(actions or [])
        self.rendered = 0
        self.handled = 0

    def render(self):
        self.rendered += 1
        return "fake page"

    def handle_key(self, key):
        self.handled += 1
        # 真实页面都会处理 QUIT；测试页面也要，否则死循环
        if key.type == ih.EventType.QUIT:
            return Action.QUIT
        if self.actions:
            return self.actions.pop(0)
        return None


class TestRouterMainLoop:
    def test_run_returns_immediately_when_no_pages(self):
        r = Router()
        r.run()

    def test_run_quit_via_event(self, monkeypatch):
        page = _FakePage()
        r = Router()
        r.push(page)
        # read_key 返回 QUIT，_FakePage 会把它转成 Action.QUIT
        monkeypatch.setattr(router_module.ih, "read_key",
                            lambda **kw: ih.KeyEvent(ih.EventType.QUIT))
        with patch("uno.mod_store.render.clear_screen"):
            r.run()
        assert r.running is False

    def test_run_quit_via_action(self, monkeypatch):
        page = _FakePage(actions=[Action.QUIT])
        r = Router()
        r.push(page)
        monkeypatch.setattr(router_module.ih, "read_key",
                            lambda **kw: ih.KeyEvent(ih.EventType.UP))
        with patch("uno.mod_store.render.clear_screen"):
            r.run()
        assert r.running is False

    def test_run_back_pops_page(self, monkeypatch):
        page1 = _FakePage(actions=[None])
        page2 = _FakePage(actions=[Action.BACK])
        r = Router()
        r.push(page1)
        r.push(page2)
        calls = [0]

        def fake_read(**kw):
            calls[0] += 1
            if calls[0] >= 3:
                return None
            return ih.KeyEvent(ih.EventType.UP)

        monkeypatch.setattr(router_module.ih, "read_key", fake_read)
        with patch("uno.mod_store.render.clear_screen"):
            r.run()
        # page2 已被 pop
        assert page2 not in r.stack

    def test_run_back_on_last_page_quits(self, monkeypatch):
        page = _FakePage(actions=[Action.BACK])
        r = Router()
        r.push(page)
        monkeypatch.setattr(router_module.ih, "read_key",
                            lambda **kw: ih.KeyEvent(ih.EventType.UP))
        with patch("uno.mod_store.render.clear_screen"):
            r.run()
        assert r.running is False

    def test_run_read_key_none_exits(self, monkeypatch):
        page = _FakePage()
        r = Router()
        r.push(page)
        monkeypatch.setattr(router_module.ih, "read_key", lambda **kw: None)
        with patch("uno.mod_store.render.clear_screen"):
            r.run()
        assert page.rendered >= 1

    def test_run_keyboard_interrupt(self, monkeypatch):
        page = _FakePage()
        r = Router()
        r.push(page)

        def raise_ki(**kw):
            raise KeyboardInterrupt()

        monkeypatch.setattr(router_module.ih, "read_key", raise_ki)
        with patch("uno.mod_store.render.clear_screen"):
            r.run()

    def test_dispatch_tuple_detail(self):
        r = Router(mod_index=MagicMock())
        fake_page = MagicMock()
        with patch("uno.mod_store.detail.DetailPage", return_value=fake_page):
            r._dispatch((Action.DETAIL, {"ID": "X"}))
            assert fake_page in r.stack

    def test_dispatch_detail_no_payload(self):
        r = Router()
        r._dispatch((Action.DETAIL, None))
        assert r.stack == []

    def test_dispatch_search_with_mod_index(self):
        mi = MagicMock()
        r = Router(mod_index=mi)
        fake_page = MagicMock()
        with patch("uno.mod_store.search.SearchPage", return_value=fake_page):
            r._dispatch(Action.SEARCH)
            assert fake_page in r.stack

    def test_dispatch_search_no_mod_index(self):
        r = Router(mod_index=None)
        r._dispatch(Action.SEARCH)
        # 现在 router 会 push 一个 MessagePage 而非 print
        assert len(r.stack) == 1
        msg = getattr(r.stack[0], "message", "")
        assert "错误" in msg or "未初始化" in msg

    def test_dispatch_unknown_action(self):
        r = Router()
        r._dispatch("SOMETHING_WEIRD")

    def test_pop_empty(self):
        r = Router()
        assert r.pop() is None

    def test_current_empty(self):
        r = Router()
        assert r.current() is None


# ==================== input_handler 边界 ====================
class TestInputHandlerEdge:
    def test_map_char_backspace_del(self):
        assert ih._map_char("\x7f").type == ih.EventType.BACKSPACE
        assert ih._map_char("\x08").type == ih.EventType.BACKSPACE

    def test_map_char_uppercase_letters(self):
        assert ih._map_char("U").type == ih.EventType.UP
        assert ih._map_char("D").type == ih.EventType.DOWN
        assert ih._map_char("L").type == ih.EventType.LEFT
        assert ih._map_char("R").type == ih.EventType.RIGHT
        assert ih._map_char("S").type == ih.EventType.SEARCH
        assert ih._map_char("Q").type == ih.EventType.QUIT
        assert ih._map_char("H").type == ih.EventType.HELP

    def test_map_char_e_is_enter(self):
        assert ih._map_char("e").type == ih.EventType.ENTER
        assert ih._map_char("E").type == ih.EventType.ENTER

    def test_keyevent_eq(self):
        a = ih.KeyEvent(ih.EventType.CHAR, "a")
        b = ih.KeyEvent(ih.EventType.CHAR, "a")
        c = ih.KeyEvent(ih.EventType.CHAR, "b")
        assert a == b
        assert not (a == c)
        assert not (a == "not_a_keyevent")

    def test_keyevent_repr(self):
        e = ih.KeyEvent(ih.EventType.CHAR, "x")
        assert "CHAR" in repr(e)
        assert "x" in repr(e)

    def test_read_key_non_tty_returns_none(self, monkeypatch):
        monkeypatch.setattr(os, "name", "posix")
        with patch("sys.stdin") as mock_stdin:
            mock_stdin.isatty.return_value = False
            assert ih.read_key() is None

    def test_read_key_ctrl_c_raises(self, monkeypatch):
        monkeypatch.setattr(ih, "_read_bytes", lambda: b"\x03")
        with pytest.raises(KeyboardInterrupt):
            ih.read_key()

    def test_read_key_multibyte_chinese(self, monkeypatch):
        """示 = e7 a4 ba"""
        seq = [b"\xe7", b"\xa4", b"\xba"]
        calls = [0]

        def fake_read(**kw):
            if calls[0] < len(seq):
                b = seq[calls[0]]
                calls[0] += 1
                return b
            return None

        monkeypatch.setattr(ih, "_read_bytes", fake_read)
        event = ih.read_key()
        assert event.type == ih.EventType.CHAR
        assert event.char == "示"

    def test_read_key_two_byte_char(self, monkeypatch):
        """© = c2 a9"""
        seq = [b"\xc2", b"\xa9"]
        calls = [0]

        def fake_read(**kw):
            if calls[0] < len(seq):
                b = seq[calls[0]]
                calls[0] += 1
                return b
            return None

        monkeypatch.setattr(ih, "_read_bytes", fake_read)
        event = ih.read_key()
        assert event.type == ih.EventType.CHAR
        assert event.char == "©"

    def test_read_key_four_byte_emoji(self, monkeypatch):
        """😀 = f0 9f 98 80"""
        seq = [b"\xf0", b"\x9f", b"\x98", b"\x80"]
        calls = [0]

        def fake_read(**kw):
            if calls[0] < len(seq):
                b = seq[calls[0]]
                calls[0] += 1
                return b
            return None

        monkeypatch.setattr(ih, "_read_bytes", fake_read)
        event = ih.read_key()
        assert event.type == ih.EventType.CHAR
        assert event.char == "😀"

    def test_read_key_invalid_byte(self, monkeypatch):
        monkeypatch.setattr(ih, "_read_bytes", lambda: b"\x80")
        event = ih.read_key()
        assert event is not None

    def test_read_key_incomplete_utf8(self, monkeypatch):
        calls = [0]

        def fake_read(**kw):
            calls[0] += 1
            if calls[0] == 1:
                return b"\xe7"
            return None

        monkeypatch.setattr(ih, "_read_bytes", fake_read)
        event = ih.read_key()
        assert event is not None

    def test_read_key_none_first(self, monkeypatch):
        monkeypatch.setattr(ih, "_read_bytes", lambda: None)
        assert ih.read_key() is None


# ==================== main 模块 ====================
class TestModStoreMain:
    def test_find_mods_dir_returns_path(self):
        from uno.mod_store import main as store_main
        from pathlib import Path
        p = store_main._find_mods_dir()
        assert isinstance(p, Path)

    def test_find_mods_dir_fallback(self):
        from uno.mod_store import main as store_main
        from pathlib import Path
        with patch.object(Path, "is_dir", return_value=False):
            p = store_main._find_mods_dir()
            assert p.name == "mods"

    def test_run_mod_store_calls_router(self):
        from uno.mod_store import main as store_main
        fake_index = MagicMock()
        fake_router = MagicMock()
        with patch.object(store_main, "ModIndex", return_value=fake_index), \
             patch.object(store_main, "Router", return_value=fake_router), \
             patch.object(store_main, "MainMenu", return_value=MagicMock()):
            store_main.run_mod_store()
        fake_router.run.assert_called_once()
        fake_router.push.assert_called_once()


# ==================== 页面遗漏分支 ====================
class TestPageBranches:
    def test_main_menu_current_mod_no_official(self):
        from uno.mod_store.menu import MainMenu

        class Idx:
            def get_official(self):
                return []

            def get_handpicked(self):
                return [{"ID": "X", "name": "X", "author": "a",
                         "author_github": "a", "version": "1.0.0",
                         "skills": 1}]

        menu = MainMenu(Idx())
        menu.selected = 0
        assert menu.current_mod() is not None

    def test_main_menu_current_mod_out_of_range(self):
        from uno.mod_store.menu import MainMenu

        class Idx:
            def get_official(self):
                return []

            def get_handpicked(self):
                return []

        menu = MainMenu(Idx())
        menu.selected = 0
        assert menu.current_mod() is None

    def test_search_page_quit_on_empty(self):
        from uno.mod_store.search import SearchPage
        page = SearchPage(MagicMock())
        assert page.handle_key(ih.KeyEvent(ih.EventType.QUIT)) == Action.QUIT

    def test_search_page_quit_in_results(self):
        from uno.mod_store.search import SearchPage
        page = SearchPage(MagicMock())
        page.state = "RESULTS"
        assert page.handle_key(ih.KeyEvent(ih.EventType.QUIT)) == Action.QUIT

    def test_search_page_backspace_empty(self):
        from uno.mod_store.search import SearchPage
        page = SearchPage(MagicMock())
        page.handle_key(ih.KeyEvent(ih.EventType.BACKSPACE))
        assert page.query == ""

    def test_search_page_no_mod_index_returns_empty(self):
        from uno.mod_store.search import SearchPage
        page = SearchPage(None)
        page.query = "x"
        page._do_search()
        assert page.results == []

    def test_search_page_non_printable_char(self):
        from uno.mod_store.search import SearchPage
        page = SearchPage(MagicMock())
        page.handle_key(ih.KeyEvent(ih.EventType.CHAR, "\x00"))
        assert page.query == ""

    def test_search_page_up_down_empty_results(self):
        from uno.mod_store.search import SearchPage
        page = SearchPage(MagicMock())
        page.state = "RESULTS"
        page.results = []
        page.handle_key(ih.KeyEvent(ih.EventType.UP))
        page.handle_key(ih.KeyEvent(ih.EventType.DOWN))
        assert page.selected == 0

    def test_search_page_enter_on_no_selection(self):
        from uno.mod_store.search import SearchPage
        page = SearchPage(MagicMock())
        page.state = "RESULTS"
        page.results = []
        assert page.handle_key(ih.KeyEvent(ih.EventType.ENTER)) is None

    def test_detail_page_handle_unknown_key(self):
        from uno.mod_store.detail import DetailPage
        page = DetailPage({"name": "X"})
        assert page.handle_key(ih.KeyEvent(ih.EventType.UP)) is None

    def test_detail_page_format_dict_non_dict(self):
        from uno.mod_store.detail import DetailPage
        page = DetailPage({"name": "X"})
        assert page._format_dict("not a dict") == "not a dict"

    def test_detail_page_format_list_non_list(self):
        from uno.mod_store.detail import DetailPage
        page = DetailPage({"name": "X"})
        assert page._format_list("not a list") == "not a list"

    def test_detail_page_rely_on_dict_shown(self):
        from uno.mod_store.detail import DetailPage
        mod = {
            "name": "X", "author": "a", "author_github": "a",
            "version": "1.0.0", "micover": "1.0.0", "lacover": None,
            "repo": "r", "skills": 1,
            "rely_on": {"S1": "依赖说明"},
            "reject": {"S2": "冲突"},
            "only_tolerate": ["S1", "S4"],
            "needs": ["core.Skill"],
        }
        text = DetailPage(mod).render()
        assert "S1" in text
        assert "S2" in text
        assert "S4" in text
        assert "core.Skill" in text

    def test_detail_page_no_license(self):
        from uno.mod_store.detail import DetailPage
        mod = {"name": "X", "author": "a", "author_github": "a",
               "version": "1.0.0", "micover": "1.0.0", "lacover": None,
               "repo": "r", "skills": 0, "description": "d"}
        text = DetailPage(mod).render()
        assert "协议" not in text


# ==================== mod_index 遗漏 ====================
class TestModIndexMissed:
    def test_load_index_non_dict(self, tmp_path, capsys):
        from uno.mod_index import ModIndex
        (tmp_path / "mod_idx.json").write_text("[1,2,3]", encoding="utf-8")
        idx = ModIndex(mods_dir=str(tmp_path))
        data = idx.load_index()
        assert data["handpicked"] == []
        out = capsys.readouterr().out
        assert "警告" in out

    def test_load_mod_non_dict(self, tmp_path, capsys):
        from uno.mod_index import ModIndex
        (tmp_path / "bad.json").write_text("[1,2,3]", encoding="utf-8")
        idx = ModIndex(mods_dir=str(tmp_path))
        assert idx.load_mod("bad.json") is None
        out = capsys.readouterr().out
        assert "警告" in out

    def test_search_with_limit(self, tmp_path):
        import json
        from uno.mod_index import ModIndex
        mods = []
        for i in range(5):
            fn = f"m{i}.json"
            (tmp_path / fn).write_text(json.dumps({
                "ID": f"M{i}", "name": f"测试{i}", "description": "d",
                "author": "a", "author_github": "a", "repo": "r",
                "version": "1.0.0", "micover": "1.0.0",
                "lacover": None, "skills": 1,
            }, ensure_ascii=False), encoding="utf-8")
            mods.append(fn)
        (tmp_path / "mod_idx.json").write_text(json.dumps({
            "handpicked": mods, "other": [],
            "version": "1.0.0", "update_time": "",
        }), encoding="utf-8")
        idx = ModIndex(mods_dir=str(tmp_path))
        result = idx.search("测试", limit=3)
        assert len(result) == 3

    def test_search_matches_tags(self, tmp_path):
        import json
        from uno.mod_index import ModIndex
        (tmp_path / "m.json").write_text(json.dumps({
            "ID": "M", "name": "n", "description": "d",
            "author": "a", "author_github": "a", "repo": "r",
            "version": "1.0.0", "micover": "1.0.0",
            "lacover": None, "skills": 1,
            "tags": ["特殊标签"],
        }, ensure_ascii=False), encoding="utf-8")
        (tmp_path / "mod_idx.json").write_text(json.dumps({
            "handpicked": ["m.json"], "other": [],
            "version": "1.0.0", "update_time": "",
        }), encoding="utf-8")
        idx = ModIndex(mods_dir=str(tmp_path))
        result = idx.search("特殊标签")
        assert len(result) == 1
