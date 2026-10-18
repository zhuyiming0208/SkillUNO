"""测试 tools/discover_mods.py。全部 mock，不联网。"""
import os
import sys
import json
from unittest.mock import patch, MagicMock

import pytest

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)
sys.path.insert(0, os.path.join(PROJECT_ROOT, "tools"))

import discover_mods as dm


def _make_response(status=200, json_data=None, text=None):
    m = MagicMock()
    m.status_code = status
    if json_data is not None:
        m.json.return_value = json_data
    else:
        m.json.side_effect = ValueError("not json")
    return m


def _mock_repo(owner, name, branch="main"):
    return {"owner": {"login": owner}, "name": name, "default_branch": branch}


def _mock_search(owners, per_page=100):
    """构造 search_repositories 的响应。owners 是 [(owner, repo_name)]"""
    items = [_mock_repo(o, r) for o, r in owners]
    return _make_response(200, {"items": items})


def _full_meta(mid, owner="author"):
    return {
        "ID": mid, "name": f"模组{mid}", "description": "d",
        "author": owner, "author_github": owner, "repo": f"https://github.com/{owner}/{mid}",
        "version": "1.0.0", "micover": "1.0.0", "lacover": None,
        "skills": 1,
    }


def _setup_mods_dir(tmp_path, monkeypatch):
    """把 mods_dir 固定到 tmp_path，并造一个干净的 mod_idx.json。"""
    monkeypatch.setattr(dm, "os", dm.os)  # no-op

    fake_root = tmp_path
    (fake_root / "mods").mkdir(exist_ok=True)

    # 造 official.json 和 handpicked 元数据
    (fake_root / "mods" / "official.json").write_text(
        json.dumps({"version": "1.0.0", "mods": ["S1.json"]}), encoding="utf-8")
    (fake_root / "mods" / "S1.json").write_text(
        json.dumps(_full_meta("S1"), ensure_ascii=False), encoding="utf-8")
    (fake_root / "mods" / "example.json").write_text(
        json.dumps(_full_meta("EXAMPLE"), ensure_ascii=False), encoding="utf-8")
    (fake_root / "mods" / "mod_idx.json").write_text(json.dumps({
        "version": "1.0.0",
        "handpicked": ["example.json"],
        "other": [],
        "update_time": "",
    }), encoding="utf-8")

    # patch 根目录
    fake_script = fake_root / "tools" / "discover_mods.py"
    fake_script.parent.mkdir(exist_ok=True)
    fake_script.touch()

    def fake_abspath(_p):
        return str(fake_script)
    monkeypatch.setattr(dm.os.path, "abspath", fake_abspath)
    return fake_root


def _run_with_repos(tmp_path, monkeypatch, repos, meta_map, old_other=None):
    """在 tmp_path 环境里跑 main()。
    repos: [(owner, repo_name)]
    meta_map: {(owner, repo_name): meta_dict or None}
    """
    root = _setup_mods_dir(tmp_path, monkeypatch)

    if old_other is not None:
        idx_path = root / "mods" / "mod_idx.json"
        data = json.loads(idx_path.read_text(encoding="utf-8"))
        data["other"] = old_other
        idx_path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

    search_resp = _mock_search(repos)

    def fake_get(url, **kwargs):
        if "search/repositories" in url:
            return search_resp
        # raw
        for (o, r), meta in meta_map.items():
            if f"/{o}/{r}/" in url:
                if meta is None:
                    return _make_response(404)
                return _make_response(200, meta)
        return _make_response(404)

    with patch.object(dm.requests, "get", side_effect=fake_get):
        dm.main()

    return root


class TestDiscovery:
    def test_no_repos(self, tmp_path, monkeypatch, capsys):
        root = _run_with_repos(tmp_path, monkeypatch, [], {})
        idx = json.loads((root / "mods" / "mod_idx.json").read_text(encoding="utf-8"))
        assert idx["other"] == []

    def test_one_valid_repo(self, tmp_path, monkeypatch):
        repos = [("alice", "mod-a")]
        meta_map = {("alice", "mod-a"): _full_meta("MODA", "alice")}
        root = _run_with_repos(tmp_path, monkeypatch, repos, meta_map)

        idx = json.loads((root / "mods" / "mod_idx.json").read_text(encoding="utf-8"))
        assert "MODA.json" in idx["other"]
        assert (root / "mods" / "MODA.json").exists()

    def test_missing_metadata(self, tmp_path, monkeypatch):
        repos = [("bob", "no-meta")]
        meta_map = {("bob", "no-meta"): None}
        root = _run_with_repos(tmp_path, monkeypatch, repos, meta_map)
        idx = json.loads((root / "mods" / "mod_idx.json").read_text(encoding="utf-8"))
        assert idx["other"] == []

    def test_missing_field(self, tmp_path, monkeypatch):
        repos = [("c", "r")]
        bad = _full_meta("BAD", "c")
        del bad["skills"]
        meta_map = {("c", "r"): bad}
        root = _run_with_repos(tmp_path, monkeypatch, repos, meta_map)
        idx = json.loads((root / "mods" / "mod_idx.json").read_text(encoding="utf-8"))
        assert idx["other"] == []

    def test_official_id_rejected(self, tmp_path, monkeypatch):
        repos = [("d", "fake-s1")]
        meta_map = {("d", "fake-s1"): _full_meta("S1", "d")}
        root = _run_with_repos(tmp_path, monkeypatch, repos, meta_map)
        idx = json.loads((root / "mods" / "mod_idx.json").read_text(encoding="utf-8"))
        assert idx["other"] == []

    def test_author_mismatch(self, tmp_path, monkeypatch):
        repos = [("real_owner", "mod")]
        meta = _full_meta("STOLEN", "fake_author")
        meta_map = {("real_owner", "mod"): meta}
        root = _run_with_repos(tmp_path, monkeypatch, repos, meta_map)
        idx = json.loads((root / "mods" / "mod_idx.json").read_text(encoding="utf-8"))
        assert idx["other"] == []

    def test_author_case_insensitive(self, tmp_path, monkeypatch):
        repos = [("Alice", "mod")]
        meta = _full_meta("M", "alice")  # 小写
        meta_map = {("Alice", "mod"): meta}
        root = _run_with_repos(tmp_path, monkeypatch, repos, meta_map)
        idx = json.loads((root / "mods" / "mod_idx.json").read_text(encoding="utf-8"))
        assert "M.json" in idx["other"]

    def test_handpicked_not_in_other(self, tmp_path, monkeypatch):
        repos = [("e", "example")]
        meta_map = {("e", "example"): _full_meta("EXAMPLE", "e")}
        root = _run_with_repos(tmp_path, monkeypatch, repos, meta_map)
        idx = json.loads((root / "mods" / "mod_idx.json").read_text(encoding="utf-8"))
        assert "EXAMPLE.json" not in idx["other"]

    def test_removed_when_gone(self, tmp_path, monkeypatch):
        # old_other 有 OLD，但本次没发现
        (tmp_path / "mods").mkdir(exist_ok=True)
        # 先造文件
        root = _setup_mods_dir(tmp_path, monkeypatch)
        (root / "mods" / "OLD.json").write_text(
            json.dumps(_full_meta("OLD"), ensure_ascii=False), encoding="utf-8")
        idx_path = root / "mods" / "mod_idx.json"
        data = json.loads(idx_path.read_text(encoding="utf-8"))
        data["other"] = ["OLD.json"]
        idx_path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

        with patch.object(dm.requests, "get", side_effect=lambda *a, **k: _mock_search([])):
            dm.main()

        idx = json.loads((root / "mods" / "mod_idx.json").read_text(encoding="utf-8"))
        assert idx["other"] == []
        assert not (root / "mods" / "OLD.json").exists()

    def test_duplicate_id_keeps_first(self, tmp_path, monkeypatch):
        repos = [("x", "first"), ("y", "second")]
        meta_map = {
            ("x", "first"): _full_meta("DUP", "x"),
            ("y", "second"): _full_meta("DUP", "y"),
        }
        root = _run_with_repos(tmp_path, monkeypatch, repos, meta_map)
        idx = json.loads((root / "mods" / "mod_idx.json").read_text(encoding="utf-8"))
        assert "DUP.json" in idx["other"]

    def test_pagination(self, tmp_path, monkeypatch):
        # 150 个仓库 → 2 次请求
        owners = [(f"o{i}", f"r{i}") for i in range(150)]
        pages = [owners[:100], owners[100:]]

        call_count = {"n": 0}

        def fake_get(url, **kwargs):
            if "search/repositories" in url:
                call_count["n"] += 1
                page = kwargs.get("params", {}).get("page", 1)
                batch = pages[page - 1] if page - 1 < len(pages) else []
                return _mock_search(batch)
            return _make_response(404)

        _setup_mods_dir(tmp_path, monkeypatch)
        with patch.object(dm.requests, "get", side_effect=fake_get):
            dm.main()

        assert call_count["n"] == 2

    def test_summary_contains_removed(self, tmp_path, monkeypatch, capsys):
        root = _setup_mods_dir(tmp_path, monkeypatch)
        (root / "mods" / "OLD.json").write_text(
            json.dumps(_full_meta("OLD"), ensure_ascii=False), encoding="utf-8")
        idx_path = root / "mods" / "mod_idx.json"
        data = json.loads(idx_path.read_text(encoding="utf-8"))
        data["other"] = ["OLD.json"]
        idx_path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

        with patch.object(dm.requests, "get", side_effect=lambda *a, **k: _mock_search([])):
            dm.main()

        out = capsys.readouterr().out
        assert "移除" in out
        assert "OLD" in out
