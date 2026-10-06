"""模组索引与元数据加载测试。"""
import os
import sys
import json

import pytest

# 路径配置：tests/ 与 src/ 同级，位于项目根目录下
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)
SRC_DIR = os.path.join(PROJECT_ROOT, "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from uno.mod_index import ModIndex, OFFICIAL_MODS, REQUIRED_FIELDS


@pytest.fixture
def real_mods_dir():
    """项目根目录下的真实 mods 目录（包含 mod_idx.json 与 example.json）。"""
    return os.path.join(PROJECT_ROOT, "mods")


# ---------- 索引读取 ----------
class TestLoadIndex:
    def test_load_index_success(self, real_mods_dir):
        idx = ModIndex(mods_dir=real_mods_dir)
        data = idx.load_index()
        assert isinstance(data, dict)
        assert "handpicked" in data
        assert "other" in data
        assert "version" in data
        assert "update_time" in data

    def test_load_index_missing_file_returns_empty(self, tmp_path, capsys):
        idx = ModIndex(mods_dir=str(tmp_path))
        data = idx.load_index()
        assert data["handpicked"] == []
        assert data["other"] == []
        captured = capsys.readouterr()
        assert "警告" in captured.out

    def test_load_index_bad_json_returns_empty(self, tmp_path, capsys):
        (tmp_path / "mod_idx.json").write_text("not-json", encoding="utf-8")
        idx = ModIndex(mods_dir=str(tmp_path))
        data = idx.load_index()
        assert data["handpicked"] == []
        captured = capsys.readouterr()
        assert "警告" in captured.out


# ---------- 单个模组读取 ----------
class TestLoadMod:
    def test_load_example_success(self, real_mods_dir):
        idx = ModIndex(mods_dir=real_mods_dir)
        mod = idx.load_mod("example.json")
        assert mod is not None
        assert mod["ID"] == "EXAMPLE"
        assert mod["name"] == "示例模组"
        # 必填字段全部存在
        for field in REQUIRED_FIELDS:
            assert field in mod

    def test_load_example_has_author_github(self, real_mods_dir):
        """example.json 中 author_github 字段存在且非空。"""
        idx = ModIndex(mods_dir=real_mods_dir)
        mod = idx.load_mod("example.json")
        assert mod is not None
        assert "author_github" in mod
        assert mod["author_github"]  # 非空字符串

    def test_load_nonexistent_returns_none(self, real_mods_dir, capsys):
        idx = ModIndex(mods_dir=real_mods_dir)
        result = idx.load_mod("does_not_exist.json")
        assert result is None
        captured = capsys.readouterr()
        assert "警告" in captured.out

    def test_load_mod_missing_required_returns_none(self, tmp_path, capsys):
        bad = tmp_path / "bad.json"
        bad.write_text(json.dumps({"ID": "BAD"}), encoding="utf-8")
        idx = ModIndex(mods_dir=str(tmp_path))
        result = idx.load_mod("bad.json")
        assert result is None
        captured = capsys.readouterr()
        assert "缺少必填字段" in captured.out

    def test_load_mod_missing_author_github_returns_none(self, tmp_path, capsys):
        """缺失 author_github 的模组应被跳过，并打印含该字段名的警告。"""
        bad = tmp_path / "no_github.json"
        bad.write_text(json.dumps({
            "ID": "NOGH", "name": "n", "description": "d", "author": "a",
            # 故意缺 author_github
            "repo": "r", "version": "1.0.0", "micover": "1.0.0",
            "lacover": None, "skills": 1,
        }, ensure_ascii=False), encoding="utf-8")
        idx = ModIndex(mods_dir=str(tmp_path))
        result = idx.load_mod("no_github.json")
        assert result is None
        captured = capsys.readouterr()
        assert "author_github" in captured.out

    def test_load_mod_bad_json_returns_none(self, tmp_path, capsys):
        bad = tmp_path / "bad.json"
        bad.write_text("not-json", encoding="utf-8")
        idx = ModIndex(mods_dir=str(tmp_path))
        result = idx.load_mod("bad.json")
        assert result is None
        captured = capsys.readouterr()
        assert "格式错误" in captured.out

    def test_load_mod_all_required_fields_present(self, tmp_path):
        """构造一个合规的最小模组，确认加载成功。"""
        full = {
            "ID": "OK", "name": "OK", "description": "d", "author": "a",
            "author_github": "a_gh", "repo": "r", "version": "1.0.0",
            "micover": "1.0.0", "lacover": None, "skills": 1,
        }
        (tmp_path / "ok.json").write_text(
            json.dumps(full, ensure_ascii=False), encoding="utf-8"
        )
        idx = ModIndex(mods_dir=str(tmp_path))
        mod = idx.load_mod("ok.json")
        assert mod is not None
        assert mod["ID"] == "OK"


# ---------- 列表与搜索 ----------
class TestListAndSearch:
    def _write_index(self, tmp_path, handpicked, other):
        (tmp_path / "mod_idx.json").write_text(
            json.dumps({
                "handpicked": handpicked,
                "other": other,
                "version": "1.0.0",
                "update_time": "2026-10-06",
            }, ensure_ascii=False),
            encoding="utf-8",
        )

    def _write_mod(self, tmp_path, filename, mod_id, name, author):
        (tmp_path / filename).write_text(
            json.dumps({
                "ID": mod_id, "name": name, "description": "d",
                "author": author, "author_github": author,
                "repo": "r", "version": "1.0.0",
                "micover": "1.0.0", "lacover": None, "skills": 1,
            }, ensure_ascii=False),
            encoding="utf-8",
        )

    def _setup_example_mod(self, tmp_path):
        """在临时目录里构造一个可被搜索到的 EXAMPLE 模组。"""
        self._write_index(tmp_path, ["example.json"], [])
        self._write_mod(tmp_path, "example.json", "EXAMPLE", "示例模组", "example_author")

    # ---------- 列表 ----------
    def test_get_handpicked(self, tmp_path):
        self._write_index(tmp_path, ["a.json"], ["b.json"])
        self._write_mod(tmp_path, "a.json", "A", "甲", "author_a")
        self._write_mod(tmp_path, "b.json", "B", "乙", "author_b")
        idx = ModIndex(mods_dir=str(tmp_path))
        result = idx.get_handpicked()
        assert len(result) == 1
        assert result[0]["ID"] == "A"

    def test_get_all_merges(self, tmp_path):
        self._write_index(tmp_path, ["a.json"], ["b.json"])
        self._write_mod(tmp_path, "a.json", "A", "甲", "author_a")
        self._write_mod(tmp_path, "b.json", "B", "乙", "author_b")
        idx = ModIndex(mods_dir=str(tmp_path))
        result = idx.get_all()
        ids = {m["ID"] for m in result}
        assert ids == {"A", "B"}

    def test_get_all_skips_invalid(self, tmp_path):
        self._write_index(tmp_path, ["a.json", "missing.json"], [])
        self._write_mod(tmp_path, "a.json", "A", "甲", "author_a")
        idx = ModIndex(mods_dir=str(tmp_path))
        result = idx.get_all()
        assert len(result) == 1

    # ---------- 搜索（用临时数据，不依赖真实 mods/）----------
    def test_search_by_id_case_insensitive(self, tmp_path):
        self._setup_example_mod(tmp_path)
        idx = ModIndex(mods_dir=str(tmp_path))
        result = idx.search("EXAMPLE")
        assert any(m["ID"] == "EXAMPLE" for m in result)

    def test_search_by_id_lowercase(self, tmp_path):
        self._setup_example_mod(tmp_path)
        idx = ModIndex(mods_dir=str(tmp_path))
        result = idx.search("example")
        assert any(m["ID"] == "EXAMPLE" for m in result)

    def test_search_by_author(self, tmp_path):
        self._setup_example_mod(tmp_path)
        idx = ModIndex(mods_dir=str(tmp_path))
        result = idx.search("example_author")
        assert any(m["ID"] == "EXAMPLE" for m in result)

    def test_search_by_name(self, tmp_path):
        self._setup_example_mod(tmp_path)
        idx = ModIndex(mods_dir=str(tmp_path))
        result = idx.search("示例")
        assert any(m["ID"] == "EXAMPLE" for m in result)

    def test_search_no_match(self, tmp_path):
        self._setup_example_mod(tmp_path)
        idx = ModIndex(mods_dir=str(tmp_path))
        result = idx.search("不存在的关键词xyz")
        assert result == []

    def test_search_empty_keyword(self, tmp_path):
        self._setup_example_mod(tmp_path)
        idx = ModIndex(mods_dir=str(tmp_path))
        assert idx.search("") == []
        assert idx.search("   ") == []

    def test_search_returns_empty_when_index_empty(self, tmp_path):
        """索引空时搜索应返回空列表，不报错。"""
        self._write_index(tmp_path, [], [])
        idx = ModIndex(mods_dir=str(tmp_path))
        assert idx.search("任何") == []


# ---------- 官方模组 ----------
class TestOfficialMods:
    def test_get_official_returns_three(self, real_mods_dir):
        idx = ModIndex(mods_dir=real_mods_dir)
        mods = idx.get_official()
        assert len(mods) == 3

    def test_get_official_ids(self, real_mods_dir):
        idx = ModIndex(mods_dir=real_mods_dir)
        ids = {m["id"] for m in idx.get_official()}
        assert ids == {"S1", "S2", "S4"}

    def test_get_official_returns_copy(self, real_mods_dir):
        """修改返回值不应污染 OFFICIAL_MODS。"""
        idx = ModIndex(mods_dir=real_mods_dir)
        mods = idx.get_official()
        mods[0]["name"] = "被修改"
        assert OFFICIAL_MODS[0]["name"] != "被修改"