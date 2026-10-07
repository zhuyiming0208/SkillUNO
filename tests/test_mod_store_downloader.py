"""测试 downloader：URL 构造、下载、检查已存在、启用。"""
import os
import sys
import io
import urllib.error
from unittest.mock import patch, MagicMock

import pytest

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)
SRC_DIR = os.path.join(PROJECT_ROOT, "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from uno.mod_store import downloader as dl


# ==================== build_download_urls ====================
class TestBuildUrls:
    def test_basic_4_urls(self):
        mod = {"ID": "X", "author_github": "u", "repo": "https://github.com/u/r"}
        urls = dl.build_download_urls(mod)
        assert len(urls) == 4
        assert "raw.githubusercontent.com/u/r/main/X.py" in urls[0]
        assert "raw.githubusercontent.com/u/r/master/X.py" in urls[1]
        assert "cdn.jsdelivr.net/gh/u/r@main/X.py" in urls[2]
        assert "cdn.jsdelivr.net/gh/u/r@master/X.py" in urls[3]

    def test_py_file_and_branch_override(self):
        mod = {"ID": "X", "author_github": "u",
               "repo": "https://github.com/u/r",
               "py_file": "custom.py", "branch": "dev"}
        urls = dl.build_download_urls(mod)
        assert len(urls) == 2
        assert "raw.githubusercontent.com/u/r/dev/custom.py" in urls[0]
        assert "cdn.jsdelivr.net/gh/u/r@dev/custom.py" in urls[1]

    def test_chinese_filename(self):
        mod = {"ID": "X", "author_github": "u",
               "repo": "https://github.com/u/r",
               "py_file": "中文.py"}
        urls = dl.build_download_urls(mod)
        assert "%E4%B8%AD%E6%96%87.py" in urls[0]

    def test_missing_fields(self):
        assert dl.build_download_urls({}) == []

    def test_repo_with_git_suffix(self):
        mod = {"ID": "X", "author_github": "u",
               "repo": "https://github.com/u/r.git"}
        urls = dl.build_download_urls(mod)
        assert "u/r/main" in urls[0]
        # 精确判 r.git 子串，避免误伤 githubusercontent 里的 "git"
        assert "r.git" not in urls[0]

    def test_repo_with_trailing_slash(self):
        mod = {"ID": "X", "author_github": "u",
               "repo": "https://github.com/u/r/"}
        urls = dl.build_download_urls(mod)
        assert "u/r/main" in urls[0]


# ==================== 假响应 ====================
class _FakeResp:
    def __init__(self, data, headers=None):
        self._buf = io.BytesIO(data)
        self.headers = headers or {}

    def read(self, n=-1):
        return self._buf.read(n)

    def __enter__(self):
        return self

    def __exit__(self, *a):
        pass


# ==================== download_mod ====================
class TestDownload:
    def test_whitelist_reject(self, tmp_path):
        mod = {"ID": "X", "author_github": "u",
               "repo": "https://evil.com/u/r"}
        ok, msg = dl.download_mod(mod, pending_dir=str(tmp_path))
        assert ok is False
        assert "不允许" in msg

    def test_network_error(self, tmp_path):
        mod = {"ID": "X", "author_github": "u",
               "repo": "https://github.com/u/r"}
        with patch("uno.mod_store.downloader.urlopen",
                   side_effect=urllib.error.URLError("boom")):
            ok, msg = dl.download_mod(mod, pending_dir=str(tmp_path))
        assert ok is False
        assert "网络" in msg

    def test_timeout_error(self, tmp_path):
        mod = {"ID": "X", "author_github": "u",
               "repo": "https://github.com/u/r"}
        with patch("uno.mod_store.downloader.urlopen",
                   side_effect=urllib.error.URLError("timed out")):
            ok, msg = dl.download_mod(mod, pending_dir=str(tmp_path))
        assert ok is False
        assert "超时" in msg

    def test_404_fallback_success(self, tmp_path):
        """前几个 URL 404，第四个成功。"""
        mod = {"ID": "X", "author_github": "u",
               "repo": "https://github.com/u/r"}
        calls = [0]

        def fake_open(req, timeout=None):
            calls[0] += 1
            if calls[0] < 4:
                raise urllib.error.HTTPError(
                    req.full_url, 404, "nf", {}, None
                )
            return _FakeResp(b'SEASON_ID = "X"\n')

        with patch("uno.mod_store.downloader.urlopen", side_effect=fake_open):
            ok, msg = dl.download_mod(mod, pending_dir=str(tmp_path))
        assert ok is True
        assert os.path.isfile(msg)

    def test_all_404(self, tmp_path):
        mod = {"ID": "X", "author_github": "u",
               "repo": "https://github.com/u/r"}
        with patch("uno.mod_store.downloader.urlopen",
                   side_effect=urllib.error.HTTPError(
                       "u", 404, "nf", {}, None
                   )):
            ok, msg = dl.download_mod(mod, pending_dir=str(tmp_path))
        assert ok is False
        assert "不存在" in msg

    def test_content_length_too_large(self, tmp_path):
        mod = {"ID": "X", "author_github": "u",
               "repo": "https://github.com/u/r"}
        resp = _FakeResp(b"", headers={"Content-Length": str(6 * 1024 * 1024)})
        with patch("uno.mod_store.downloader.urlopen", return_value=resp):
            ok, msg = dl.download_mod(mod, pending_dir=str(tmp_path))
        assert ok is False
        assert "5MB" in msg

    def test_streaming_exceeds_limit(self, tmp_path):
        """无 Content-Length 但边读边计数超限。"""
        mod = {"ID": "X", "author_github": "u",
               "repo": "https://github.com/u/r"}

        class _BigResp:
            def __init__(self):
                self.sent = 0
                self.headers = {}   # 没有 Content-Length

            def read(self, n=-1):
                if self.sent >= 6 * 1024 * 1024:
                    return b""
                chunk = b"a" * (1024 * 1024)
                self.sent += len(chunk)
                return chunk

            def __enter__(self):
                return self

            def __exit__(self, *a):
                pass

        # 每次 urlopen 返回全新 mock，避免 sent 跨 URL 累积
        with patch("uno.mod_store.downloader.urlopen",
                   side_effect=lambda *a, **kw: _BigResp()):
            ok, msg = dl.download_mod(mod, pending_dir=str(tmp_path))
        assert ok is False
        assert "5MB" in msg

    def test_success_saves_file(self, tmp_path):
        mod = {"ID": "X", "author_github": "u",
               "repo": "https://github.com/u/r"}
        resp = _FakeResp(b'SEASON_ID = "X"\n')
        with patch("uno.mod_store.downloader.urlopen", return_value=resp):
            ok, msg = dl.download_mod(mod, pending_dir=str(tmp_path))
        assert ok is True
        assert os.path.isfile(msg)
        assert msg.endswith("X.py")

    def test_no_tmp_left_after_success(self, tmp_path):
        mod = {"ID": "X", "author_github": "u",
               "repo": "https://github.com/u/r"}
        resp = _FakeResp(b'data')
        with patch("uno.mod_store.downloader.urlopen", return_value=resp):
            dl.download_mod(mod, pending_dir=str(tmp_path))
        tmps = [f for f in os.listdir(str(tmp_path)) if f.endswith(".tmp")]
        assert tmps == []

    def test_redirect_rejected(self, tmp_path):
        mod = {"ID": "X", "author_github": "u",
               "repo": "https://github.com/u/r"}
        with patch("uno.mod_store.downloader.urlopen",
                   side_effect=urllib.error.HTTPError(
                       "u", 302, "redir", {}, None
                   )):
            ok, msg = dl.download_mod(mod, pending_dir=str(tmp_path))
        assert ok is False
        assert "重定向" in msg

    def test_pending_dir_is_file(self, tmp_path):
        """pending_dir 存在但是文件，应返回错误。"""
        bad = tmp_path / "pending_file"
        bad.write_text("not a dir", encoding="utf-8")
        mod = {"ID": "X", "author_github": "u",
               "repo": "https://github.com/u/r"}
        ok, msg = dl.download_mod(mod, pending_dir=str(bad))
        assert ok is False
        assert "不是目录" in msg


# ==================== check_existing ====================
class TestCheckExisting:
    def test_installed(self, tmp_path):
        (tmp_path / "X.py").write_text("", encoding="utf-8")
        r = dl.check_existing("X", mods_dir=str(tmp_path),
                              pending_dir=str(tmp_path / "_p"))
        assert r is not None
        assert r["location"] == "installed"

    def test_pending(self, tmp_path):
        pd = tmp_path / "_p"
        pd.mkdir()
        (pd / "X.py").write_text("", encoding="utf-8")
        r = dl.check_existing("X", mods_dir=str(tmp_path),
                              pending_dir=str(pd))
        assert r is not None
        assert r["location"] == "pending"

    def test_none(self, tmp_path):
        r = dl.check_existing("X", mods_dir=str(tmp_path),
                              pending_dir=str(tmp_path / "_p"))
        assert r is None

    def test_installed_preferred_over_pending(self, tmp_path):
        pd = tmp_path / "_p"
        pd.mkdir()
        (tmp_path / "X.py").write_text("old", encoding="utf-8")
        (pd / "X.py").write_text("new", encoding="utf-8")
        r = dl.check_existing("X", mods_dir=str(tmp_path),
                              pending_dir=str(pd))
        assert r["location"] == "installed"


# ==================== enable_mod ====================
class TestEnableMod:
    def test_move_no_backup(self, tmp_path):
        mods = tmp_path / "mods"
        pending = mods / "_pending"
        pending.mkdir(parents=True)
        (pending / "X.py").write_text("new", encoding="utf-8")
        ok, msg = dl.enable_mod("X", mods_dir=str(mods),
                                pending_dir=str(pending))
        assert ok is True
        assert (mods / "X.py").read_text(encoding="utf-8") == "new"
        assert not (pending / "X.py").exists()

    def test_move_with_backup_success(self, tmp_path):
        mods = tmp_path / "mods"
        pending = mods / "_pending"
        pending.mkdir(parents=True)
        (mods / "X.py").write_text("old", encoding="utf-8")
        (pending / "X.py").write_text("new", encoding="utf-8")
        ok, msg = dl.enable_mod("X", mods_dir=str(mods),
                                pending_dir=str(pending))
        assert ok is True
        assert (mods / "X.py").read_text(encoding="utf-8") == "new"
        assert not (mods / "X.py.bak").exists()

    def test_old_bak_cleaned_first(self, tmp_path):
        mods = tmp_path / "mods"
        pending = mods / "_pending"
        pending.mkdir(parents=True)
        (mods / "X.py").write_text("old", encoding="utf-8")
        (mods / "X.py.bak").write_text("stale", encoding="utf-8")
        (pending / "X.py").write_text("new", encoding="utf-8")
        ok, msg = dl.enable_mod("X", mods_dir=str(mods),
                                pending_dir=str(pending))
        assert ok is True
        assert (mods / "X.py").read_text(encoding="utf-8") == "new"
        assert not (mods / "X.py.bak").exists()

    def test_mods_dir_missing(self, tmp_path):
        ok, msg = dl.enable_mod("X", mods_dir=str(tmp_path / "none"),
                                pending_dir=str(tmp_path))
        assert ok is False
        assert "不存在" in msg

    def test_pending_missing(self, tmp_path):
        mods = tmp_path / "mods"
        mods.mkdir()
        ok, msg = dl.enable_mod("X", mods_dir=str(mods),
                                pending_dir=str(tmp_path / "none"))
        assert ok is False
        assert "待启用文件不存在" in msg