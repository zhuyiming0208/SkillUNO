"""历史集成测试。"""
import os
import sys
from unittest.mock import patch, MagicMock

import pytest

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)
SRC_DIR = os.path.join(PROJECT_ROOT, "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from uno.mod_store import input_handler as ih
from uno.mod_store import history as hs
from uno.mod_store.router import Router, Action, MessagePage


def _mod():
    return {"ID": "X", "name": "N", "author": "a",
            "version": "1.0.0", "repo": "r",
            "skills": 1, "achievements": 0,
            "needs": [], "rely_on": {}, "reject": {}, "only_tolerate": []}


class TestHistoryIntegration:
    def test_download_records(self, tmp_path):
        hp = str(tmp_path / "h.json")
        r = Router(mod_index=MagicMock(), mods_dir=str(tmp_path),
                   pending_dir=str(tmp_path / "_pending"), history_path=hp)
        from uno.mod_store.confirm import ConfirmPage
        r.push(ConfirmPage(_mod(), history_path=hp))
        with patch("uno.mod_store.downloader.download_mod",
                   return_value=(True, "p")), \
             patch("uno.mod_store.validator.validate_download",
                   return_value=(True, "", "X")):
            r._dispatch("CONFIRM")
        records = hs.find_records("X", hp)
        assert any(rec["action"] == "downloaded" for rec in records)

    def test_enable_records(self, tmp_path):
        hp = str(tmp_path / "h.json")
        r = Router(mod_index=MagicMock(), mods_dir=str(tmp_path),
                   pending_dir=str(tmp_path / "_pending"), history_path=hp)
        from uno.mod_store.confirm import ConfirmPage
        from uno.mod_store.enable import EnablePage
        r.push(ConfirmPage(_mod(), history_path=hp))
        r.push(EnablePage("X", "p"))
        with patch("uno.mod_store.downloader.enable_mod",
                   return_value=(True, "mods/X.py")):
            r._dispatch("ENABLE")
        assert any(rec["action"] == "enabled"
                   for rec in hs.find_records("X", hp))

    def test_keep_pending_records(self, tmp_path):
        hp = str(tmp_path / "h.json")
        r = Router(mod_index=MagicMock(), mods_dir=str(tmp_path),
                   pending_dir=str(tmp_path / "_pending"), history_path=hp)
        from uno.mod_store.confirm import ConfirmPage
        from uno.mod_store.enable import EnablePage
        r.push(ConfirmPage(_mod(), history_path=hp))
        r.push(EnablePage("X", "p"))
        r._dispatch("KEEP_PENDING")
        assert any(rec["action"] == "kept_pending"
                   for rec in hs.find_records("X", hp))

    def test_h_home(self, tmp_path):
        hp = str(tmp_path / "h.json")
        r = Router(mod_index=MagicMock(), mods_dir=str(tmp_path),
                   pending_dir=str(tmp_path / "_pending"), history_path=hp)
        r._dispatch(Action.HISTORY)
        from uno.mod_store.history_view import HistoryPage
        assert isinstance(r.current(), HistoryPage)

    def test_history_back(self, tmp_path):
        hp = str(tmp_path / "h.json")
        r = Router(mod_index=MagicMock(), mods_dir=str(tmp_path),
                   pending_dir=str(tmp_path / "_pending"), history_path=hp)
        r._dispatch(Action.HISTORY)
        n = len(r.stack)
        r._dispatch(Action.BACK)
        assert len(r.stack) == n - 1

    def test_confirm_shows_history_hint(self, tmp_path):
        hp = str(tmp_path / "h.json")
        hs.add_record(_mod(), "downloaded", "pending", hp)
        from uno.mod_store.confirm import ConfirmPage
        page = ConfirmPage(_mod(), history_path=hp)
        assert "检测到历史记录" in page.render()

    def test_add_record_error_no_break(self, tmp_path):
        hp = str(tmp_path / "h.json")
        r = Router(mod_index=MagicMock(), mods_dir=str(tmp_path),
                   pending_dir=str(tmp_path / "_pending"), history_path=hp)
        from uno.mod_store.confirm import ConfirmPage
        from uno.mod_store.enable import EnablePage
        bad_mod = {"ID": "X", "name": "N", "author": "a", "repo": "r"}
        r.push(ConfirmPage(bad_mod, history_path=hp))
        r.push(EnablePage("X", "p"))
        with patch("uno.mod_store.downloader.enable_mod",
                   return_value=(True, "mods/X.py")):
            r._dispatch("ENABLE")
        assert isinstance(r.current(), MessagePage)
