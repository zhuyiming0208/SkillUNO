"""下载确认页。"""
from uno.mod_store import input_handler as ih
from uno.mod_store.render import draw_box, pad_text, colorize
from uno.mod_store.history import check_downloaded


def _fmt_dict(d):
    if not isinstance(d, dict) or not d:
        return "无"
    return ", ".join(f"{k} ({v})" for k, v in d.items())


def _fmt_list(lst):
    if not isinstance(lst, list) or not lst:
        return "无"
    return ", ".join(str(x) for x in lst)


class ConfirmPage:
    BOX_WIDTH = 74

    def __init__(self, mod_data, existing=None, mod_index=None, history_path=None,
                 is_update=False, local_version=None, latest_version=None):
        self.mod = mod_data
        self.existing = existing
        self.mod_index = mod_index
        self.history_path = history_path
        self.is_update = is_update
        self.local_version = local_version
        self.latest_version = latest_version
        self.error = None
        try:
            self.last_record = (
                check_downloaded(mod_data.get("ID", ""), history_path)
                if history_path else None
            )
        except Exception:
            self.last_record = None

    def render(self) -> str:
        mod = self.mod
        lines = []
        title = "更新模组" if self.is_update else "确认下载"
        lines.append(colorize(pad_text(title, self.BOX_WIDTH, "center"),
                              "bright_cyan"))
        lines.append("")
        lines.append(f"  模组：{mod.get('name', '?')}")
        lines.append(f"  作者：{mod.get('author', '?')}")
        if self.is_update and self.local_version and self.latest_version:
            lines.append(f"  版本：v{self.local_version} → v{self.latest_version}")
        else:
            lines.append(f"  版本：{mod.get('version', '?')}")
        lines.append(f"  来源：{mod.get('repo', '?')}")
        lines.append("")
        lines.append(
            f"  此模组将加入：{mod.get('skills', 0)} 张技能牌、"
            f"{mod.get('achievements', 0)} 个成就"
        )
        needs = mod.get("needs") or []
        needs_str = ", ".join(needs) if needs else "未声明"
        lines.append(f"  此模组声明使用：{needs_str}")
        lines.append("")
        lines.append(f"  依赖：{_fmt_dict(mod.get('rely_on'))}")
        lines.append(f"  排斥：{_fmt_dict(mod.get('reject'))}")
        lines.append(f"  白名单：{_fmt_list(mod.get('only_tolerate'))}")
        lines.append("")
        if self.last_record:
            r = self.last_record
            t = (r.get("time") or "")[:16]
            ver = r.get("version", "?")
            status = r.get("status")
            if status == "uninstalled":
                lines.append(colorize(
                    f"  ⚠️ 该模组曾被卸载（{t}）。继续将重新下载。", "red"
                ))
            else:
                lines.append(colorize(
                    f"  ⚠️ 检测到历史记录：{t} 下载过 v{ver}。继续将重新下载。",
                    "red"
                ))
            lines.append("")
        if self.existing:
            loc = self.existing.get("location")
            path = self.existing.get("path", "")
            if loc == "installed":
                lines.append(colorize(
                    f"  ⚠️ 检测到已安装同 ID 模组：{path}，继续将覆盖已安装版本。",
                    "red"))
            elif loc == "pending":
                lines.append(colorize(
                    f"  ⚠️ 检测到待启用同 ID 模组：{path}，继续将重新下载并覆盖。",
                    "red"))
            lines.append("")
        if self.error:
            lines.append(colorize(f"  ❌ {self.error}", "red"))
            lines.append("")
            lines.append(colorize("  按任意键返回...", "dim"))
            return draw_box(lines, self.BOX_WIDTH)
        lines.append(colorize(
            "  ⚠️ 启用后，模组代码将在游戏下次启动时执行。", "red"))
        lines.append(colorize(
            "     请确认作者可信。若不放心，可保留在 _pending/ 不启用。", "red"))
        lines.append("")
        lines.append(colorize(
            "  若下载后 ID 与已有模组冲突，将拒绝启用。", "dim"))
        lines.append("")
        if self.is_update:
            lines.append(colorize("  Y 确认更新 | N / ~ 返回", "dim"))
        else:
            lines.append(colorize("  Y 确认下载 | N / ~ 返回", "dim"))
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
