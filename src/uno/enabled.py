"""模组启用状态（disabled 列表）。

文件格式：
    {"version": "1.0.0", "disabled": ["MOD_A", "MOD_B"]}

不在 disabled 列表中的已安装模组 = 启用。
文件不存在 = 全部启用（向后兼容）。
"""
import os
import json


def load_disabled(enabled_path):
    """读取 disabled 集合。文件不存在/损坏返回空集合。"""
    if not enabled_path:
        return set()
    try:
        with open(enabled_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return set()
    if not isinstance(data, dict):
        return set()
    disabled = data.get("disabled", [])
    if not isinstance(disabled, list):
        return set()
    return set(str(x) for x in disabled)


def save_disabled(disabled, enabled_path):
    """原子写入。"""
    if not enabled_path:
        raise ValueError("enabled_path 不能为空")
    parent = os.path.dirname(enabled_path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    tmp = enabled_path + ".tmp"
    if os.path.exists(tmp):
        try:
            os.remove(tmp)
        except OSError:
            pass
    data = {"version": "1.0.0", "disabled": sorted(disabled)}
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, enabled_path)


def is_mod_enabled(mod_id, enabled_path):
    """mod_id 在 disabled 列表 → False，否则 True。"""
    return mod_id not in load_disabled(enabled_path)


def set_mod_enabled(mod_id, enabled, enabled_path):
    """True：从 disabled 移除。False：加入 disabled。幂等。"""
    disabled = load_disabled(enabled_path)
    if enabled:
        disabled.discard(mod_id)
    else:
        disabled.add(mod_id)
    save_disabled(disabled, enabled_path)
