"""测试 mod_store.cli 子命令。"""
import os
import sys
import json
from unittest.mock import patch, MagicMock

import pytest

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)
SRC_DIR = os.path.join(PROJECT_ROOT, "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from uno.mod_store import cli as modcli


def _mod(**kw):
    base = {
        "ID": "EXAMPLE", "name": "示例模组", "author": "example_author",
        "author_github": "example_author",
        "repo": "https://github.com/example_author/example",
        "version": "1.0.0", "micover": "1.0.0", "lacover": None,
        "skills": 3, "achievements": 0, "description": "示例简介",
        "license": "MIT", "tags": ["示例"],
        "rely_on": {}, "reject": {}, "only_tolerate": [],
        "needs": ["core.Skill"],
    }
    base.update(kw)
    return base


def _write_mod_index(mods_dir):
    idx_path = os.path.join(mods_dir, "mod_idx.json")
    with open(idx_path, "w", encoding="utf-8") as f:
        json.dump({"handpicked": ["example.json"], "other": [],
                   "version": "1.0.0", "update_time": ""}, f,
                  ensure_ascii=False)


def _write_example(mods_dir):
    path = os.path.join(mods_dir, "example.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(_mod(), f, ensure_ascii=False)


class TestRunCliDispatch:
    def test_no_args_prints_help(self, tmp_path, capsys):
        rc = modcli.run_cli([], str(tmp_path))
        out = capsys.readouterr().out
        assert rc == 0
        assert "list" in out and "install" in out and "uninstall" in out

    def test_help_flag(self, tmp_path):
        assert modcli.run_cli(["--help"], str(tmp_path)) == 0

    def test_unknown_command(self, tmp_path, capsys):
        rc = modcli.run_cli(["foobar"], str(tmp_path))
        out = capsys.readouterr().out
        assert rc == 2
        assert "未知子命令" in out

    def test_search_missing_keyword(self, tmp_path):
        assert modcli.run_cli(["search"], str(tmp_path)) == 2

    def test_info_missing_id(self, tmp_path):
        assert modcli.run_cli(["info"], str(tmp_path)) == 2

    def test_install_missing_id(self, tmp_path):
        assert modcli.run_cli(["install"], str(tmp_path)) == 2

    def test_uninstall_missing_id(self, tmp_path):
        assert modcli.run_cli(["uninstall"], str(tmp_path)) == 2


class TestCmdList:
    def test_contains_official(self, tmp_path, capsys):
        _write_mod_index(str(tmp_path))
        rc = modcli.cmd_list(str(tmp_path),
                             os.path.join(str(tmp_path), "enabled.json"))
        out = capsys.readouterr().out
        assert rc == 0
        assert "S1" in out and "经典赛季" in out

    def test_contains_thirdparty(self, tmp_path, capsys):
        _write_mod_index(str(tmp_path))
        _write_example(str(tmp_path))
        modcli.cmd_list(str(tmp_path), os.path.join(str(tmp_path), "enabled.json"))
        assert "示例模组" in capsys.readouterr().out

    def test_empty_thirdparty(self, tmp_path, capsys):
        modcli.cmd_list(str(tmp_path), os.path.join(str(tmp_path), "enabled.json"))
        assert "（无）" in capsys.readouterr().out


class TestCmdSearch:
    def test_found(self, tmp_path, capsys):
        _write_mod_index(str(tmp_path))
        _write_example(str(tmp_path))
        rc = modcli.cmd_search("example", str(tmp_path),
                               os.path.join(str(tmp_path), "enabled.json"))
        assert rc == 0
        assert "示例模组" in capsys.readouterr().out

    def test_not_found(self, tmp_path, capsys):
        _write_mod_index(str(tmp_path))
        _write_example(str(tmp_path))
        rc = modcli.cmd_search("不存在xyz", str(tmp_path),
                               os.path.join(str(tmp_path), "enabled.json"))
        assert rc == 1
        assert "未找到" in capsys.readouterr().out


class TestCmdInfo:
    def test_official_s1(self, tmp_path, capsys):
        # 造官方数据：official.json + S1.json
        import json as _json
        (tmp_path / "official.json").write_text(
            _json.dumps({"version": "1.0.0", "mods": ["S1.json"]}),
            encoding="utf-8",
        )
        (tmp_path / "S1.json").write_text(
            _json.dumps(_mod(ID="S1", name="经典赛季", skills=16,
                             author="SkillUNO 官方"),
                        ensure_ascii=False),
            encoding="utf-8",
        )
        rc = modcli.cmd_info("S1", str(tmp_path),
                             os.path.join(str(tmp_path), "enabled.json"))
        out = capsys.readouterr().out
        assert rc == 0
        assert "经典赛季" in out
        assert "内置" in out

    def test_example(self, tmp_path, capsys):
        _write_mod_index(str(tmp_path))
        _write_example(str(tmp_path))
        rc = modcli.cmd_info("EXAMPLE", str(tmp_path),
                             os.path.join(str(tmp_path), "enabled.json"))
        out = capsys.readouterr().out
        assert rc == 0
        assert "示例模组" in out
        assert "example_author" in out
        assert "MIT" in out
        assert "任意版本" in out
        assert "core.Skill" in out
        assert "安装状态：未安装" in out

    def test_not_found(self, tmp_path, capsys):
        _write_mod_index(str(tmp_path))
        rc = modcli.cmd_info("NOTEXIST", str(tmp_path),
                             os.path.join(str(tmp_path), "enabled.json"))
        assert rc == 1
        assert "未找到模组" in capsys.readouterr().out


class TestCmdInstall:
    def test_builtin_rejected(self, tmp_path, capsys):
        rc = modcli.cmd_install("S1", str(tmp_path),
                                os.path.join(str(tmp_path), "_pending"),
                                os.path.join(str(tmp_path), "history.json"),
                                os.path.join(str(tmp_path), "enabled.json"))
        assert rc == 1
        assert "官方模组" in capsys.readouterr().out

    def test_not_found(self, tmp_path, capsys):
        _write_mod_index(str(tmp_path))
        rc = modcli.cmd_install("NOTEXIST", str(tmp_path),
                                os.path.join(str(tmp_path), "_pending"),
                                os.path.join(str(tmp_path), "history.json"),
                                os.path.join(str(tmp_path), "enabled.json"))
        assert rc == 1
        assert "未找到模组" in capsys.readouterr().out

    def test_success(self, tmp_path, capsys):
        _write_mod_index(str(tmp_path))
        _write_example(str(tmp_path))
        pending = os.path.join(str(tmp_path), "_pending")
        with patch("uno.mod_store.cli.download_mod",
                   return_value=(True, os.path.join(pending, "EXAMPLE.py"))), \
             patch("uno.mod_store.cli.validate_download",
                   return_value=(True, "", "EXAMPLE")), \
             patch("uno.mod_store.cli.enable_mod",
                   return_value=(True, "mods/EXAMPLE.py")):
            rc = modcli.cmd_install("EXAMPLE", str(tmp_path), pending,
                                    os.path.join(str(tmp_path), "history.json"),
                                    os.path.join(str(tmp_path), "enabled.json"))
        out = capsys.readouterr().out
        assert rc == 0
        assert "已安装并启用" in out

    def test_download_fail(self, tmp_path, capsys):
        _write_mod_index(str(tmp_path))
        _write_example(str(tmp_path))
        with patch("uno.mod_store.cli.download_mod",
                   return_value=(False, "网络连接失败")):
            rc = modcli.cmd_install("EXAMPLE", str(tmp_path),
                                    os.path.join(str(tmp_path), "_pending"),
                                    os.path.join(str(tmp_path), "history.json"),
                                    os.path.join(str(tmp_path), "enabled.json"))
        out = capsys.readouterr().out
        assert rc == 1
        assert "网络连接失败" in out


class TestCmdUninstall:
    def test_not_installed(self, tmp_path, capsys):
        rc = modcli.cmd_uninstall("NOTEXIST", str(tmp_path),
                                  os.path.join(str(tmp_path), "_pending"),
                                  os.path.join(str(tmp_path), "enabled.json"),
                                  os.path.join(str(tmp_path), "history.json"))
        assert rc == 1
        assert "未安装" in capsys.readouterr().out

    def test_builtin_rejected(self, tmp_path, capsys):
        rc = modcli.cmd_uninstall("S1", str(tmp_path),
                                  os.path.join(str(tmp_path), "_pending"),
                                  os.path.join(str(tmp_path), "enabled.json"),
                                  os.path.join(str(tmp_path), "history.json"))
        assert rc == 1
        assert "官方模组" in capsys.readouterr().out

    def test_success(self, tmp_path, capsys):
        (tmp_path / "EXAMPLE.py").write_text("SEASON_ID='EXAMPLE'\n",
                                             encoding="utf-8")
        _write_mod_index(str(tmp_path))
        _write_example(str(tmp_path))
        with patch("uno.mod_store.cli.uninstall_mod",
                   return_value=(True, "已卸载")):
            rc = modcli.cmd_uninstall("EXAMPLE", str(tmp_path),
                                      os.path.join(str(tmp_path), "_pending"),
                                      os.path.join(str(tmp_path), "enabled.json"),
                                      os.path.join(str(tmp_path), "history.json"))
        assert rc == 0
        assert "已卸载" in capsys.readouterr().out


class TestCmdListCollections:
    def test_none(self, tmp_path, capsys):
        rc = modcli.cmd_list_collections(str(tmp_path / "collections.json"))
        assert rc == 0
        assert "暂无模组集" in capsys.readouterr().out

    def test_lists(self, tmp_path, capsys):
        p = tmp_path / "collections.json"
        p.write_text(json.dumps({
            "version": "1.0.0",
            "collections": [
                {"id": "NEWBIE_PACK", "name": "新手包", "mods": ["S1", "EXAMPLE"]},
            ],
        }, ensure_ascii=False), encoding="utf-8")
        rc = modcli.cmd_list_collections(str(p))
        out = capsys.readouterr().out
        assert rc == 0
        assert "NEWBIE_PACK" in out and "新手包" in out


class TestCmdInstallCollection:
    def test_not_found(self, tmp_path, capsys):
        rc = modcli.cmd_install_collection(
            "NOTEXIST", str(tmp_path),
            os.path.join(str(tmp_path), "_pending"),
            os.path.join(str(tmp_path), "history.json"),
            os.path.join(str(tmp_path), "collections.json"))
        assert rc == 1
        assert "未找到模组集" in capsys.readouterr().out

    def test_success_skips_builtin(self, tmp_path, capsys):
        p = tmp_path / "collections.json"
        p.write_text(json.dumps({
            "version": "1.0.0",
            "collections": [
                {"id": "PACK", "name": "P", "mods": ["S1", "EXAMPLE"]},
            ],
        }, ensure_ascii=False), encoding="utf-8")
        _write_mod_index(str(tmp_path))
        _write_example(str(tmp_path))
        pending = os.path.join(str(tmp_path), "_pending")
        with patch("uno.mod_store.cli.download_mod",
                   return_value=(True, os.path.join(pending, "EXAMPLE.py"))), \
             patch("uno.mod_store.cli.validate_download",
                   return_value=(True, "", "EXAMPLE")), \
             patch("uno.mod_store.cli.enable_mod",
                   return_value=(True, "mods/EXAMPLE.py")):
            rc = modcli.cmd_install_collection(
                "PACK", str(tmp_path), pending,
                os.path.join(str(tmp_path), "history.json"), str(p))
        out = capsys.readouterr().out
        assert rc == 0
        assert "跳过 S1" in out
        assert "安装完成" in out


class TestCliEntry:
    def test_entry_dispatches_mod(self, monkeypatch):
        from uno import main as game_main
        called = {}

        def fake_run_cli(args, mods_dir):
            called['args'] = args
            return 0

        monkeypatch.setattr(sys, 'argv', ['skilluno', 'mod', 'list'])
        with patch("uno.mod_store.cli.run_cli", side_effect=fake_run_cli), \
             patch("uno.paths.find_mods_dir", return_value="/tmp/mods"):
            with pytest.raises(SystemExit) as exc:
                game_main.cli_entry()
        assert exc.value.code == 0
        assert called['args'] == ['list']

    def test_entry_falls_back_to_menu(self, monkeypatch):
        from uno import main as game_main
        called = {'menu': False}

        def fake_cli():
            called['menu'] = True

        monkeypatch.setattr(sys, 'argv', ['skilluno'])
        with patch.object(game_main, 'cli', side_effect=fake_cli):
            game_main.cli_entry()
        assert called['menu'] is True
