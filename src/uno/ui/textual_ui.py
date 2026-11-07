"""Textual 全屏 TUI（阶段 1：仅主菜单）。"""
import threading
import re

try:
    from textual.app import App, ComposeResult
    from textual.widgets import Button, Static, RichLog, Header, Footer, Input
    from textual.screen import Screen
    from textual.containers import Center, Vertical, Container
    TEXTUAL_AVAILABLE = True
except ImportError:
    TEXTUAL_AVAILABLE = False


if TEXTUAL_AVAILABLE:



    from uno.ui import ConsoleUI

    class TextualUI(ConsoleUI):
        """纯 TUI 适配器，通过 Input 控件和 Event 实现跨线程输入。"""
        def __init__(self, app, game_screen):
            self.app = app
            self.game_screen = game_screen
            self._input_event = threading.Event()
            self._input_result = ""

        def show(self, text=""):
            if not text: return
            # 捕获回合切换，更新 Header
            m_turn = re.search(r"^===== (.*?) 的回合 =====$", text, re.M)
            if m_turn:
                turn_name = m_turn.group(1)
                self.app.call_from_thread(setattr, self.app, "sub_title", f"轮到：{turn_name}")
            # 用正则简单着色，提升 TUI 阅读体验
            text = re.sub(r"^=== (.*?) ===$", r"[bold cyan]=== \1 ===[/bold cyan]", text, flags=re.M)
            text = re.sub(r"^类型: (.*)$", r"[magenta]类型:[/magenta] \1", text, flags=re.M)
            text = re.sub(r"^简介: (.*)$", r"[yellow]简介:[/yellow] \1", text, flags=re.M)
            text = re.sub(r"^详细: (.*)$", r"[dim]详细:[/dim] [dim]\1[/dim]", text, flags=re.M)
            text = re.sub(r"^可发动的技能：$", r"[bold green]可发动的技能：[/bold green]", text, flags=re.M)
            self.app.call_from_thread(self.game_screen.write_log, text)

        def show_error(self, text=""):
            self.show(text)

        def clear_screen(self):
            self.app.call_from_thread(self.game_screen.clear_log)

        def input(self, prompt=""):
            # 1. 告诉 UI 线程显示输入框
            self.app.call_from_thread(self.game_screen.show_input, prompt)
            # 2. 阻塞后台线程，等待 UI 线程的输入结果
            self._input_event.clear()
            self._input_event.wait()
            return self._input_result

        def pause(self, message=""):
            return self.input(message)


    class GameScreen(Screen):
        """全屏游戏界面。"""

        def __init__(self, test_mode=False, **kwargs):
            super().__init__(**kwargs)
            self.test_mode = test_mode
            self.textual_ui = None

        def compose(self) -> ComposeResult:
            yield Header(show_clock=False, icon="")
            yield RichLog(id="game-log", highlight=True, markup=True)
            yield Input(placeholder="等待游戏开始...", id="game-input")
            yield Footer(show_command_palette=False)

        def on_mount(self) -> None:
            self.query_one("#game-input").display = False
            if not self.test_mode:
                self.run_worker(self.run_game, thread=True)

        def write_log(self, text: str):
            self.query_one("#game-log", RichLog).write(text)

        def clear_log(self):
            self.query_one("#game-log", RichLog).clear()

        def show_input(self, prompt: str):
            """UI 线程：显示输入框并聚焦。"""
            inp = self.query_one("#game-input", Input)
            lines = prompt.split(chr(10))
            # 把多行说明打印到日志里
            if len(lines) > 1:
                for line in lines[:-1]:
                    self.write_log(line)
                short_prompt = lines[-1][:50]
            else:
                short_prompt = prompt[:50]
                
            inp.placeholder = short_prompt
            inp.value = ""
            inp.display = True
            inp.focus()

        def on_input_submitted(self, event: Input.Submitted):
            """UI 线程：用户敲回车。"""
            if self.textual_ui:
                self.textual_ui._input_result = event.value
                self.textual_ui._input_event.set()
            event.input.display = False
            self.query_one("#game-log", RichLog).write(f"> {event.value}")

        def run_game(self):
            """后台线程：运行游戏引擎。"""
            from uno.core import UNOGame
            
            # 实例化 UI
            self.textual_ui = TextualUI(self.app, self)
            self.write_log("=== 准备开始新游戏 ===")

            try:
                pname = self.textual_ui.input("请输入你的名字（回车默认'你'）: ").strip()
                if not pname:
                    pname = "你"
                
                # 查战绩并重定向到日志
                import io
                from contextlib import redirect_stdout
                from uno.archive import show_record
                buf = io.StringIO()
                with redirect_stdout(buf):
                    show_record(pname)
                if buf.getvalue().strip():
                    self.textual_ui.show(buf.getvalue())
                
                season_prompt = (
                    "请选择赛季组合:\n"
                    "  官方：1 - 经典 (S1) / 2 - 被动 (S2) / 3 - 同盟 (S3) / 4 - 补丁 (S4)\n"
                    "  自定义：输入 Mod 的 SEASON_ID（如 LOD）\n"
                    "默认 S1: "
                )
                import os
                from uno.paths import find_mods_dir
                
                mods_dir = str(find_mods_dir())
                smap = {'1':'S1', '2':'S2', '3':'S3', '4':'S4'}
                
                while True:
                    seasons_input = self.textual_ui.input(season_prompt).strip()
                    if not seasons_input:
                        seasons = ["S1"]
                        break
                        
                    parts = [p.strip() for p in seasons_input.split(',') if p.strip()]
                    parsed = []
                    invalid = []
                    for p in parts:
                        sid = smap.get(p, p)
                        if sid in ("S1", "S2", "S3", "S4"):
                            parsed.append(sid)
                        elif os.path.isfile(os.path.join(mods_dir, f"{sid}.py")):
                            parsed.append(sid)
                        else:
                            invalid.append(sid)
                            
                    if invalid:
                        err = f"[bold red]错误：找不到以下赛季或模组：{', '.join(invalid)}[/bold red]"
                        self.textual_ui.show(err)
                        continue
                        
                    seasons = parsed if parsed else ["S1"]
                    break
                
                self.write_log(f"开局设定：玩家 [{pname}]，赛季 [{','.join(seasons)}]")

                game = UNOGame(pname, seasons, debug=False, use_rich_ui=False)
                # 关键：把 game 和所有玩家（包括 AI）的 ui 全部换成 TUI 适配器
                game.ui = self.textual_ui
                for p in game.players:
                    p.ui = self.textual_ui

                game.run()
            except SystemExit:
                self.write_log("=== 游戏已退出，返回主菜单 ===")
                self.app.call_from_thread(self.app.pop_screen)
            except Exception as e:
                self.write_log(f"[red]游戏崩溃: {e}[/red]")


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
                self.app.push_screen(GameScreen())
            elif event.button.id == "quit":
                self.app.exit(result="quit")

    class SkillUNOApp(App):
        """TUI 主应用。"""

        TITLE = "SkillUNO"
        SUB_TITLE = "主菜单"

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
