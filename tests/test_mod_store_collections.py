"""测试 collections 模块。"""
import os
import sys
import json
from unittest.mock import patch

import pytest

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)
SRC_DIR = os.path.join(PROJECT_ROOT, "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from uno.mod_store import collections as col


class TestLoad:
    def test_missing_returns_empty(self, tmp_path):
        p = tmp_path / "c.json"
        assert col.load_collections(str(p)) == {"version": "1.0.0", "collections": []}
        assert not p.exists()

    def test_reads(self, tmp_path):
        p = tmp_path / "c.json"
        p.write_text(json.dumps({
            "version": "1.0.0",
            "collections": [{"id": "A", "name": "A"}],
        }), encoding="utf-8")
        assert col.load_collections(str(p))["collections"][0]["id"] == "A"

    def test_broken(self, tmp_path):
        p = tmp_path / "c.json"
        p.write_text("nope", encoding="utf-8")
        assert col.load_collections(str(p))["collections"] == []

    def test_empty_path(self):
        assert col.load_collections("")["collections"] == []


class TestSave:
    def test_roundtrip(self, tmp_path):
        p = tmp_path / "c.json"
        data = {"version": "1.0.0", "collections": [{"id": "X"}]}
        col.save_collections(data, str(p))
        assert json.loads(p.read_text(encoding="utf-8")) == data

    def test_creates_parent(self, tmp_path):
        p = tmp_path / "a" / "b" / "c.json"
        col.save_collections({"version": "1.0.0", "collections": []}, str(p))
        assert p.exists()

    def test_atomic_failure(self, tmp_path):
        p = tmp_path / "c.json"
        original = {"version": "1.0.0", "collections": [{"keep": True}]}
        col.save_collections(original, str(p))
        with patch("uno.mod_store.collections.os.replace",
                   side_effect=OSError("disk")):
            with pytest.raises(OSError):
                col.save_collections({"version": "1.0.0", "collections": []}, str(p))
        assert json.loads(p.read_text(encoding="utf-8")) == original

    def test_empty_path(self):
        with pytest.raises(ValueError):
            col.save_collections({}, "")


class TestGet:
    def test_finds(self, tmp_path):
        p = tmp_path / "c.json"
        col.save_collections({
            "version": "1.0.0",
            "collections": [{"id": "A"}, {"id": "B"}],
        }, str(p))
        assert col.get_collection("A", str(p))["id"] == "A"

    def test_missing(self, tmp_path):
        p = tmp_path / "c.json"
        col.save_collections({"version": "1.0.0", "collections": []}, str(p))
        assert col.get_collection("NOPE", str(p)) is None
