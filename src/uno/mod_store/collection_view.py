"""模组集详情页。"""
from uno.mod_store import input_handler as ih
from uno.mod_store.router import Action
from uno.mod_store.render import draw_box, pad_text, colorize


BUILTIN_IDS = {"S1", "S2", "S3", "S4"}


class CollectionView:
    BOX_WIDTH = 74

    def __init__(self, ctx, collection_data):
        self.ctx = ctx
        self.collection = collection_data

    def render(self) -> str:
        c = self.collection
        lines = []
        title = f"模组集 — {c.get('name', '?')}"
        lines.append(colorize(pad_text(title, self.BOX_WIDTH, "center"),
                              "bright_cyan"))
        lines.append("")
        lines.append(f"  {c.get('description', '')}")
        lines.append("")
        lines.append(colorize("【包含模组】", "bright_yellow"))

        mods = c.get("mods", [])
        installed_ids = self._installed_ids()
        for mid in mods:
            mark = self._state_mark(mid, installed_ids)
            builtin = "  [内置]" if mid in BUILTIN_IDS else ""
            lines.append(f"    {mid}  {mark}{builtin}")
        lines.append("")
        lines.append(colorize(
            "  I 一键安装全部 | Q 返回", "dim"))
        return draw_box(lines, self.BOX_WIDTH)

    def _installed_ids(self):
        import os
        ids = set()
        # 从 enabled_path 推断 mods_dir
        mods_dir = None
        if getattr(self.ctx, "enabled_path", None):
            mods_dir = os.path.dirname(self.ctx.enabled_path)
        if not mods_dir or not os.path.isdir(mods_dir):
            return ids
        from uno.mod_store.updater import list_installed_mods
        for m in list_installed_mods(mods_dir):
            ids.add(m["id"])
        return ids

    def _state_mark(self, mod_id, installed_ids):
        if mod_id in BUILTIN_IDS:
            return "✓"
        if mod_id in installed_ids:
            return "✓"
        return ""

    def handle_key(self, key):
        if key.type in (ih.EventType.QUIT, ih.EventType.BACK):
            return Action.BACK
        if key.type == ih.EventType.CHAR and key.char:
            ch = key.char.lower()
            if ch == "i":
                return (Action.INSTALL_ALL, self.collection)
            if ch == "q":
                return Action.BACK
        return None
