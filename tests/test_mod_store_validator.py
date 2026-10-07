"""测试 validator：静态语法检查、SEASON_ID 提取、ID 冲突。"""
import os
import sys
from unittest.mock import patch

import pytest

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)
SRC_DIR = os.path.join(PROJECT_ROOT, "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from uno.mod_store import validator as vd


class TestSyntax:
    def test_valid_file(self, tmp_path):
        f = tmp_path / "ok.py"
        f.write_text("SEASON_ID = 'X'\n", encoding="utf-8")
        ok, msg = vd.check_syntax(str(f))
        assert ok is True

    def test_syntax_error(self, tmp_path):
        f = tmp_path / "bad.py"
        f.write_text("def broken(:\n", encoding="utf-8")
        ok, msg = vd.check_syntax(str(f))
        assert ok is False
        assert "语法错误" in msg

    def test_missing_file(self, tmp_path):
        ok, msg = vd.check_syntax(str(tmp_path / "nope.py"))
        assert ok is False
        assert "读取失败" in msg


class TestExtractSeasonId:
    def test_extract_ok(self, tmp_path):
        f = tmp_path / "ok.py"
        f.write_text('SEASON_ID = "MOD_X"\n', encoding="utf-8")
        sid, msg = vd.extract_season_id(str(f))
        assert sid == "MOD_X"
        assert msg == ""

    def test_missing(self, tmp_path):
        f = tmp_path / "no.py"
        f.write_text("x = 1\n", encoding="utf-8")
        sid, msg = vd.extract_season_id(str(f))
        assert sid is None
        assert "缺少" in msg

    def test_non_string(self, tmp_path):
        f = tmp_path / "num.py"
        f.write_text("SEASON_ID = 123\n", encoding="utf-8")
        sid, msg = vd.extract_season_id(str(f))
        assert sid is None
        assert "不是字符串" in msg

    def test_too_large(self, tmp_path):
        f = tmp_path / "big.py"
        f.write_text("x = 1\n" * 100, encoding="utf-8")
        with patch("uno.mod_store.validator.os.path.getsize",
                   return_value=600 * 1024):
            sid, msg = vd.extract_season_id(str(f))
        assert sid is None
        assert "过大" in msg

    def test_syntax_error_returns_none(self, tmp_path):
        f = tmp_path / "bad.py"
        f.write_text("SEASON_ID = \n", encoding="utf-8")
        sid, msg = vd.extract_season_id(str(f))
        assert sid is None
        assert "语法错误" in msg

    def test_no_execution(self, tmp_path, capsys):
        """恶意代码不应被执行。"""
        f = tmp_path / "evil.py"
        f.write_text(
            'SEASON_ID = "EVIL"\nprint("EXECUTED")\n',
            encoding="utf-8"
        )
        sid, msg = vd.extract_season_id(str(f))
        captured = capsys.readouterr()
        assert "EXECUTED" not in captured.out
        assert sid == "EVIL"


class TestConflict:
    def test_official_conflict(self):
        conflict, msg = vd.check_id_conflict("S1")
        assert conflict is True
        assert "官方" in msg

    def test_official_s3_conflict(self):
        conflict, msg = vd.check_id_conflict("S3")
        assert conflict is True

    def test_mod_conflict(self, tmp_path):
        f = tmp_path / "mymod.py"
        f.write_text('SEASON_ID = "MYMOD"\n', encoding="utf-8")
        conflict, msg = vd.check_id_conflict("MYMOD", mods_dir=str(tmp_path))
        assert conflict is True
        assert "已安装" in msg

    def test_no_conflict(self, tmp_path):
        conflict, msg = vd.check_id_conflict("NEW", mods_dir=str(tmp_path))
        assert conflict is False

    def test_skip_dunder_init(self, tmp_path):
        (tmp_path / "__init__.py").write_text(
            'SEASON_ID = "NEW"\n', encoding="utf-8"
        )
        conflict, msg = vd.check_id_conflict("NEW", mods_dir=str(tmp_path))
        assert conflict is False


class TestValidateDownload:
    def test_ok(self, tmp_path):
        f = tmp_path / "ok.py"
        f.write_text('SEASON_ID = "OK"\n', encoding="utf-8")
        empty = tmp_path / "empty"
        empty.mkdir()
        ok, err, sid = vd.validate_download(str(f), mods_dir=str(empty))
        assert ok is True
        assert sid == "OK"

    def test_syntax_fail(self, tmp_path):
        f = tmp_path / "bad.py"
        f.write_text("def x(:\n", encoding="utf-8")
        ok, err, sid = vd.validate_download(str(f))
        assert ok is False
        assert sid is None

    def test_missing_season_id(self, tmp_path):
        f = tmp_path / "nosid.py"
        f.write_text("x = 1\n", encoding="utf-8")
        ok, err, sid = vd.validate_download(str(f))
        assert ok is False

    def test_conflict_fail(self, tmp_path):
        f = tmp_path / "x.py"
        f.write_text('SEASON_ID = "S1"\n', encoding="utf-8")
        ok, err, sid = vd.validate_download(str(f), mods_dir=str(tmp_path))
        assert ok is False
        assert "冲突" in err
        assert sid == "S1"