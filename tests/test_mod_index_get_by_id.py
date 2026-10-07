"""测试 ModIndex.get_by_id。"""
import os
import sys
import json

import pytest

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)
SRC_DIR = os.path.join(PROJECT_ROOT, "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from uno.mod_index import ModIndex


def _write_mod(tmp_path, filename, mod_id):
    (tmp_path / filename).write_text(json.dumps({
        "ID": mod_id, "name": "N", "description": "d",
        "author": "a", "author_github": "a", "repo": "r",
        "version": "1.0.0", "micover": "1.0.0",
        "lacover": None, "skills": 1,
    }, ensure_ascii=False), encoding="utf-8")


def _write_index(tmp_path, handpicked):
    (tmp_path / "mod_idx.json").write_text(json.dumps({
        "handpicked": handpicked, "other": [],
        "version": "1.0.0", "update_time": "",
    }), encoding="utf-8")


class TestGetById:
    def test_finds(self, tmp_path):
        _write_mod(tmp_path, "a.json", "A")
        _write_index(tmp_path, ["a.json"])
        idx = ModIndex(mods_dir=str(tmp_path))
        assert idx.get_by_id("A")["ID"] == "A"

    def test_not_found(self, tmp_path):
        _write_index(tmp_path, [])
        idx = ModIndex(mods_dir=str(tmp_path))
        assert idx.get_by_id("NOPE") is None

    def test_case_sensitive(self, tmp_path):
        _write_mod(tmp_path, "a.json", "ABC")
        _write_index(tmp_path, ["a.json"])
        idx = ModIndex(mods_dir=str(tmp_path))
        assert idx.get_by_id("abc") is None
