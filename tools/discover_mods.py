"""每日自动发现 skilluno-mod topic 的 GitHub 仓库，重建 mods/mod_idx.json 的 other 列表。

决策：
- handpicked 完全不动
- other 每次完全重建
- 失效仓库自动移除（不删官方、不删 handpicked）
- 结果写入 mods/，由 CI 通过 PR 提交供人工审核

依赖：仅标准库（urllib.request），不依赖 requests。
"""
import os
import sys
import json
import time
import urllib.request
import urllib.error
import urllib.parse


GITHUB_API = "https://api.github.com"
RAW_BASE = "https://raw.githubusercontent.com"
TOPIC = "skilluno-mod"
USER_AGENT = "SkillUNO-Discover-Bot"
RESERVED_IDS = {"S1", "S2", "S3", "S4"}
REQUIRED_FIELDS = [
    "ID", "name", "description", "author", "author_github",
    "repo", "version", "micover", "lacover", "skills",
]


def _headers():
    h = {"User-Agent": USER_AGENT, "Accept": "application/vnd.github+json"}
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        h["Authorization"] = f"Bearer {token}"
    return h


def _http_get(url, headers, timeout):
    """发起 GET。返回 (status_code, body_bytes)。

    HTTP 错误码（404/403/429 等）不抛异常，返回对应 code + 空 body。
    网络层错误（DNS/超时/连接失败）抛 urllib.error.URLError。
    """
    req = urllib.request.Request(url, headers=headers)
    try:
        resp = urllib.request.urlopen(req, timeout=timeout)
        status = resp.getcode() or getattr(resp, "status", 200)
        body = resp.read()
        resp.close()
        return status, body
    except urllib.error.HTTPError as e:
        return e.code, b""


def search_repos():
    """搜索所有带 topic:skilluno-mod 的仓库。返回 [{owner, name, default_branch}]。"""
    repos = []
    page = 1
    while True:
        qs = urllib.parse.urlencode(
            {"q": f"topic:{TOPIC}", "per_page": 100, "page": page}
        )
        url = f"{GITHUB_API}/search/repositories?{qs}"
        try:
            status, body = _http_get(url, _headers(), 30)
        except urllib.error.URLError as e:
            print(f"警告：搜索请求失败：{e}")
            break

        if status in (403, 429):
            print(f"警告：GitHub API 速率限制 ({status})，停止搜索")
            break
        if status != 200:
            print(f"警告：搜索返回 HTTP {status}，停止搜索")
            break

        try:
            data = json.loads(body.decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            print("警告：搜索响应不是合法 JSON，停止搜索")
            break

        items = data.get("items", [])
        for it in items:
            repos.append({
                "owner": it["owner"]["login"],
                "name": it["name"],
                "default_branch": it.get("default_branch", "main"),
            })
        if len(items) < 100:
            break
        page += 1
    return repos


def fetch_metadata(owner, repo, branch):
    """从 raw.githubusercontent.com 拉 skilluno_mod.json。失败返回 None。"""
    url = f"{RAW_BASE}/{owner}/{repo}/{branch}/skilluno_mod.json"
    try:
        status, body = _http_get(url, {"User-Agent": USER_AGENT}, 15)
    except urllib.error.URLError:
        return None
    if status != 200:
        return None
    try:
        return json.loads(body.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        return None


def validate(meta, owner):
    """校验元数据。返回 (ok, reason)。"""
    if not isinstance(meta, dict):
        return (False, "skilluno_mod.json 缺失或无法解析")
    for f in REQUIRED_FIELDS:
        if f not in meta:
            return (False, f"缺少字段 {f}")
    mid = meta.get("ID", "")
    if mid in RESERVED_IDS:
        return (False, f"ID {mid} 为官方保留")
    author = str(meta.get("author_github", ""))
    if author.lower() != owner.lower():
        return (False, f"author_github ({author}) 与仓库 owner ({owner}) 不一致")
    return (True, "")


def _load_json(path, default):
    if not os.path.isfile(path):
        return default
    try:
        with open(path, "r", encoding="utf-8-sig") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return default


def _save_atomic(path, data):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


def _filename_to_id(mods_dir, filename):
    p = os.path.join(mods_dir, filename)
    data = _load_json(p, None)
    if isinstance(data, dict):
        return data.get("ID")
    return None


def main():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    mods_dir = os.path.join(root, "mods")
    idx_path = os.path.join(mods_dir, "mod_idx.json")

    old_index = _load_json(idx_path, {
        "version": "1.0.0", "handpicked": [], "other": [], "update_time": "",
    })
    handpicked = old_index.get("handpicked", [])
    old_other = old_index.get("other", [])

    # handpicked 里的 ID（用于去重）
    handpicked_ids = set()
    for fn in handpicked:
        mid = _filename_to_id(mods_dir, fn)
        if mid:
            handpicked_ids.add(mid)

    # old_other 里的 ID（用于计算新增/更新/移除）
    old_other_ids = set()
    for fn in old_other:
        mid = _filename_to_id(mods_dir, fn)
        if mid:
            old_other_ids.add(mid)

    # 搜索
    repos = search_repos()
    print(f"发现 {len(repos)} 个仓库")

    # 校验
    valid_mods = {}
    skipped = []
    for repo in repos:
        meta = fetch_metadata(repo["owner"], repo["name"], repo["default_branch"])
        ok, reason = validate(meta, repo["owner"])
        if not ok:
            skipped.append(f"{repo['owner']}/{repo['name']}: {reason}")
            continue
        mid = meta["ID"]
        if mid in valid_mods:
            skipped.append(f"{repo['owner']}/{repo['name']}: 重复 ID {mid}，保留第一个")
            continue
        if mid in handpicked_ids:
            print(f"[跳过] {mid} 已在 handpicked 中")
            continue
        valid_mods[mid] = meta

    # 写模组 JSON + 重建 other
    new_other = []
    for mid in sorted(valid_mods.keys()):
        fn = f"{mid}.json"
        new_other.append(fn)
        _save_atomic(os.path.join(mods_dir, fn), valid_mods[mid])

    # 移除失效仓库
    removed = []
    for mid in old_other_ids - set(valid_mods.keys()):
        if mid in RESERVED_IDS or mid in handpicked_ids:
            continue  # 防御：绝不误删
        p = os.path.join(mods_dir, f"{mid}.json")
        if os.path.isfile(p):
            os.remove(p)
        removed.append(mid)

    # 计算新增/更新
    discovered_ids = set(valid_mods.keys())
    added = sorted(discovered_ids - old_other_ids)
    updated = sorted(discovered_ids & old_other_ids)

    # 写 mod_idx.json（原子）
    new_index = {
        "version": old_index.get("version", "1.0.0"),
        "handpicked": handpicked,
        "other": new_other,
        "update_time": time.strftime("%Y-%m-%d", time.gmtime()),
    }
    _save_atomic(idx_path, new_index)

    # 摘要
    print()
    print("=" * 60)
    print(f"发现 {len(repos)} 个仓库")
    print(f"校验通过 {len(valid_mods)} 个")
    print(f"新增 {len(added)} 个：{', '.join(added) if added else '无'}")
    print(f"更新 {len(updated)} 个：{', '.join(updated) if updated else '无'}")
    print(f"移除 {len(removed)} 个：{', '.join(sorted(removed)) if removed else '无'}")
    print(f"跳过 {len(skipped)} 个：")
    for s in skipped:
        print(f"  - {s}")
    print("=" * 60)


if __name__ == "__main__":
    main()
