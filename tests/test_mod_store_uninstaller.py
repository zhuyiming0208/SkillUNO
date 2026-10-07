"""测试卸载。"""
import os
import sys
from unittest.mock import MagicMock

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)
SRC_DIR = os.path.join(PROJECT_ROOT, "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from uno.mod_store.uninstaller import uninstall_mod
from uno.mod_store.context import StoreContext
from uno.enabled import set_mod_enabled, is_mod_enabled


def _ctx(tmp_path):
    return StoreContext(
        mod_index=MagicMock(),
        history_path=str(tmp_path / "history.json"),
        enabled_path=str(tmp_path / "enabled.json"),
        collections_path=str(tmp_path / "collections.json"),
    )


def test_missing_mod_returns_ok(tmp_path):
    ctx = _ctx(tmp_path)
    ok, msg = uninstall_mod("NOPE", ctx)
    assert ok is True


def test_removes_installed(tmp_path):
    (tmp_path / "X.py").write_text("x", encoding="utf-8")
    ctx = _ctx(tmp_path)
    ok, msg = uninstall_mod("X", ctx)
    assert ok is True
    assert not (tmp_path / "X.py").exists()


def test_removes_pending(tmp_path):
    p = tmp_path / "_pending"
    p.mkdir()
    (p / "X.py").write_text("x", encoding="utf-8")
    ctx = _ctx(tmp_path)
    ok, msg = uninstall_mod("X", ctx)
    assert ok is True
    assert not (p / "X.py").exists()


def test_remove_failure(tmp_path):
    f = tmp_path / "X.py"
    f.write_text("x", encoding="utf-8")
    ctx = _ctx(tmp_path)
    import unittest.mock as m
    with m.patch("uno.mod_store.uninstaller.os.remove",
                 side_effect=OSError("perm")):
        ok, msg = uninstall_mod("X", ctx)
    assert ok is False


def test_removes_from_disabled(tmp_path):
    ctx = _ctx(tmp_path)
    set_mod_enabled("X", False, ctx.enabled_path)
    (tmp_path / "X.py").write_text("x", encoding="utf-8")
    ok, msg = uninstall_mod("X", ctx)
    assert ok is True
    assert is_mod_enabled("X", ctx.enabled_path) is True


def test_removes_both_locations(tmp_path):
    (tmp_path / "X.py").write_text("x", encoding="utf-8")
    p = tmp_path / "_pending"
    p.mkdir()
    (p / "X.py").write_text("y", encoding="utf-8")
    ctx = _ctx(tmp_path)
    ok, msg = uninstall_mod("X", ctx)
    assert ok is True
    assert not (tmp_path / "X.py").exists()
    assert not (p / "X.py").exists()
