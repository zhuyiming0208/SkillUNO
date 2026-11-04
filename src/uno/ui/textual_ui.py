"""Textual 全屏 TUI（阶段 1：仅主菜单）。"""
try:
    from textual.app import App, ComposeResult
    from textual.widgets import Button, Static
    from textual.screen import Screen
    from textual.containers import Center, Vertical
    TEXTUAL_AVAILABLE = True
except ImportError:
    TEXTUAL_AVAILABLE = False


if TEXTUAL_AVAILABLE:



    class MenuScreen(Screen):
        """主菜单：新游戏 / 退出。"""

        def compose(self) -> ComposeResult:
            with Vertical(id="menu-card"):
                yield Static("S K I L L U N O", id="title")
                yield Static("进阶 UNO · 全屏终端版", id="subtitle")
                with Center():
                    yield Button("新  游  戏", id="new", variant="primary")
                with Center():
                    yield Button("退      出", id="quit", variant="error")
                yield Static("↑↓ 选择 · Enter 确认 · 或直接鼠标点击", id="hint")

        def on_button_pressed(self, event: Button.Pressed) -> None:
            if event.button.id == "new":
                self.app.exit(result="new")
            elif event.button.id == "quit":
                self.app.exit(result="quit")

    class SkillUNOApp(App):
        """TUI 主应用。"""

        CSS = """
        Screen {
            background: #0d1117;
            align: center middle;
        }
        #menu-card {
            width: 90%;
            max-width: 80;
            height: auto;
            min-height: 24;
            padding: 3 6;
            background: #161b22;
            border: round #00d9ff;
        }
        #title {
            text-align: center;
            text-style: bold;
            color: #00d9ff;
            width: 100%;
            margin-top: 1;
            margin-bottom: 2;
        }
        #subtitle {
            text-align: center;
            color: #ff00ff;
            width: 100%;
            margin-bottom: 3;
            text-style: bold;
        }
        #divider, #divider-bottom {
            text-align: center;
            color: #30363d;
            width: 100%;
        }
        #divider {
            margin-bottom: 2;
        }
        #divider-bottom {
            margin-top: 2;
            margin-bottom: 2;
        }
        Button {
            width: 100%;
            height: 3;
            margin-bottom: 2;
            border: none;
            content-align: center middle;
        }
        Button:focus {
            border: none;
        }
        Button#new {
            background: #00d9ff;
            color: #0d1117;
            text-style: bold;
        }
        Button#new:hover {
            background: #ff00ff;
            color: #ffffff;
        }
        Button#quit {
            background: #f85149;
            color: #ffffff;
            text-style: bold;
        }
        Button#quit:hover {
            background: #ff00ff;
            color: #ffffff;
        }
        #hint {
            text-align: center;
            color: #8b949e;
            width: 100%;
            margin-top: 2;
            text-style: italic;
        }
        """

        def on_mount(self) -> None:
            self.push_screen(MenuScreen())


def run_tui():
    """启动 TUI 菜单。"""
    if not TEXTUAL_AVAILABLE:
        print("未安装 textual，无法启动全屏 TUI。")
        print("请运行：pip install 'skilluno[tui]'")
        return None
    app = SkillUNOApp()
    return app.run()
