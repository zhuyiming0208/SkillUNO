"""模组商店主菜单页面。"""
from uno.mod_store import input_handler as ih
from uno.mod_store.router import Action
from uno.mod_store.render import (
    draw_box, pad_text, colorize, display_width,
)


class MainMenu:
    """主菜单：官方模组区 + 精选模组区 + 操作栏。"""

    MAX_HANDPICKED_DISPLAY = 12
    BOX_WIDTH = 60

    def __init__(self, mod_index, history_path=None):
        self.mod_index = mod_index
        self.history_path = history_path
        self.official = mod_index.get_official()
        self.handpicked = mod_index.get_handpicked()
        self.selected = 0

        # 超过 12 个精选模组时，打印警告，只保留前 12 个
        if len(self.handpicked) > self.MAX_HANDPICKED_DISPLAY:
            print(
                f"警告：精选模组超过 {self.MAX_HANDPICKED_DISPLAY} 个"
                f"（当前 {len(self.handpicked)} 个），"
                f"只显示前 {self.MAX_HANDPICKED_DISPLAY} 个。"
            )
            self.handpicked = self.handpicked[:self.MAX_HANDPICKED_DISPLAY]

        self.total_items = len(self.official) + len(self.handpicked)
        if self.total_items == 0:
            self.total_items = 1

    # ---------- 渲染 ----------
    def render(self) -> str:
        lines = []

        title = "SkillUNO 模组商店"
        lines.append(colorize(pad_text(title, self.BOX_WIDTH, "center"), "bright_cyan"))
        lines.append("")

        # 官方模组区
        lines.append(colorize("【官方模组】", "bright_yellow"))
        if self.official:
            for i, mod in enumerate(self.official):
                lines.append(self._render_official_item(i, mod))
        else:
            lines.append("  （暂无官方模组）")
        lines.append("")

        # 精选模组区
        lines.append(colorize("【精选模组】", "bright_yellow"))
        if not self.handpicked:
            lines.append("  暂无精选模组")
        else:
            base = len(self.official)
            for i, mod in enumerate(self.handpicked):
                real_idx = base + i
                lines.append(self._render_mod_item(real_idx, mod))
        lines.append("")

        # 操作栏
        bar = "u/d 选择 | Enter 详情 | S 搜索 | H 历史 | Q 退出"
        lines.append(colorize(bar, "dim"))

        return draw_box(lines, self.BOX_WIDTH)

    def _render_official_item(self, idx, mod) -> str:
        prefix = "> " if self.selected == idx else "  "
        name = mod.get("name", "?")
        skills = mod.get("skills", 0)
        tag = colorize("[内置]", "green")
        text = f"{prefix}{name}  技能×{skills}  {tag}"
        if self.selected == idx:
            text = colorize(text, "bright_cyan")
        return text

    def _render_mod_item(self, idx, mod) -> str:
        prefix = "> " if self.selected == idx else "  "
        name = mod.get("name", "?")
        author = mod.get("author", "?")
        version = mod.get("version", "?")
        skills = mod.get("skills", 0)
        text = f"{prefix}{name}  by {author}  v{version}  技能×{skills}"
        if self.selected == idx:
            text = colorize(text, "bright_cyan")
        return text

    # ---------- 按键 ----------
    def handle_key(self, key):
        if key.type == ih.EventType.UP:
            self.selected = (self.selected - 1) % self.total_items
            return None
        if key.type == ih.EventType.DOWN:
            self.selected = (self.selected + 1) % self.total_items
            return None
        if key.type == ih.EventType.QUIT:
            return Action.QUIT
        if key.type == ih.EventType.SEARCH:
            return Action.SEARCH
        if key.type == ih.EventType.HELP:
            return Action.HISTORY
        if key.type == ih.EventType.ENTER:
            mod = self.current_mod()
            if mod is None:
                return None
            return (Action.DETAIL, mod)
        if key.type == ih.EventType.BACK:
            return Action.QUIT
        return None

    def current_mod(self):
        """返回当前选中项的模组数据。"""
        if self.selected < len(self.official):
            return self.official[self.selected]
        idx = self.selected - len(self.official)
        if 0 <= idx < len(self.handpicked):
            return self.handpicked[idx]
        return None