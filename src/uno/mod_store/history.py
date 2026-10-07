"""模组商店历史记录。

注意：字段名与 ModIndex.load_mod() 返回的字典一致（ID 大写）。
所有函数显式接收 history_path，不依赖默认路径。
"""
import os
import json
import datetime


ACTION_LABELS = {
    "downloaded":   "下载",
    "enabled":      "启用",
    "kept_pending": "待启用",
    "updated":      "更新",
    "uninstalled":  "卸载",
}

VALID_ACTIONS = {"downloaded", "enabled", "kept_pending", "updated", "uninstalled"}
VALID_STATUSES = {"enabled", "pending", "uninstalled"}

MAX_RECORDS = 500
MAX_DISPLAY = 50


def _empty_history():
    return {"version": "1.0.0", "records": []}


def load_history(history_path):
    if not history_path:
        return _empty_history()
    try:
        with open(history_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return _empty_history()
    if not isinstance(data, dict):
        return _empty_history()
    if "version" not in data:
        data["version"] = "1.0.0"
    if not isinstance(data.get("records"), list):
        data["records"] = []
    return data


def save_history(history, history_path):
    if not history_path:
        raise ValueError("history_path 不能为空")
    parent = os.path.dirname(history_path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    tmp = history_path + ".tmp"
    if os.path.exists(tmp):
        try:
            os.remove(tmp)
        except OSError:
            pass
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)
    os.replace(tmp, history_path)


def add_record(mod_data, action, status, history_path, max_records=MAX_RECORDS):
    if action not in VALID_ACTIONS:
        raise ValueError(f"非法 action：{action}")
    if status not in VALID_STATUSES:
        raise ValueError(f"非法 status：{status}")
    required = ["ID", "name", "author", "version", "repo"]
    for field in required:
        if field not in mod_data:
            raise ValueError(f"模组数据缺少字段：{field}")
    record = {
        "time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "mod_id": mod_data["ID"],
        "mod_name": mod_data["name"],
        "author": mod_data["author"],
        "version": mod_data["version"],
        "repo": mod_data["repo"],
        "action": action,
        "status": status,
    }
    history = load_history(history_path)
    history["records"].append(record)
    while len(history["records"]) > max_records:
        history["records"].pop(0)
    save_history(history, history_path)


def find_records(mod_id, history_path):
    history = load_history(history_path)
    filtered = [r for r in history["records"] if r.get("mod_id") == mod_id]
    return filtered[::-1]


def check_downloaded(mod_id, history_path):
    records = find_records(mod_id, history_path)
    return records[0] if records else None
