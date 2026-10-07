"""模组详情页。"""
from uno.mod_store import input_handler as ih
from uno.mod_store.router import Action
from uno.mod_store.render import (
    draw_box, pad_text, colorize,
)


class DetailPage:
    """显示单个模组的详细信息。"""

    BOX_WIDTH = 70

    def __init__(self, mod_data, mod_index=None, history_path=None):
        self.mod = mod_data
        self.mod_index = mod_index
        self.history_path = history_path

    # ---------- 渲染 ----------
    def render(self) -> str:
        mod = self.mod
        lines = []

        # 标题
        name = mod.get("name", "?")
        title = f"模组详情 — {name}"
        lines.append(colorize(pad_text(title, self.BOX_WIDTH, "center"), "bright_cyan"))
        lines.append("")

        # 基本信息
        lines.append(colorize("【基本信息】", "bright_yellow"))
        lines.append(f"  名称：{name}")
        author = mod.get("author", "?")
        author_github = mod.get("author_github", "")
        if author_github:
            lines.append(f"  作者：{author} (@{author_github})")
        else:
            lines.append(f"  作者：{author}")
        lines.append(f"  版本：{mod.get('version', '?')}")
        micover = mod.get("micover", "?")
        lacover = mod.get("lacover")
        if lacover is None:
            lines.append(f"  兼容性：{micover} ~ 任意版本")
        else:
            lines.append(f"  兼容性：{micover} ~ {lacover}")
        lines.append(f"  GitHub：{mod.get('repo', '?')}")
        license_ = mod.get("license")
        if license_:
            lines.append(f"  协议：{license_}")
        lines.append("")

        # 简介
        lines.append(colorize("【简介】", "bright_yellow"))
        desc = mod.get("description", "（无）")
        lines.append(f"  {desc}")
        lines.append("")

        # 技能预览
        lines.append(colorize("【技能】", "bright_yellow"))
        skills_count = mod.get("skills", 0)
        lines.append(f"  共 {skills_count} 个技能")
        skill_names = mod.get("skill_names") or mod.get("skills_list")
        if isinstance(skill_names, list) and skill_names:
            for s in skill_names:
                lines.append(f"    - {s}")
        else:
            lines.append("    技能详情请查看源码")
        lines.append("")

        # 关系
        lines.append(colorize("【关系】", "bright_yellow"))
        rely_on = mod.get("rely_on") or {}
        reject = mod.get("reject") or {}
        tolerate = mod.get("only_tolerate") or []
        lines.append(f"  依赖：{self._format_dict(rely_on) if rely_on else '无'}")
        lines.append(f"  排斥：{self._format_dict(reject) if reject else '无'}")
        lines.append(f"  白名单：{self._format_list(tolerate) if tolerate else '无'}")
        lines.append("")

        # 权限
        lines.append(colorize("【权限声明】", "bright_yellow"))
        needs = mod.get("needs") or []
        if needs:
            for n in needs:
                lines.append(f"  - {n}")
        else:
            lines.append("  未声明")
        lines.append("")

        # 操作栏
        lines.append(colorize("  I 安装 | R 查看源码 | Q 返回", "dim"))

        return draw_box(lines, self.BOX_WIDTH)

    def _format_dict(self, d):
        if not isinstance(d, dict):
            return str(d)
        return ", ".join(f"{k} ({v})" for k, v in d.items())

    def _format_list(self, lst):
        if not isinstance(lst, list):
            return str(lst)
        return ", ".join(str(x) for x in lst)

    # ---------- 按键 ----------
    def handle_key(self, key):
        if key.type in (ih.EventType.QUIT, ih.EventType.BACK):
            return Action.BACK

        if key.type == ih.EventType.CHAR and key.char:
            ch = key.char.lower()
            if ch == 'i':
                return "INSTALL"
            if ch == 'r':
                return "VIEW_SOURCE"

        return None