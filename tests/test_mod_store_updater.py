"""测试 updater。"""
import os
import sys
import json

import pytest

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)
SRC_DIR = os.path.join(PROJECT_ROOT, "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from uno.mod_store import updater as up


class TestParseVersion:
    def test_normal(self):
        assert up._parse_version("1.2.0") == ((1, 2, 0), False)

    def test_prerelease(self):
        assert up._parse_version("1.2.0-beta") == ((1, 2, 0), True)

    def test_invalid(self):
        assert up._parse_version("abc") == ((0, 0, 0), False)

    def test_short(self):
        assert up._parse_version("1.2") == ((1, 2, 0), False)

    def test_empty(self):
        assert up._parse_version("") == ((0, 0, 0), False)


class TestCompareVersions:
    def test_prerelease_less_than_stable(self):
        assert up._compare_versions("1.2.0-beta", "1.2.0") == -1

    def test_stable_greater_than_prerelease(self):
        assert up._compare_versions("1.2.0", "1.2.0-beta") == 1

    def test_minor_bump(self):
        assert up._compare_versions("1.2.0", "1.2.1") == -1

    def test_major_bump(self):
        assert up._compare_versions("1.3.0", "1.2.9") == 1

    def test_equal(self):
        assert up._compare_versions("1.2.0", "1.2.0") == 0

    def test_both_prerelease_equal(self):
        assert up._compare_versions("1.2.0-beta", "1.2.0-alpha") == 0


class _FakeIdx:
    def __init__(self, mods):
        self._mods = mods

    def get_by_id(self, mid):
        return self._mods.get(mid)


class TestCheckUpdates:
    def test_same_version_not_returned(self):
        idx = _FakeIdx({"X": {"ID": "X", "version": "1.0.0"}})
        result = up.check_updates([{"id": "X", "version": "1.0.0"}], idx)
        assert result == []

    def test_newer_returned(self):
        idx = _FakeIdx({"X": {"ID": "X", "version": "1.1.0"}})
        result = up.check_updates([{"id": "X", "version": "1.0.0"}], idx)
        assert len(result) == 1
        assert result[0]["id"] == "X"
        assert result[0]["latest_version"] == "1.1.0"

    def test_missing_in_index(self):
        idx = _FakeIdx({})
        result = up.check_updates([{"id": "X", "version": "1.0.0"}], idx)
        assert result == []

    def test_builtin_skipped(self):
        idx = _FakeIdx({"S1": {"ID": "S1", "version": "2.0.0"}})
        result = up.check_updates([{"id": "S1", "version": "1.0.0"}], idx)
        assert result == []

    def test_all_builtins_skipped(self):
        idx = _FakeIdx({
            "S1": {"ID": "S1", "version": "2.0.0"},
            "S2": {"ID": "S2", "version": "2.0.0"},
            "S3": {"ID": "S3", "version": "2.0.0"},
            "S4": {"ID": "S4", "version": "2.0.0"},
        })
        mods = [{"id": x, "version": "1.0.0"} for x in ("S1", "S2", "S3", "S4")]
        assert up.check_updates(mods, idx) == []


class TestListInstalled:
    def test_empty_dir(self, tmp_path):
        assert up.list_installed_mods(str(tmp_path)) == []

    def test_lists_py_files(self, tmp_path):
        (tmp_path / "A.py").write_text(
            'SEASON_ID = "A"\n__version__ = "1.2.3"\n', encoding="utf-8")
        (tmp_path / "B.py").write_text(
            'SEASON_ID = "B"\n', encoding="utf-8")
        result = up.list_installed_mods(str(tmp_path))
        ids = {m["id"] for m in result}
        assert ids == {"A", "B"}
        a = next(m for m in result if m["id"] == "A")
        assert a["version"] == "1.2.3"

    def test_skips_dunder(self, tmp_path):
        (tmp_path / "__init__.py").write_text('SEASON_ID = "X"\n', encoding="utf-8")
        assert up.list_installed_mods(str(tmp_path)) == []

    def test_skips_no_season_id(self, tmp_path):
        (tmp_path / "A.py").write_text("x = 1\n", encoding="utf-8")
        assert up.list_installed_mods(str(tmp_path)) == []
