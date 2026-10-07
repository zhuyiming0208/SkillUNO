"""模组集数据层。"""
import os
import json


def _empty():
    return {"version": "1.0.0", "collections": []}


def load_collections(path):
    """读取模组集文件。不存在/损坏返回空结构。"""
    if not path:
        return _empty()
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return _empty()
    if not isinstance(data, dict):
        return _empty()
    if "version" not in data:
        data["version"] = "1.0.0"
    if not isinstance(data.get("collections"), list):
        data["collections"] = []
    return data


def save_collections(collections, path):
    """原子写入。"""
    if not path:
        raise ValueError("path 不能为空")
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    tmp = path + ".tmp"
    if os.path.exists(tmp):
        try:
            os.remove(tmp)
        except OSError:
            pass
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(collections, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


def get_collection(collection_id, path):
    """按 ID 查找。"""
    data = load_collections(path)
    for c in data["collections"]:
        if c.get("id") == collection_id:
            return c
    return None
