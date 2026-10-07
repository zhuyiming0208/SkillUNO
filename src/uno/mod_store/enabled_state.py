"""商店侧的启用状态包装。"""
from uno.enabled import (
    load_disabled, save_disabled, is_mod_enabled, set_mod_enabled,
)


def load_state(enabled_path):
    return {"disabled": sorted(load_disabled(enabled_path))}


def set_enabled(mod_id, enabled, enabled_path):
    set_mod_enabled(mod_id, enabled, enabled_path)
