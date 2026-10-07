"""启用确认页。"""
from uno.mod_store import input_handler as ih
from uno.mod_store.render import draw_box, pad_text, colorize


class EnablePage:
    BOX_WIDTH = 74

    def __init__(self, season_id, pending_path):
        self.season_id = season_id
        self.pending_path = pending_path
        self.error = None

    def render(self) -> str:
        lines = []
        title = "启用模组"
        lines.append(colorize(pad_text(title, self.BOX_WIDTH, "center"), "bright_cyan"))
        lines.append("")
        lines.append(f"  下载成功：{self.pending_path}")
        lines.append(f"  静态验证通过，SEASON_ID：{self.season_id}")
        lines.append("")
        lines.append("  是否启用？启用后重启游戏生效。")
        lines.append("")

        if self.error:
            lines.append(colorize(f"  ❌ {self.error}", "red"))
            lines.append("")
            lines.append(colorize("  按任意键返回...", "dim"))
            return draw_box(lines, self.BOX_WIDTH)

        lines.append(colorize(
            "  ⚠️ 启用后，模组代码将在游戏下次启动时执行。", "red"
        ))
        lines.append(colorize(
            "     请确认作者可信。若不放心，可保留在 _pending/ 不启用。", "red"
        ))
        lines.append("")
        lines.append(colorize("  Y 启用 | N / ~ 保留在 _pending", "dim"))
        return draw_box(lines, self.BOX_WIDTH)

    def handle_key(self, key):
        if self.error:
            self.error = None
            return None

        if key.type in (ih.EventType.BACK, ih.EventType.QUIT):
            return "KEEP_PENDING"

        if key.type == ih.EventType.CHAR and key.char:
            ch = key.char.lower()
            if ch == "y":
                return "ENABLE"
            if ch == "n":
                return "KEEP_PENDING"
        return None