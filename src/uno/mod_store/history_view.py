"""历史记录页面。"""
from uno.mod_store import input_handler as ih
from uno.mod_store.router import Action
from uno.mod_store.render import draw_box, pad_text, colorize
from uno.mod_store.history import load_history, ACTION_LABELS, MAX_DISPLAY


_STATUS_MARKS = {
    "enabled": "✓ 已启用",
    "pending": "○ 待启用",
    "uninstalled": "✗ 已卸载",
}


class HistoryPage:
    BOX_WIDTH = 74

    def __init__(self, history_path, mod_index):
        self.history_path = history_path
        self.mod_index = mod_index
        history = load_history(history_path)
        self.records = history.get("records", [])[::-1][:MAX_DISPLAY]
        self.total = len(history.get("records", []))
        self.selected = 0
        self.message = None

    def render(self) -> str:
        lines = []
        title = "下载历史"
        lines.append(colorize(pad_text(title, self.BOX_WIDTH, "center"),
                              "bright_cyan"))
        lines.append("")
        if self.message:
            lines.append(colorize(f"  {self.message}", "yellow"))
            lines.append("")
            lines.append(colorize("  按任意键继续...", "dim"))
            return draw_box(lines, self.BOX_WIDTH)
        if not self.records:
            lines.append("  暂无下载历史")
            lines.append("")
            lines.append(colorize("  Q / ~ 返回", "dim"))
            return draw_box(lines, self.BOX_WIDTH)
        for i, r in enumerate(self.records):
            prefix = "> " if self.selected == i else "  "
            t = (r.get("time") or "")[:16]
            name = r.get("mod_name", "?")
            author = r.get("author", "?")
            version = r.get("version", "?")
            action_cn = ACTION_LABELS.get(r.get("action", ""), r.get("action", "?"))
            status_mark = _STATUS_MARKS.get(r.get("status", ""), "")
            text = (
                f"{prefix}{t}  {name} ({author})  "
                f"v{version}  {action_cn}  {status_mark}"
            )
            if self.selected == i:
                text = colorize(text, "bright_cyan")
            lines.append(text)
        if self.total > MAX_DISPLAY:
            lines.append("")
            lines.append(colorize(
                f"  仅显示最近 {MAX_DISPLAY} 条，共 {self.total} 条", "dim"
            ))
        lines.append("")
        lines.append(colorize("  u/d 选择 | Enter 详情 | Q 返回", "dim"))
        return draw_box(lines, self.BOX_WIDTH)

    def handle_key(self, key):
        if self.message:
            self.message = None
            return None
        if key.type in (ih.EventType.QUIT, ih.EventType.BACK):
            return Action.BACK
        if key.type == ih.EventType.UP:
            if self.records:
                self.selected = (self.selected - 1) % len(self.records)
            return None
        if key.type == ih.EventType.DOWN:
            if self.records:
                self.selected = (self.selected + 1) % len(self.records)
            return None
        if key.type == ih.EventType.ENTER:
            if not self.records:
                return None
            record = self.records[self.selected]
            try:
                mod_data = self.mod_index.get_by_id(record["mod_id"])
            except Exception:
                mod_data = None
            if mod_data is None:
                self.message = "该模组已不在索引中"
                return None
            return (Action.DETAIL, mod_data)
        return None
