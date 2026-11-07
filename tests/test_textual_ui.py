"""Textual TUI 阶段 1 测试。"""
import asyncio
import os
import sys

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)
SRC_DIR = os.path.join(PROJECT_ROOT, "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

import pytest

# 如果未安装 textual（CI 或精简环境），整个文件跳过，防止 collection error
textual = pytest.importorskip("textual")

from uno.ui.textual_ui import TEXTUAL_AVAILABLE


def test_textual_available():
    assert TEXTUAL_AVAILABLE is True


def test_run_tui_fallback_when_no_textual(monkeypatch):
    import uno.ui.textual_ui as mod
    monkeypatch.setattr(mod, "TEXTUAL_AVAILABLE", False)
    assert mod.run_tui() is None


def test_menu_screen_renders_two_buttons():
    from uno.ui.textual_ui import SkillUNOApp

    async def _run():
        app = SkillUNOApp()
        async with app.run_test() as pilot:
            await pilot.pause()
            return len(app.screen.query("Button"))

    assert asyncio.run(_run()) == 2


def test_click_new_goes_to_game_screen(monkeypatch):
    from uno.ui.textual_ui import SkillUNOApp, GameScreen

    async def _run():
        app = SkillUNOApp()
        pushed_screens = []
        orig_push = app.push_screen
        def _fake_push(screen, **kwargs):
            # 防止测试环境真启动后台游戏线程导致死锁
            if isinstance(screen, GameScreen):
                screen.test_mode = True
            pushed_screens.append(screen)
            orig_push(screen, **kwargs)
        monkeypatch.setattr(app, "push_screen", _fake_push)

        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.click("#new")
            await pilot.pause()
            return pushed_screens

    screens = asyncio.run(_run())
    # on_mount 里 push 了 MenuScreen，点击又 push 了 GameScreen
    assert len(screens) >= 1
    assert isinstance(screens[-1], GameScreen)

def test_click_quit_returns_quit():
    from uno.ui.textual_ui import SkillUNOApp

    async def _run():
        app = SkillUNOApp()
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.click("#quit")
            await pilot.pause()
            return app.return_value

    assert asyncio.run(_run()) == "quit"
