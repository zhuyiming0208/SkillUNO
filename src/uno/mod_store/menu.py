"""模组商店主菜单页面。"""
from uno.mod_store import input_handler as ih
from uno.mod_store.router import Action
from uno.mod_store.render import (
    draw_box, pad_text, colorize, display_width,
)


class MainMenu:
    """主菜单：官方模组区 + 精选模组区 + 操作栏。"""

    MAX_HANDPICKED_DISPLAY = 8
    BOX_WIDTH = 60

    def __init__(self, mod_index):
        self.mod_index = mod_index
        self.official = mod_index.get_official()
        self.handpicked = mod_index.get_handpicked()
        self.selected = 0

        displayed = min(len(self.handpicked), self.MAX_HANDPICKED_DISPLAY)
        self.total_items = len(self.official) + displayed
        if self.total_items == 0:
            self.total_items = 1  # 至少允许一个"选中"

    # ---------- 渲染 ----------
    def render(self) -> str:
        lines = []

        # 标题
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
        displayed = self.handpicked[:self.MAX_HANDPICKED_DISPLAY]
        if not displayed:
            lines.append("  （暂无精选模组）")
        else:
            base = len(self.official)
            for i, mod in enumerate(displayed):
                real_idx = base + i
                lines.append(self._render_mod_item(real_idx, mod))
            extra = len(self.handpicked) - len(displayed)
            if extra > 0:
                lines.append(colorize(f"  还有 {extra} 个，按 S 搜索", "dim"))
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
            return Action.HELP
        if key.type == ih.EventType.ENTER:
            return Action.DETAIL
        if key.type == ih.EventType.BACK:
            return Action.QUIT  # 主菜单按 BACK 直接退出
        return None