"""静态验证下载的模组文件。绝不执行文件内容。"""
import ast
import os


MAX_AST_SIZE = 500 * 1024  # 500 KB
OFFICIAL_IDS = {"S1", "S2", "S3", "S4"}


def check_syntax(file_path):
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            source = f.read()
    except OSError as e:
        return (False, f"读取失败：{e}")
    try:
        ast.parse(source, filename=file_path)
        return (True, "")
    except SyntaxError as e:
        return (False, f"语法错误：{e}")


def extract_season_id(file_path):
    try:
        size = os.path.getsize(file_path)
    except OSError as e:
        return (None, f"读取失败：{e}")
    if size > MAX_AST_SIZE:
        return (None, "文件过大，拒绝验证")
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            source = f.read()
    except OSError as e:
        return (None, f"读取失败：{e}")
    try:
        tree = ast.parse(source, filename=file_path)
    except SyntaxError as e:
        return (None, f"语法错误：{e}")

    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "SEASON_ID":
                    value = node.value
                    if isinstance(value, ast.Constant) and isinstance(value.value, str):
                        return (value.value, "")
                    return (None, "SEASON_ID 不是字符串常量")
    return (None, "缺少 SEASON_ID")


def check_id_conflict(season_id, mods_dir="mods", official_ids=None):
    if official_ids is None:
        official_ids = OFFICIAL_IDS
    if season_id in official_ids:
        return (True, f"模组 ID 与官方赛季冲突：{season_id}")
    if not os.path.isdir(mods_dir):
        return (False, "")
    for fname in os.listdir(mods_dir):
        if not fname.endswith(".py") or fname == "__init__.py":
            continue
        fpath = os.path.join(mods_dir, fname)
        if not os.path.isfile(fpath):
            continue
        sid, _ = extract_season_id(fpath)
        if sid == season_id:
            return (True, f"模组 ID 与已安装模组冲突：{season_id}")
    return (False, "")


def validate_download(file_path, mods_dir="mods", official_ids=None):
    """返回 (是否通过, 错误信息, SEASON_ID)。"""
    ok, msg = check_syntax(file_path)
    if not ok:
        return (False, msg, None)
    sid, msg = extract_season_id(file_path)
    if sid is None:
        return (False, msg, None)
    conflict, msg = check_id_conflict(sid, mods_dir=mods_dir, official_ids=official_ids)
    if conflict:
        return (False, msg, sid)
    return (True, "", sid)