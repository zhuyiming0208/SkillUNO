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
    from uno.ui.actions import (
        PlayCardAction, DrawCardAction, QuitGameAction,
        ActivateSkillAction, HelpAction,
    )

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
            pl = prompt.lower()
            if "y/n" in pl:
                allowed = {"y", "n"}
                self.app.call_from_thread(
                    self.game_screen.show_key_hint,
                    "按 Y 打出 / 按 N 保留", allowed,
                )
            elif "颜色" in prompt:
                allowed = {"0", "1", "2", "3"}
                self.app.call_from_thread(
                    self.game_screen.show_key_hint,
                    "按 0红 1蓝 2绿 3黄", allowed,
                )
            elif "技能序号" in prompt:
                allowed = {str(i) for i in range(10)} | {"enter"}
                self.app.call_from_thread(
                    self.game_screen.show_key_hint,
                    "按数字键选技能，回车取消", allowed,
                )
            else:
                # 名字、自定义赛季等，走输入框 fallback
                self.app.call_from_thread(self.game_screen.show_input, prompt)
                self._input_event.clear()
                self._input_event.wait()
                return self._input_result
            self._input_event.clear()
            self._input_event.wait()
            return self._input_result

        def pause(self, message=""):
            return self.input(message)

        def choose_from(self, title, options):
            """后台线程：显示选项按钮，等待点击，返回选中的选项字符串。"""
            self.app.call_from_thread(
                self.game_screen.show_choices, title, options
            )
            self._input_event.clear()
            self._input_event.wait()
            self.app.call_from_thread(self.game_screen.clear_choose_buttons)
            return self._input_result

        def choose_action(self, player, game, top_card, current_color):
            """TUI 结构化动作：渲染按钮并等待点击。"""
            self.app.call_from_thread(
                self.game_screen.show_choose_buttons, player, top_card, current_color
            )
            self._input_event.clear()
            self._input_event.wait()
            self.app.call_from_thread(self.game_screen.clear_choose_buttons)
            return self._input_result


    class GameScreen(Screen):
        """全屏游戏界面。"""

        def __init__(self, test_mode=False, **kwargs):
            super().__init__(**kwargs)
            self.test_mode = test_mode
            self.textual_ui = None
            self._key_mode = False
            self._allowed_keys = set()
            self._choice_options = []
            self._choice_seq = 0

        def compose(self) -> ComposeResult:
            yield Header(show_clock=False, icon="")
            yield RichLog(id="game-log", highlight=True, markup=True)
            yield Container(id="card-bar")
            yield Input(placeholder="等待游戏开始...", id="game-input")
            yield Footer(show_command_palette=False)

        def on_mount(self) -> None:
            self.query_one("#game-input").display = False
            self.query_one("#card-bar").display = False
            if not self.test_mode:
                self.run_worker(self.run_game, thread=True)

        def write_log(self, text: str):
            self.query_one("#game-log", RichLog).write(text)

        def clear_log(self):
            self.query_one("#game-log", RichLog).clear()

        def show_choose_buttons(self, player, top_card, current_color):
            """UI 线程：渲染手牌按钮 + 技能按钮 + 抽牌/帮助/退出按钮。"""
            bar = self.query_one("#card-bar", Container)
            bar.remove_children()
            # 手牌按钮
            for i, card in enumerate(player.hand):
                playable = card.is_playable_on(top_card, current_color)
                btn = Button(
                    f"[{i}] {card}",
                    id=f"card_{i}",
                    variant="primary" if playable else "default",
                    disabled=not playable,
                )
                bar.mount(btn)
            # 技能按钮
            skills = player.available_active_skills()
            for i, sk in enumerate(skills):
                bar.mount(Button(
                    f"技能:{sk.name}",
                    id=f"skill_{i}",
                    variant="success",
                ))
            # 通用按钮
            bar.mount(Button("抽牌", id="draw_btn", variant="warning"))
            bar.mount(Button("帮助", id="help_btn", variant="default"))
            bar.mount(Button("退出", id="quit_btn", variant="error"))
            self.query_one("#game-input").display = False
            bar.display = True

        def clear_choose_buttons(self):
            """UI 线程：清空按钮区。"""
            bar = self.query_one("#card-bar", Container)
            bar.remove_children()
            bar.display = False

        def on_button_pressed(self, event: Button.Pressed) -> None:
            """处理按钮点击，构造 Action 唤醒后台线程。"""
            if self.textual_ui is None:
                return
            bid = event.button.id or ""
            if bid.startswith("card_"):
                try:
                    idx = int(bid[5:])
                except ValueError:
                    return
                self.textual_ui._input_result = PlayCardAction(card_index=idx)
                self.textual_ui._input_event.set()
                event.stop()
            elif bid == "draw_btn":
                self.textual_ui._input_result = DrawCardAction()
                self.textual_ui._input_event.set()
                event.stop()
            elif bid == "quit_btn":
                self.textual_ui._input_result = QuitGameAction()
                self.textual_ui._input_event.set()
                event.stop()
            elif bid == "help_btn":
                self.textual_ui._input_result = HelpAction()
                self.textual_ui._input_event.set()
                event.stop()
            elif bid.startswith("skill_"):
                try:
                    idx = int(bid[6:])
                except ValueError:
                    return
                self.textual_ui._input_result = ActivateSkillAction(skill_index=idx)
                self.textual_ui._input_event.set()
                event.stop()
            elif bid.startswith("choice_"):
                try:
                    idx = int(bid.split("_")[-1])
                except (ValueError, IndexError):
                    return
                if 0 <= idx < len(self._choice_options):
                    self.textual_ui._input_result = self._choice_options[idx]
                    self.textual_ui._input_event.set()
                event.stop()

        def show_choices(self, title: str, options: list):
            """UI 线程：显示选项按钮。"""
            self._choice_options = list(options)
            self._choice_seq += 1
            seq = self._choice_seq
            self.write_log(f"[bold cyan]{title}[/bold cyan]")
            bar = self.query_one("#card-bar", Container)
            bar.remove_children()
            for i, opt in enumerate(options):
                bar.mount(Button(opt, id=f"choice_{seq}_{i}", variant="primary"))
            self.query_one("#game-input").display = False
            bar.display = True

        def show_key_hint(self, hint: str, allowed_keys):
            """UI 线程：显示按键提示（替代输入框）。"""
            self.query_one("#game-input").display = False
            self._key_mode = True
            self._allowed_keys = set(allowed_keys)
            self.write_log(f"[bold yellow]👉 {hint}[/bold yellow]")

        def on_key(self, event):
            """全局按键：按键模式下响应。"""
            if self.textual_ui is None or not self._key_mode:
                return
            ch = (event.key or "").lower()
            if ch not in self._allowed_keys:
                return
            if ch == "enter":
                self.textual_ui._input_result = ""
            else:
                self.textual_ui._input_result = ch
            self._key_mode = False
            self._allowed_keys = set()
            self.textual_ui._input_event.set()
            event.stop()

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
            # 先清空当前焦点（避免按钮被删除后焦点悬空）
            self.set_focus(None)
            # 等布局刷新完再聚焦，否则 display=True 尚未生效
            self.call_after_refresh(self.set_focus, inp)

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
                import os
                from uno.paths import find_mods_dir
                mods_dir = str(find_mods_dir())

                # === 玩家名字：按钮选择 ===
                name_opts = ["你", "__GOD__", "自定义..."]
                name_choice = self.textual_ui.choose_from("选择玩家名字", name_opts)
                if name_choice == "自定义...":
                    pname = self.textual_ui.input("请输入你的名字: ").strip()
                    if not pname:
                        pname = "你"
                else:
                    pname = name_choice

                # 查战绩并重定向到日志
                import io
                from contextlib import redirect_stdout
                from uno.archive import show_record
                buf = io.StringIO()
                with redirect_stdout(buf):
                    show_record(pname)
                if buf.getvalue().strip():
                    self.textual_ui.show(buf.getvalue())

                # === 赛季：按钮多选 + 确认 ===
                season_available = [
                    ("经典 (S1)", "S1"),
                    ("被动 (S2)", "S2"),
                    ("同盟 (S3)", "S3"),
                    ("补丁 (S4)", "S4"),
                ]
                if os.path.isfile(os.path.join(mods_dir, "LOD.py")):
                    season_available.append(("生死 (LOD)", "LOD"))

                picked = []
                while True:
                    opts = []
                    for label, sid in season_available:
                        mark = "✓ " if sid in picked else "  "
                        opts.append(f"{mark}{label}")
                    opts.append(f"确认选择 ({','.join(picked) if picked else 'S1 默认'})")
                    opts.append("自定义...")

                    choice = self.textual_ui.choose_from(
                        f"选择赛季（已选 {len(picked)} 个）", opts)
                    if choice.startswith("确认选择"):
                        seasons = picked if picked else ["S1"]
                        break
                    if choice == "自定义...":
                        custom = self.textual_ui.input(
                            "输入 Mod 的 SEASON_ID（逗号分隔）: ").strip()
                        if custom:
                            parsed = []
                            invalid = []
                            for p in [x.strip() for x in custom.split(",") if x.strip()]:
                                if p in ("S1", "S2", "S3", "S4"):
                                    parsed.append(p)
                                elif os.path.isfile(os.path.join(mods_dir, f"{p}.py")):
                                    parsed.append(p)
                                else:
                                    invalid.append(p)
                            if invalid:
                                self.textual_ui.show(
                                    f"[bold red]未找到：{', '.join(invalid)}[/bold red]")
                                continue
                            seasons = parsed
                            break
                        continue
                    for label, sid in season_available:
                        if choice.endswith(label):
                            if sid in picked:
                                picked.remove(sid)
                            else:
                                picked.append(sid)
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
        #card-bar {
            height: auto;
            max-height: 24;
            padding: 1;
            background: #161b22;
            border-top: solid #30363d;
            layout: grid;
            grid-size: 4;
            grid-rows: 4;
            overflow-y: auto;
        }
        #card-bar Button {
            width: 100%;
            min-width: 8;
            height: 4;
            margin: 0;
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
