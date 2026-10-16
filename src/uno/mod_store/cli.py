"""SkillUNO CLI 子命令：skilluno mod <子命令>。"""
import os
import sys

from uno.mod_store.render import display_width
from uno.mod_store.downloader import (
    check_existing, download_mod, enable_mod,
)
from uno.mod_store.validator import validate_download
from uno.mod_store.history import add_record
from uno.mod_store.collections import load_collections, get_collection
from uno.mod_store.uninstaller import uninstall_mod
from uno.mod_store.context import StoreContext
from uno.enabled import is_mod_enabled


BUILTIN_IDS = {"S1", "S2", "S3", "S4"}


def print_help() -> int:
    print("""用法：skilluno mod <子命令> [参数]

子命令：
  list                      列出全部模组
  search <关键词>            模糊搜索模组
  info <ID>                 查看模组详情
  install <ID>              下载并安装模组
  uninstall <ID>            卸载模组
  list-collections          列出全部模组集
  install-collection <ID>   一键安装模组集

示例：
  skilluno mod list
  skilluno mod search example
  skilluno mod info S1
  skilluno mod install EXAMPLE
  skilluno mod uninstall EXAMPLE
  skilluno mod install-collection NEWBIE_PACK""")
    return 0


def _pad(s, width):
    s = "" if s is None else str(s)
    w = display_width(s)
    return s + " " * max(0, width - w)


def _load_index(mods_dir):
    from uno.mod_index import ModIndex
    return ModIndex(mods_dir=mods_dir)


def _format_official_row(mod_id, name, skills, enabled):
    status = "[已启用]" if enabled else "[已禁用]"
    return f"  {_pad(mod_id, 8)}{_pad(name, 16)}技能×{_pad(str(skills), 5)}{status}"


def _format_thirdparty_row(mod_id, name, author, version, skills, status):
    return (
        f"  {_pad(mod_id, 12)}{_pad(name, 16)}"
        f"by {_pad(author, 18)}v{_pad(version, 10)}"
        f"技能×{_pad(str(skills), 5)}{status}"
    )


def _thirdparty_status(mod_id, mods_dir, enabled_path):
    installed = os.path.isfile(os.path.join(mods_dir, f"{mod_id}.py"))
    if not installed:
        return "[未安装]"
    if is_mod_enabled(mod_id, enabled_path):
        return "[已启用]"
    return "[已禁用]"


def cmd_list(mods_dir, enabled_path):
    mod_index = _load_index(mods_dir)
    official = mod_index.get_official()
    official_ids = {m.get("id") or m.get("ID") for m in official}

    print("官方模组：")
    for mod in official:
        mod_id = mod.get("id") or mod.get("ID")
        name = mod.get("name", "?")
        skills = mod.get("skills", 0)
        enabled = is_mod_enabled(mod_id, enabled_path)
        print(_format_official_row(mod_id, name, skills, enabled))
    print()

    print("第三方模组：")
    all_mods = mod_index.get_all()
    third_party = [
        m for m in all_mods
        if (m.get("ID") or m.get("id")) not in official_ids
    ]
    if not third_party:
        print("  （无）")
    else:
        for mod in third_party:
            mod_id = mod.get("ID") or mod.get("id")
            print(_format_thirdparty_row(
                mod_id, mod.get("name", "?"), mod.get("author", "?"),
                mod.get("version", "?"), mod.get("skills", 0),
                _thirdparty_status(mod_id, mods_dir, enabled_path)))
    return 0


def cmd_search(keyword, mods_dir, enabled_path):
    mod_index = _load_index(mods_dir)
    results = mod_index.search(keyword)
    if not results:
        print(f"未找到匹配的模组：{keyword}")
        return 1
    official_ids = {m.get("id") or m.get("ID") for m in mod_index.get_official()}
    print(f"搜索 \"{keyword}\" 结果：")
    for mod in results:
        mod_id = mod.get("ID") or mod.get("id")
        if mod_id in official_ids:
            print(_format_official_row(
                mod_id, mod.get("name", "?"), mod.get("skills", 0),
                is_mod_enabled(mod_id, enabled_path)))
        else:
            print(_format_thirdparty_row(
                mod_id, mod.get("name", "?"), mod.get("author", "?"),
                mod.get("version", "?"), mod.get("skills", 0),
                _thirdparty_status(mod_id, mods_dir, enabled_path)))
    return 0


def cmd_info(mod_id, mods_dir, enabled_path):
    mod = _load_index(mods_dir).get_by_id(mod_id)
    if mod is None:
        print(f"未找到模组：{mod_id}")
        return 1

    micover = mod.get("micover", "?")
    lacover = mod.get("lacover")
    compat = (f"v{micover} ~ v{lacover}" if lacover
              else f"v{micover} ~ 任意版本")
    tags = mod.get("tags") or []

    print(f"ID:          {mod_id}")
    print(f"名称:        {mod.get('name', '?')}")
    print(f"作者:        {mod.get('author', '?')}")
    print(f"仓库:        {mod.get('repo', '?')}")
    print(f"版本:        v{mod.get('version', '?')}")
    print(f"许可证:      {mod.get('license') or '未声明'}")
    print(f"兼容版本:    {compat}")
    print(f"技能数:      {mod.get('skills', 0)}")
    print(f"成就数:      {mod.get('achievements', 0)}")
    print(f"标签:        {', '.join(tags) if tags else '无'}")
    print()
    print("简介：")
    desc = mod.get("description", "")
    print(f"  {desc}" if desc else "  （无）")
    print()
    print("依赖:")
    _print_relations(mod.get("rely_on"))
    print("排斥:")
    _print_relations(mod.get("reject"))
    print("白名单:")
    _print_list(mod.get("only_tolerate"))
    print("权限声明:")
    _print_list(mod.get("needs"), empty="未声明")
    print()
    installed = os.path.isfile(os.path.join(mods_dir, f"{mod_id}.py"))
    if mod_id in BUILTIN_IDS:
        print("安装状态：内置")
    elif not installed:
        print("安装状态：未安装")
        print(f"安装命令：skilluno mod install {mod_id}")
    elif is_mod_enabled(mod_id, enabled_path):
        print("安装状态：已启用")
    else:
        print("安装状态：已禁用")
    return 0


def _print_relations(obj):
    if not obj or not isinstance(obj, dict):
        print("  无")
        return
    for k, v in obj.items():
        print(f"  {k}：{v}")


def _print_list(lst, empty="无"):
    if not lst or not isinstance(lst, list):
        print(f"  {empty}")
        return
    for x in lst:
        print(f"  {x}")


def _install_one(mod_id, mods_dir, pending_dir, history_path, mod_index):
    if mod_id in BUILTIN_IDS:
        return (False, "官方模组无需安装")
    mod_data = mod_index.get_by_id(mod_id)
    if mod_data is None:
        return (False, f"未找到模组：{mod_id}")
    name = mod_data.get("name", mod_id)

    existing = check_existing(mod_id, mods_dir=mods_dir, pending_dir=pending_dir)
    if existing and existing.get("location") == "installed":
        print(f"注意：{mod_id} 已安装，将覆盖")

    ok, msg = download_mod(mod_data, pending_dir=pending_dir, mods_dir=mods_dir)
    if not ok:
        return (False, f"下载失败：{msg}")

    ok, err, sid = validate_download(msg, mods_dir=mods_dir)
    if not ok:
        try:
            if os.path.isfile(msg):
                os.remove(msg)
        except OSError:
            pass
        return (False, f"验证失败：{err}")

    ok, emsg = enable_mod(sid, mods_dir=mods_dir, pending_dir=pending_dir)
    if not ok:
        return (False, f"启用失败：{emsg}")

    for action, status in (("downloaded", "pending"), ("enabled", "enabled")):
        try:
            add_record(mod_data, action, status, history_path)
        except ValueError as e:
            print(f"警告：无法记录历史 — {e}")
    return (True, name)


def cmd_install(mod_id, mods_dir, pending_dir, history_path, enabled_path):
    if mod_id in BUILTIN_IDS:
        print(f"官方模组无需安装：{mod_id}")
        return 1
    mod_index = _load_index(mods_dir)
    mod_data = mod_index.get_by_id(mod_id)
    if mod_data is None:
        print(f"未找到模组：{mod_id}")
        return 1
    print(f"正在下载 {mod_data.get('name', mod_id)} ...")
    ok, result = _install_one(mod_id, mods_dir, pending_dir, history_path, mod_index)
    if ok:
        print(f"已安装并启用 {result}（重启游戏生效）")
        return 0
    print(result)
    return 1


def cmd_uninstall(mod_id, mods_dir, pending_dir, enabled_path, history_path):
    if mod_id in BUILTIN_IDS:
        print(f"官方模组无法卸载：{mod_id}")
        return 1
    existing = check_existing(mod_id, mods_dir=mods_dir, pending_dir=pending_dir)
    if existing is None:
        print(f"未安装：{mod_id}")
        return 1
    mod_index = _load_index(mods_dir)
    ctx = StoreContext(
        mod_index=mod_index,
        history_path=history_path,
        enabled_path=enabled_path,
        collections_path=os.path.join(mods_dir, "collections.json"),
    )
    ok, msg = uninstall_mod(mod_id, ctx)
    if not ok:
        print(f"卸载失败：{msg}")
        return 1
    mod_data = mod_index.get_by_id(mod_id)
    if mod_data is not None:
        try:
            add_record(mod_data, "uninstalled", "uninstalled", history_path)
        except ValueError as e:
            print(f"警告：无法记录历史 — {e}")
    print(f"已卸载 {mod_id}")
    return 0


def cmd_list_collections(collections_path):
    data = load_collections(collections_path)
    collections = data.get("collections", [])
    if not collections:
        print("暂无模组集")
        return 0
    print("模组集：")
    for c in collections:
        cid = c.get("id", "?")
        name = c.get("name", "?")
        count = len(c.get("mods", []))
        print(f"  {_pad(cid, 16)}{_pad(name, 18)}{count} 个模组")
    return 0


def cmd_install_collection(coll_id, mods_dir, pending_dir, history_path, collections_path):
    coll = get_collection(coll_id, collections_path)
    if coll is None:
        print(f"未找到模组集：{coll_id}")
        return 1
    mods = coll.get("mods", [])
    N = len(mods)
    mod_index = _load_index(mods_dir)
    success, failed = [], []
    for i, mid in enumerate(mods, 1):
        if mid in BUILTIN_IDS:
            print(f"[{i}/{N}] 跳过 {mid}（官方模组）")
            continue
        print(f"[{i}/{N}] 正在安装 {mid} ...")
        ok, result = _install_one(mid, mods_dir, pending_dir, history_path, mod_index)
        if ok:
            print(f"  ✓ {result}")
            success.append(result)
        else:
            print(f"  ✗ {mid}：{result}")
            failed.append((mid, result))
    print()
    print(f"安装完成：成功 {len(success)} 个，失败 {len(failed)} 个")
    return 1 if failed else 0


def run_cli(args, mods_dir):
    mods_dir = str(mods_dir)
    pending_dir = os.path.join(mods_dir, "_pending")
    history_path = os.path.join(mods_dir, "history.json")
    enabled_path = os.path.join(mods_dir, "enabled.json")
    collections_path = os.path.join(mods_dir, "collections.json")

    if not args or args[0] in ("-h", "--help"):
        return print_help()

    cmd = args[0]
    rest = args[1:]
    try:
        if cmd == "list":
            return cmd_list(mods_dir, enabled_path)
        if cmd == "search":
            if not rest:
                print("用法：skilluno mod search <关键词>")
                return 2
            return cmd_search(rest[0], mods_dir, enabled_path)
        if cmd == "info":
            if not rest:
                print("用法：skilluno mod info <ID>")
                return 2
            return cmd_info(rest[0], mods_dir, enabled_path)
        if cmd == "install":
            if not rest:
                print("用法：skilluno mod install <ID>")
                return 2
            return cmd_install(rest[0], mods_dir, pending_dir, history_path, enabled_path)
        if cmd == "uninstall":
            if not rest:
                print("用法：skilluno mod uninstall <ID>")
                return 2
            return cmd_uninstall(rest[0], mods_dir, pending_dir, enabled_path, history_path)
        if cmd == "list-collections":
            return cmd_list_collections(collections_path)
        if cmd == "install-collection":
            if not rest:
                print("用法：skilluno mod install-collection <ID>")
                return 2
            return cmd_install_collection(rest[0], mods_dir, pending_dir,
                                          history_path, collections_path)
    except KeyboardInterrupt:
        print("\n已取消")
        return 130

    print(f"未知子命令：{cmd}")
    print("运行 `skilluno mod --help` 查看用法。")
    return 2
