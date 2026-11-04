"""Textual TUI 阶段 1 测试。"""
import asyncio
import os
import sys

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)
SRC_DIR = os.path.join(PROJECT_ROOT, "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

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


def test_click_new_returns_new():
    from uno.ui.textual_ui import SkillUNOApp

    async def _run():
        app = SkillUNOApp()
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.click("#new")
            await pilot.pause()
            return app.return_value

    assert asyncio.run(_run()) == "new"


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
