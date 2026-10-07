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

    def __init__(self, mod_index, history_path=None, enabled_path=None, mods_dir=None,
                 collections_path=None):
        self.mod_index = mod_index
        self.history_path = history_path
        self.enabled_path = enabled_path
        self.mods_dir = mods_dir
        self.collections_path = collections_path
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

        self._refresh_state()
        self._load_collections()

        self.total_items = (len(self.official) + len(self.handpicked)
                            + min(3, len(self._collections)))
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

        # 模组集区
        lines.append(colorize("【模组集】", "bright_yellow"))
        if not self._collections:
            lines.append("  暂无模组集")
        else:
            base = len(self.official) + len(self.handpicked)
            for i, c in enumerate(self._collections[:3]):
                real_idx = base + i
                lines.append(self._render_collection_item(real_idx, c))
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
        mark = self._state_mark(mod.get("id"))
        mark_str = f"  {mark}" if mark else ""
        text = f"{prefix}{name}  技能×{skills}  {tag}{mark_str}"
        if self.selected == idx:
            text = colorize(text, "bright_cyan")
        return text

    def _render_mod_item(self, idx, mod) -> str:
        prefix = "> " if self.selected == idx else "  "
        name = mod.get("name", "?")
        author = mod.get("author", "?")
        version = mod.get("version", "?")
        skills = mod.get("skills", 0)
        mark = self._state_mark(mod.get("ID"))
        mark_str = f"  {mark}" if mark else ""
        text = f"{prefix}{name}  by {author}  v{version}  技能×{skills}{mark_str}"
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
        if key.type == ih.EventType.CHAR and key.char:
            ch = key.char.lower()
            if ch == "u":
                mod = self.current_mod()
                if mod is None:
                    return None
                mod_id = mod.get("ID") or mod.get("id")
                info = self._update_info(mod_id)
                if info is None:
                    return None
                return (Action.UPDATE, {
                    "mod_data": info["mod_data"],
                    "local_version": info["local_version"],
                    "latest_version": info["latest_version"],
                })
        if key.type == ih.EventType.ENTER:
            kind, item = self.current_item()
            if item is None:
                return None
            if kind == "collection":
                return (Action.COLLECTION, item)
            return (Action.DETAIL, item)
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

    def _refresh_state(self):
        from uno.mod_store.updater import list_installed_mods, check_updates
        from uno.enabled import load_disabled
        self._installed = list_installed_mods(self.mods_dir) if self.mods_dir else []
        self._installed_ids = {m["id"] for m in self._installed}
        try:
            self._updates = check_updates(self._installed, self.mod_index)
        except Exception:
            self._updates = []
        self._update_ids = {u["id"] for u in self._updates}
        if self.enabled_path:
            try:
                self._disabled_ids = load_disabled(self.enabled_path)
            except Exception:
                self._disabled_ids = set()
        else:
            self._disabled_ids = set()

    def refresh_updates(self):
        """路由在更新/卸载/启用成功后调用。"""
        self._refresh_state()

    def _state_mark(self, mod_id):
        """状态标记优先级：↑ > ✓ > ○"""
        if not mod_id:
            return ""
        if mod_id in self._update_ids:
            return "↑"
        if mod_id in self._installed_ids:
            if mod_id in self._disabled_ids:
                return "○"
            return "✓"
        return ""

    def _update_info(self, mod_id):
        for u in self._updates:
            if u["id"] == mod_id:
                return u
        return None


    def _load_collections(self):
        from uno.mod_store.collections import load_collections
        if not self.collections_path:
            self._collections = []
            return
        try:
            data = load_collections(self.collections_path)
            self._collections = data.get("collections", [])
        except Exception:
            self._collections = []

    def _render_collection_item(self, idx, coll) -> str:
        prefix = "> " if self.selected == idx else "  "
        name = coll.get("name", "?")
        count = len(coll.get("mods", []))
        text = f"{prefix}{name}  ({count} 个模组)"
        if self.selected == idx:
            text = colorize(text, "bright_cyan")
        return text

    def current_item(self):
        """返回 (kind, item)。kind 是 'official' / 'handpicked' / 'collection'。"""
        idx = self.selected
        if idx < len(self.official):
            return ("official", self.official[idx])
        idx -= len(self.official)
        if idx < len(self.handpicked):
            return ("handpicked", self.handpicked[idx])
        idx -= len(self.handpicked)
        if idx < len(self._collections):
            return ("collection", self._collections[idx])
        return (None, None)
