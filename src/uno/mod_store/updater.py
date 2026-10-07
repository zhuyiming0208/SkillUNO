"""更新检查与版本比较。"""
import os
import ast


BUILTIN_IDS = {"S1", "S2", "S3", "S4"}
_MAX_FILE_SIZE = 500 * 1024


def _parse_version(version):
    """返回 ((major, minor, patch), is_prerelease)。解析失败返回 ((0,0,0), False)。"""
    if not version:
        return (0, 0, 0), False
    v = str(version).strip()
    is_pre = False
    if "-" in v:
        v = v.split("-", 1)[0]
        is_pre = True
    parts = v.split(".")
    nums = []
    for p in parts[:3]:
        try:
            nums.append(int(p))
        except ValueError:
            return (0, 0, 0), False
    while len(nums) < 3:
        nums.append(0)
    return tuple(nums), is_pre


def _compare_versions(a, b):
    """返回 -1 / 0 / 1。
    1.2.0-beta < 1.2.0 < 1.2.1
    两个都有预发布标记 → 返回 0（不做字母序）
    """
    va, pa = _parse_version(a)
    vb, pb = _parse_version(b)
    if va != vb:
        return -1 if va < vb else 1
    if pa and not pb:
        return -1
    if not pa and pb:
        return 1
    return 0


def _extract_var(path, var_name):
    """从 .py 文件用 ast 提取指定顶层变量（字符串常量）。"""
    try:
        if os.path.getsize(path) > _MAX_FILE_SIZE:
            return None
        with open(path, "r", encoding="utf-8-sig") as f:
            src = f.read()
        tree = ast.parse(src)
    except (OSError, SyntaxError, ValueError):
        return None
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name) and t.id == var_name:
                    if (isinstance(node.value, ast.Constant)
                            and isinstance(node.value.value, str)):
                        return node.value.value
    return None


def list_installed_mods(mods_dir):
    """扫描 mods/ 目录（不含 _pending/），返回 [{"id", "version", "path"}, ...]。"""
    result = []
    if not mods_dir or not os.path.isdir(mods_dir):
        return result
    for fname in sorted(os.listdir(mods_dir)):
        if not fname.endswith(".py") or fname.startswith("_"):
            continue
        path = os.path.join(mods_dir, fname)
        if not os.path.isfile(path):
            continue
        mod_id = _extract_var(path, "SEASON_ID")
        if not mod_id:
            continue
        version = _extract_var(path, "__version__") or _extract_var(path, "SEASON_VERSION") or "0.0.0"
        result.append({"id": mod_id, "version": version, "path": path})
    return result


def check_updates(installed_mods, mod_index):
    """返回有更新的模组列表。

    installed_mods: [{"id", "version"}, ...]
    每项返回：{"id", "local_version", "latest_version", "mod_data"}
    跳过内置模组。
    """
    result = []
    for inst in installed_mods:
        mod_id = inst.get("id")
        if not mod_id or mod_id in BUILTIN_IDS:
            continue
        local = inst.get("version", "0.0.0")
        try:
            mod_data = mod_index.get_by_id(mod_id)
        except Exception:
            mod_data = None
        if mod_data is None:
            continue
        latest = mod_data.get("version", "0.0.0")
        if _compare_versions(local, latest) < 0:
            result.append({
                "id": mod_id,
                "local_version": local,
                "latest_version": latest,
                "mod_data": mod_data,
            })
    return result
