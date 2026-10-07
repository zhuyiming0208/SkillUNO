"""测试 history 模块。"""
import os
import re
import json
import sys
from unittest.mock import patch

import pytest

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)
SRC_DIR = os.path.join(PROJECT_ROOT, "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from uno.mod_store import history as hs


def _mod(id_="EXAMPLE"):
    return {
        "ID": id_, "name": "示例模组", "author": "alice",
        "version": "1.0.0", "repo": "https://github.com/alice/x",
    }


class TestLoadHistory:
    def test_missing_file(self, tmp_path):
        p = tmp_path / "history.json"
        assert hs.load_history(str(p)) == {"version": "1.0.0", "records": []}
        assert not p.exists()

    def test_reads_existing(self, tmp_path):
        p = tmp_path / "history.json"
        p.write_text(json.dumps({"version": "1.0.0",
                                 "records": [{"mod_id": "X"}]}),
                     encoding="utf-8")
        assert hs.load_history(str(p))["records"] == [{"mod_id": "X"}]

    def test_broken_json(self, tmp_path):
        p = tmp_path / "history.json"
        p.write_text("not-json", encoding="utf-8")
        assert hs.load_history(str(p))["records"] == []

    def test_empty_path(self):
        assert hs.load_history("") == {"version": "1.0.0", "records": []}

    def test_empty_file(self, tmp_path):
        p = tmp_path / "history.json"
        p.write_text("", encoding="utf-8")
        assert hs.load_history(str(p))["records"] == []

    def test_json_array(self, tmp_path):
        p = tmp_path / "history.json"
        p.write_text("[]", encoding="utf-8")
        assert hs.load_history(str(p))["records"] == []


class TestSaveHistory:
    def test_basic(self, tmp_path):
        p = tmp_path / "history.json"
        data = {"version": "1.0.0", "records": [{"a": 1}]}
        hs.save_history(data, str(p))
        assert json.loads(p.read_text(encoding="utf-8")) == data

    def test_creates_parent(self, tmp_path):
        p = tmp_path / "sub" / "deep" / "history.json"
        hs.save_history({"version": "1.0.0", "records": []}, str(p))
        assert p.exists()

    def test_cleans_stale_tmp(self, tmp_path):
        p = tmp_path / "history.json"
        tmp = str(p) + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            f.write("stale")
        hs.save_history({"version": "1.0.0", "records": []}, str(p))
        assert not os.path.exists(tmp)

    def test_atomic_failure(self, tmp_path):
        p = tmp_path / "history.json"
        original = {"version": "1.0.0", "records": [{"keep": True}]}
        hs.save_history(original, str(p))
        with patch("uno.mod_store.history.os.replace",
                   side_effect=OSError("disk full")):
            with pytest.raises(OSError):
                hs.save_history({"version": "1.0.0", "records": []}, str(p))
        assert json.loads(p.read_text(encoding="utf-8")) == original

    def test_empty_path(self):
        with pytest.raises(ValueError):
            hs.save_history({}, "")


class TestAddRecord:
    def test_appends(self, tmp_path):
        p = str(tmp_path / "h.json")
        hs.add_record(_mod(), "downloaded", "pending", p)
        data = hs.load_history(p)
        assert len(data["records"]) == 1
        r = data["records"][0]
        assert re.match(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}", r["time"])
        assert r["mod_id"] == "EXAMPLE"
        assert r["mod_name"] == "示例模组"
        assert r["action"] == "downloaded"
        assert r["status"] == "pending"

    def test_multiple(self, tmp_path):
        p = str(tmp_path / "h.json")
        hs.add_record(_mod(), "downloaded", "pending", p)
        hs.add_record(_mod(), "enabled", "enabled", p)
        assert len(hs.load_history(p)["records"]) == 2

    def test_missing_field(self, tmp_path):
        p = str(tmp_path / "h.json")
        bad = {"name": "X", "author": "a", "version": "1", "repo": "r"}
        with pytest.raises(ValueError) as exc:
            hs.add_record(bad, "downloaded", "pending", p)
        assert "缺少字段" in str(exc.value)

    def test_invalid_action(self, tmp_path):
        p = str(tmp_path / "h.json")
        with pytest.raises(ValueError):
            hs.add_record(_mod(), "hacked", "pending", p)

    def test_invalid_status(self, tmp_path):
        p = str(tmp_path / "h.json")
        with pytest.raises(ValueError):
            hs.add_record(_mod(), "downloaded", "hacked", p)

    def test_max_records(self, tmp_path):
        p = str(tmp_path / "h.json")
        for i in range(5):
            hs.add_record(_mod(id_=f"M{i}"), "downloaded", "pending", p,
                          max_records=3)
        data = hs.load_history(p)
        assert len(data["records"]) == 3
        assert data["records"][0]["mod_id"] == "M2"


class TestFindRecords:
    def test_newest_first(self, tmp_path):
        p = str(tmp_path / "h.json")
        hs.add_record(_mod(), "downloaded", "pending", p)
        hs.add_record(_mod(), "enabled", "enabled", p)
        records = hs.find_records("EXAMPLE", p)
        assert records[0]["action"] == "enabled"
        assert records[1]["action"] == "downloaded"

    def test_new_list(self, tmp_path):
        p = str(tmp_path / "h.json")
        hs.add_record(_mod(), "downloaded", "pending", p)
        r1 = hs.find_records("EXAMPLE", p)
        r1.clear()
        assert len(hs.find_records("EXAMPLE", p)) == 1

    def test_missing(self, tmp_path):
        p = str(tmp_path / "h.json")
        assert hs.find_records("NOPE", p) == []


class TestCheckDownloaded:
    def test_latest(self, tmp_path):
        p = str(tmp_path / "h.json")
        hs.add_record(_mod(), "downloaded", "pending", p)
        hs.add_record(_mod(), "enabled", "enabled", p)
        assert hs.check_downloaded("EXAMPLE", p)["action"] == "enabled"

    def test_missing(self, tmp_path):
        p = str(tmp_path / "h.json")
        assert hs.check_downloaded("NOPE", p) is None
