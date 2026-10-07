"""搜索页面：输入关键词 → 显示结果 → 选中进入详情。"""
from uno.mod_store import input_handler as ih
from uno.mod_store.router import Action
from uno.mod_store.render import (
    draw_box, pad_text, colorize,
)


class SearchPage:
    """搜索页。"""

    BOX_WIDTH = 70
    MAX_RESULTS = 20
    MAX_DISPLAY = 10

    def __init__(self, mod_index):
        self.mod_index = mod_index
        self.query = ""
        self.results = []
        self.selected = 0
        self.state = "INPUT"  # INPUT | RESULTS

    # ---------- 渲染 ----------
    def render(self) -> str:
        lines = []

        title = "搜索模组"
        lines.append(colorize(pad_text(title, self.BOX_WIDTH, "center"), "bright_cyan"))
        lines.append("")

        if self.state == "INPUT":
            lines.append(f"搜索（作者名或模组名）：{self.query}")
            lines.append("")
            lines.append(colorize("  回车确认 | ~ 取消", "dim"))
        else:
            lines.append(f"关键词：{self.query}")
            lines.append("")
            if not self.results:
                lines.append("  未找到匹配的模组")
                lines.append("")
                lines.append(colorize("  ~ 返回搜索", "dim"))
            else:
                for i, mod in enumerate(self.results[:self.MAX_DISPLAY]):
                    lines.append(self._render_result_item(i, mod))
                if len(self.results) > self.MAX_DISPLAY:
                    lines.append(colorize(
                        f"  还有 {len(self.results) - self.MAX_DISPLAY} 个，请细化搜索词",
                        "dim"
                    ))
                lines.append("")
                lines.append(colorize("  u/d 选择 | Enter 详情 | ~ 返回", "dim"))

        return draw_box(lines, self.BOX_WIDTH)

    def _render_result_item(self, idx, mod) -> str:
        prefix = "> " if self.selected == idx else "  "
        name = mod.get("name", "?")
        author = mod.get("author", "?")
        version = mod.get("version", "?")
        skills = mod.get("skills", 0)
        text = f"{prefix}{name}  by {author}  v{version}  技能×{skills}"
        if self.selected == idx:
            text = colorize(text, "bright_cyan")
        return text

    def wants_raw_input(self):
        """输入框状态需要原始字符输入，不要被键位映射吞掉。"""
        return self.state == "INPUT"

    # ---------- 按键 ----------
    def handle_key(self, key):
        if self.state == "INPUT":
            return self._handle_input(key)
        return self._handle_results(key)

    def _handle_input(self, key):
        if key.type == ih.EventType.BACK:
            return Action.BACK
        if key.type == ih.EventType.ENTER:
            self._do_search()
            return None
        if key.type == ih.EventType.BACKSPACE:
            if self.query:
                # 一次删一个字符（中文也只删 1 个）
                self.query = self.query[:-1]
            return None
        if key.type == ih.EventType.CHAR and key.char:
            if key.char.isprintable():
                self.query += key.char
            return None
        if key.type == ih.EventType.QUIT:
            return Action.QUIT
        return None

    def _handle_results(self, key):
        if key.type == ih.EventType.BACK:
            # 返回搜索输入
            self.state = "INPUT"
            self.selected = 0
            return None
        if key.type == ih.EventType.UP:
            if self.results:
                self.selected = (self.selected - 1) % len(self.results)
            return None
        if key.type == ih.EventType.DOWN:
            if self.results:
                self.selected = (self.selected + 1) % len(self.results)
            return None
        if key.type == ih.EventType.ENTER:
            mod = self.current_mod()
            if mod is None:
                return None
            return (Action.DETAIL, mod)
        if key.type == ih.EventType.QUIT:
            return Action.QUIT
        return None

    def _do_search(self):
        keyword = self.query.strip()
        if self.mod_index is None:
            self.results = []
        else:
            self.results = self.mod_index.search(keyword, limit=self.MAX_RESULTS)
        self.state = "RESULTS"
        self.selected = 0

    def current_mod(self):
        if 0 <= self.selected < len(self.results):
            return self.results[self.selected]
        return None