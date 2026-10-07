"""卸载模组。"""
import os

from uno.enabled import load_disabled, save_disabled


def uninstall_mod(mod_id, ctx):
    """卸载模组。返回 (是否成功, 消息)。

    清理目标：
      1. mods/{ID}.py
      2. mods/_pending/{ID}.py
      3. enabled.json 的 disabled 列表

    文件不存在视为"已删"。删除失败返回 (False, 原因)。
    两个文件都成功后，才从 disabled 移除。
    """
    mods_dir = os.path.dirname(ctx.history_path) if ctx.history_path else "mods"
    # 从历史路径推断 mods 目录（history_path 通常在 mods/ 下）
    # 更保险：用 enabled_path 的目录
    if ctx.enabled_path:
        mods_dir = os.path.dirname(ctx.enabled_path) or mods_dir

    installed = os.path.join(mods_dir, f"{mod_id}.py")
    pending = os.path.join(mods_dir, "_pending", f"{mod_id}.py")

    deleted_any = False
    for path in (installed, pending):
        if os.path.isfile(path):
            try:
                os.remove(path)
                deleted_any = True
            except OSError as e:
                return (False, f"删除 {path} 失败：{e}")

    # 从 disabled 移除（不阻塞）
    state_msg = ""
    try:
        disabled = load_disabled(ctx.enabled_path)
        if mod_id in disabled:
            disabled.discard(mod_id)
            save_disabled(disabled, ctx.enabled_path)
    except Exception as e:
        state_msg = f"（状态清理失败：{e}）"

    if not deleted_any:
        return (True, f"模组未安装，无需卸载{state_msg}")
    return (True, f"已卸载 {mod_id}{state_msg}")
