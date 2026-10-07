"""测试 enabled 模块。"""
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

from uno import enabled as en


def test_load_missing_returns_empty(tmp_path):
    p = tmp_path / "enabled.json"
    assert en.load_disabled(str(p)) == set()


def test_load_broken_json(tmp_path):
    p = tmp_path / "enabled.json"
    p.write_text("not-json", encoding="utf-8")
    assert en.load_disabled(str(p)) == set()


def test_save_atomic(tmp_path):
    p = tmp_path / "enabled.json"
    en.save_disabled({"A"}, str(p))
    data = json.loads(p.read_text(encoding="utf-8"))
    assert data["disabled"] == ["A"]


def test_is_enabled_default(tmp_path):
    p = tmp_path / "enabled.json"
    assert en.is_mod_enabled("X", str(p)) is True


def test_set_disabled(tmp_path):
    p = str(tmp_path / "enabled.json")
    en.set_mod_enabled("X", False, p)
    assert en.is_mod_enabled("X", p) is False


def test_set_enabled_removes(tmp_path):
    p = str(tmp_path / "enabled.json")
    en.set_mod_enabled("X", False, p)
    en.set_mod_enabled("X", True, p)
    assert en.is_mod_enabled("X", p) is True


def test_idempotent(tmp_path):
    p = str(tmp_path / "enabled.json")
    en.set_mod_enabled("X", False, p)
    en.set_mod_enabled("X", False, p)
    assert en.load_disabled(p) == {"X"}


def test_empty_path_load():
    assert en.load_disabled("") == set()
