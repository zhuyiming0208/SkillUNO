"""卸载确认页。"""
import os

from uno.mod_store import input_handler as ih
from uno.mod_store.render import draw_box, pad_text, colorize


class UninstallConfirmPage:
    BOX_WIDTH = 74

    def __init__(self, ctx, mod_data):
        self.ctx = ctx
        self.mod = mod_data
        self.error = None

    def render(self) -> str:
        mod = self.mod
        mod_id = mod.get("ID", "?")
        mods_dir = os.path.dirname(self.ctx.enabled_path) if self.ctx.enabled_path else "mods"
        installed = os.path.join(mods_dir, f"{mod_id}.py")
        pending = os.path.join(mods_dir, "_pending", f"{mod_id}.py")

        lines = []
        title = "卸载模组"
        lines.append(colorize(pad_text(title, self.BOX_WIDTH, "center"), "bright_cyan"))
        lines.append("")
        lines.append(f"  模组：{mod.get('name', '?')}")
        lines.append(f"  版本：{mod.get('version', '?')}")
        lines.append("")
        lines.append("  将删除以下文件（若存在）：")
        lines.append(f"    - {installed}")
        lines.append(f"    - {pending}")
        lines.append("")
        lines.append("  此操作会删除 mods/{{ID}}.py 和 mods/_pending/{{ID}}.py，历史记录保留。".replace("{{ID}}", mod_id))
        lines.append("")
        if self.error:
            lines.append(colorize(f"  ❌ {self.error}", "red"))
            lines.append("")
            lines.append(colorize("  按任意键返回...", "dim"))
            return draw_box(lines, self.BOX_WIDTH)
        lines.append(colorize("  ⚠️ 卸载后模组代码不会在游戏下次启动时执行。", "red"))
        lines.append(colorize("     历史记录保留，可以重新下载。", "dim"))
        lines.append("")
        lines.append(colorize("  Y 确认卸载 | N / ~ 返回", "dim"))
        return draw_box(lines, self.BOX_WIDTH)

    def handle_key(self, key):
        if self.error:
            self.error = None
            return None
        if key.type in (ih.EventType.BACK, ih.EventType.QUIT):
            return "BACK"
        if key.type == ih.EventType.CHAR and key.char:
            ch = key.char.lower()
            if ch == "y":
                return "CONFIRM"
            if ch == "n":
                return "BACK"
        return None
