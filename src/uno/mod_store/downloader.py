"""下载与启用模组。

安全约束：
- URL 白名单：raw.githubusercontent.com、cdn.jsdelivr.net
- 5MB 下载上限
- 不跟随重定向
- 临时文件 + 原子重命名
- 覆盖前先备份 .bak
"""
import os
import urllib.parse
import urllib.error
from urllib.request import Request, build_opener, HTTPRedirectHandler


ALLOWED_HOSTS = {"raw.githubusercontent.com", "cdn.jsdelivr.net"}
MAX_DOWNLOAD_SIZE = 5 * 1024 * 1024  # 5 MB
USER_AGENT = "SkillUNO-ModStore/1.0"
TIMEOUT = 10


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


_opener = build_opener(_NoRedirect)


def urlopen(req, timeout=None):
    """模块级 urlopen，便于测试 mock。拒绝重定向（3xx 会抛 HTTPError）。"""
    if timeout is None:
        return _opener.open(req)
    return _opener.open(req, timeout=timeout)


# ---------- URL 构造 ----------
def _extract_repo_name(repo_url: str) -> str:
    if not repo_url:
        return ""
    s = repo_url.rstrip("/")
    if s.endswith(".git"):
        s = s[:-4]
    return s.split("/")[-1]


def build_download_urls(mod_data: dict) -> list:
    """返回候选 URL 列表，按优先级排序。

    branch 非空时只生成 2 个 URL（raw + jsdelivr）；
    branch 为空时生成 4 个 URL（raw/main、raw/master、jsdelivr/main、jsdelivr/master）。
    """
    author = (mod_data.get("author_github") or "").strip()
    repo_url = (mod_data.get("repo") or "").strip()
    if not author or not repo_url:
        return []
    repo_name = _extract_repo_name(repo_url)
    if not repo_name:
        return []
    mod_id = mod_data.get("ID") or "MOD"
    py_file = mod_data.get("py_file") or f"{mod_id}.py"
    encoded = urllib.parse.quote(py_file, safe="")
    branch = (mod_data.get("branch") or "").strip()

    if branch:
        return [
            f"https://raw.githubusercontent.com/{author}/{repo_name}/{branch}/{encoded}",
            f"https://cdn.jsdelivr.net/gh/{author}/{repo_name}@{branch}/{encoded}",
        ]
    return [
        f"https://raw.githubusercontent.com/{author}/{repo_name}/main/{encoded}",
        f"https://raw.githubusercontent.com/{author}/{repo_name}/master/{encoded}",
        f"https://cdn.jsdelivr.net/gh/{author}/{repo_name}@main/{encoded}",
        f"https://cdn.jsdelivr.net/gh/{author}/{repo_name}@master/{encoded}",
    ]


# ---------- 下载 ----------
def _safe_remove(path):
    try:
        if os.path.isfile(path):
            os.remove(path)
    except OSError:
        pass


def _try_download(url, tmp_path):
    parsed = urllib.parse.urlparse(url)
    if parsed.hostname not in ALLOWED_HOSTS:
        return (False, f"不允许的下载来源：{parsed.hostname}")

    req = Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urlopen(req, timeout=TIMEOUT) as resp:
            try:
                cl = resp.headers.get("Content-Length")
            except AttributeError:
                cl = None
            if cl is not None:
                try:
                    if int(cl) > MAX_DOWNLOAD_SIZE:
                        return (False, "文件超过 5MB 限制，拒绝下载")
                except ValueError:
                    pass

            total = 0
            with open(tmp_path, "wb") as f:
                while True:
                    chunk = resp.read(8192)
                    if not chunk:
                        break
                    total += len(chunk)
                    if total > MAX_DOWNLOAD_SIZE:
                        _safe_remove(tmp_path)
                        return (False, "文件超过 5MB 限制，拒绝下载")
                    f.write(chunk)
        return (True, "")
    except urllib.error.HTTPError as e:
        _safe_remove(tmp_path)
        if e.code == 404:
            return (False, "模组文件不存在，可能已被作者删除")
        if e.code in (301, 302, 307, 308):
            return (False, "不支持重定向，请提供直链")
        return (False, f"HTTP 错误 {e.code}")
    except urllib.error.URLError as e:
        _safe_remove(tmp_path)
        if "timed out" in str(e).lower():
            return (False, "下载超时，请检查网络")
        return (False, f"网络连接失败：{e}")
    except Exception as e:
        _safe_remove(tmp_path)
        return (False, f"下载失败：{e}")


def download_mod(mod_data, pending_dir="mods/_pending", mods_dir="mods"):
    """下载模组 .py 文件到 pending 目录。返回 (成功, 路径或错误信息)。"""
    mod_id = mod_data.get("ID") or "MOD"

    # 先校验 repo 域名，防止 evil.com 之类的伪造
    repo_url = (mod_data.get("repo") or "").strip()
    if not repo_url.startswith("https://github.com/"):
        return (False, f"不允许的下载来源：{repo_url or '(空)'}")

    urls = build_download_urls(mod_data)
    if not urls:
        return (False, "无法构造下载链接（缺少 author_github 或 repo）")

    # 确保 pending_dir 是目录
    try:
        if os.path.exists(pending_dir):
            if not os.path.isdir(pending_dir):
                return (False, f"路径已存在但不是目录：{pending_dir}")
        else:
            os.makedirs(pending_dir, exist_ok=True)
    except OSError as e:
        return (False, f"无法创建目录 {pending_dir}：{e}")

    final_path = os.path.join(pending_dir, f"{mod_id}.py")
    tmp_path = final_path + ".tmp"

    last_error = "下载失败"
    for url in urls:
        ok, msg = _try_download(url, tmp_path)
        if ok:
            try:
                os.replace(tmp_path, final_path)
                return (True, final_path)
            except OSError as e:
                _safe_remove(tmp_path)
                return (False, f"保存文件失败：{e}")
        last_error = msg

    _safe_remove(tmp_path)
    return (False, last_error)


# ---------- 检查已存在 ----------
def check_existing(mod_id, mods_dir="mods", pending_dir="mods/_pending"):
    installed = os.path.join(mods_dir, f"{mod_id}.py")
    if os.path.isfile(installed):
        return {"location": "installed", "path": installed}
    pending = os.path.join(pending_dir, f"{mod_id}.py")
    if os.path.isfile(pending):
        return {"location": "pending", "path": pending}
    return None


# ---------- 启用 ----------
def enable_mod(mod_id, mods_dir="mods", pending_dir="mods/_pending"):
    """启用待安装模组，覆盖时先备份。返回 (成功, 消息/路径)。"""
    if not os.path.isdir(mods_dir):
        return (False, f"目标目录不存在：{mods_dir}")
    src = os.path.join(pending_dir, f"{mod_id}.py")
    if not os.path.isfile(src):
        return (False, f"待启用文件不存在：{src}")
    dst = os.path.join(mods_dir, f"{mod_id}.py")
    bak = dst + ".bak"

    # 清理旧备份
    if os.path.isfile(bak):
        try:
            os.remove(bak)
        except OSError as e:
            return (False, f"无法删除旧备份 {bak}：{e}")

    # 备份已安装文件
    if os.path.isfile(dst):
        try:
            os.rename(dst, bak)
        except OSError as e:
            return (False, f"备份失败：{e}")

    # 移动待启用文件
    try:
        os.rename(src, dst)
    except OSError as e:
        # 恢复备份
        if os.path.isfile(bak):
            try:
                os.rename(bak, dst)
            except OSError:
                pass
        return (False, f"移动文件失败：{e}")

    # 成功后删除备份
    if os.path.isfile(bak):
        try:
            os.remove(bak)
        except OSError:
            pass

    return (True, dst)