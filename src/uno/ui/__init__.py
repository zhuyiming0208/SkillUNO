import os

try:
    from rich.console import Console as RichConsole
    RICH_AVAILABLE = True
except ImportError:
    RichConsole = None
    RICH_AVAILABLE = False


class ConsoleUI:
    """默认命令行 UI，用于解耦输入输出"""
    def choose_action(self, player, game, top_card, current_color):
        """结构化动作入口。

        返回 None 表示「不支持结构化动作」，调用方走原有 human_choose 流程。
        ConsoleUI / RichUI / NullUI 均返回 None，CLI 行为零变化。
        """
        return None

    def show(self, text=""):
        print(text)

    def show_error(self, text=""):
        print(f"\033[91m{text}\033[0m")

    def input(self, prompt=""):
        return input(prompt)

    def print_inline(self, text="", end=''):
        print(text, end=end)

    def clear_screen(self):
        os.system('cls' if os.name == 'nt' else 'clear')

    def pause(self, message=""):
        return input(message)


class NullUI(ConsoleUI):
    """给 AI 使用的哑巴 UI：不显示、不输入"""
    def show(self, text=""):
        pass

    def show_error(self, text=""):
        pass

    def input(self, prompt=""):
        return ""

    def print_inline(self, text="", end=''):
        pass

    def clear_screen(self):
        pass

    def pause(self, message=""):
        return ""


class RichUI(ConsoleUI):
    """彩色 UI（需要 rich 依赖）"""
    def __init__(self):
        if not RICH_AVAILABLE:
            raise RuntimeError(
                "rich 未安装，无法使用彩色界面。"
                "请运行 pip install rich 或 pip install 'skilluno[rich]'")
        self.console = RichConsole()

    def show(self, text=""):
        from rich import print as rprint
        rprint(text)

    def input(self, prompt=""):
        self.console.print(prompt, end='')
        return input()

    def print_inline(self, text="", end=''):
        self.console.print(text, end=end)

    def clear_screen(self):
        self.console.clear()

    def pause(self, message=""):
        self.console.print(message, end='')
        return input()

    # ---- 彩色专用辅助方法 ----
    def show_warning(self, text):
        self.console.print(f"[bold red]{text}[/bold red]")

    def show_success(self, text):
        self.console.print(f"[bold green]{text}[/bold green]")

    def show_golden(self, text):
        self.console.print(f"[bold gold1]{text}[/bold gold1]")

    def show_card(self, card):
        color_map = {'红': 'red', '蓝': 'blue', '绿': 'green', '黄': 'yellow', '黑': 'grey70'}
        style = color_map.get(card.color, 'white')
        self.console.print(f"[{style}]{card}[/{style}]")

    def show_hand(self, cards):
        for i, card in enumerate(cards):
            color_map = {'红': 'red', '蓝': 'blue', '绿': 'green', '黄': 'yellow', '黑': 'grey70'}
            style = color_map.get(card.color, 'white')
            self.console.print(f"[{style}][{i}]{card}[/{style}]", end=' ')
        self.console.print()

    def show_skill(self, skill):
        if skill.is_deleted:
            self.console.print("[grey50]???[/grey50]")
        elif skill.is_consumed:
            self.console.print(f"[grey50]{skill.name}(已用)[/grey50]")
        else:
            self.console.print(f"[bold cyan]{skill.name}[/bold cyan]")

    def show_turn_header(self, player):
        self.console.print(f"\n===== [bold blue]{player.name}[/bold blue] 的回合 =====")

    def show_uno_reminder(self, player):
        self.console.print(f"🔔 [bold yellow]{player.name} 喊了 UNO！[/bold yellow]")