"""Textual 全屏 TUI（阶段 1：仅主菜单）。

设计：
- 阶段 1 只实现 MenuScreen，点「新游戏」后返回 "new"，由 main.py 降级到 ConsoleUI 跑游戏。
- 不碰 core.py，不涉及跨线程，零风险。
- 未安装 textual 时，run_tui() 打印提示并返回 None，调用方降级。
"""
try:
    from textual.app import App, ComposeResult
    from textual.widgets import Button, Static, Header, Footer
    from textual.screen import Screen
    TEXTUAL_AVAILABLE = True
except ImportError:
    TEXTUAL_AVAILABLE = False


if TEXTUAL_AVAILABLE:

    class MenuScreen(Screen):
        """主菜单：新游戏 / 退出。"""

        def compose(self) -> ComposeResult:
            yield Header()
            yield Static("SkillUNO", id="title")
            yield Static("选择操作", id="subtitle")
            yield Button("新游戏", id="new", variant="primary")
            yield Button("退出", id="quit", variant="error")
            yield Footer()

        def on_button_pressed(self, event: Button.Pressed) -> None:
            if event.button.id == "new":
                self.app.exit(result="new")
            elif event.button.id == "quit":
                self.app.exit(result="quit")

    class SkillUNOApp(App):
        """TUI 主应用。run() 返回值即用户选择。"""

        CSS = """
        MenuScreen {
            align-horizontal: center;
        }
        #title {
            text-align: center;
            text-style: bold;
            color: cyan;
            height: 3;
            width: 100%;
            margin-top: 2;
        }
        #subtitle {
            text-align: center;
            color: grey;
            height: 1;
            width: 100%;
            margin-bottom: 1;
        }
        Button {
            width: 40;
            margin: 1 0;
        }
        """

        def on_mount(self) -> None:
            self.push_screen(MenuScreen())


def run_tui():
    """启动 TUI 菜单。

    返回：
      "new"  —— 用户选择新游戏（调用方降级到 ConsoleUI 跑游戏）
      "quit" —— 用户选择退出
      None   —— textual 未安装
    """
    if not TEXTUAL_AVAILABLE:
        print("未安装 textual，无法启动全屏 TUI。")
        print("请运行：pip install 'skilluno[tui]'")
        return None
    app = SkillUNOApp()
    return app.run()
