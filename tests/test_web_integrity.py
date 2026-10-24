"""网页版静态资源完整性检查。

不需要浏览器，纯 Python 扫描 HTML，防止：
- 资源路径写错（例如 collections/ 页面多写了一层 ../）
- 跳转目标不存在
- JSON 数据缺失或格式错误
- 索引引用不存在的文件
"""
import json
import re
import shutil
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent
WEB_DIR = ROOT / "web"
MODS_DIR = ROOT / "mods"

SKIP_PREFIXES = (
    "http://", "https://", "//", "#",
    "mailto:", "tel:", "javascript:", "data:",
)


def _find_html_files():
    return sorted(WEB_DIR.rglob("*.html"))


def _extract_local_refs(html_path: Path):
    """提取 HTML 里的本地资源引用（src / href）。"""
    text = html_path.read_text(encoding="utf-8")
    scripts = re.findall(r'<script[^>]+src=["\']([^"\']+)["\']', text)
    links = re.findall(r'<link[^>]+href=["\']([^"\']+)["\']', text)
    anchors = re.findall(r'<a[^>]+href=["\']([^"\']+)["\']', text)

    refs = []
    for ref in scripts + links + anchors:
        ref = ref.strip()
        if not ref or ref.startswith(SKIP_PREFIXES):
            continue
        # 去掉 ?query 和 #fragment
        ref = ref.split("?")[0].split("#")[0]
        if ref:
            refs.append(ref)
    return refs


@pytest.fixture(scope="session", autouse=True)
def prepare_web_assets():
    """测试前把 mods/*.json 复制到 web/ 下，模拟部署流程。"""
    (WEB_DIR / "mods").mkdir(parents=True, exist_ok=True)
    (WEB_DIR / "collections").mkdir(parents=True, exist_ok=True)
    for src in MODS_DIR.glob("*.json"):
        shutil.copy2(src, WEB_DIR / "mods" / src.name)
    shutil.copy2(
        MODS_DIR / "collections.json",
        WEB_DIR / "collections" / "collections.json",
    )
    yield


@pytest.mark.parametrize(
    "html",
    _find_html_files(),
    ids=lambda p: str(p.relative_to(WEB_DIR)),
)
def test_local_refs_exist(html):
    """每个 HTML 里引用的本地资源都必须真实存在。"""
    refs = _extract_local_refs(html)
    missing = []
    for ref in refs:
        target = (html.parent / ref).resolve()
        if not target.exists():
            missing.append(ref)
    assert not missing, (
        f"{html.relative_to(WEB_DIR)} 引用了不存在的资源：{missing}"
    )


def test_at_least_4_html_files():
    files = _find_html_files()
    assert len(files) >= 4, f"只找到 {len(files)} 个 HTML 文件"


def test_collections_json_valid():
    data = json.loads((MODS_DIR / "collections.json").read_text(encoding="utf-8"))
    assert "collections" in data
    for c in data["collections"]:
        assert "id" in c and "mods" in c
        assert isinstance(c["mods"], list)


def test_mod_idx_json_valid():
    data = json.loads((MODS_DIR / "mod_idx.json").read_text(encoding="utf-8"))
    assert "handpicked" in data
    assert "other" in data


def test_mod_idx_files_exist():
    data = json.loads((MODS_DIR / "mod_idx.json").read_text(encoding="utf-8"))
    files = list(data.get("handpicked", [])) + list(data.get("other", []))
    missing = [f for f in files if not (MODS_DIR / f).exists()]
    assert not missing, f"mod_idx.json 引用了不存在的文件：{missing}"


def test_official_mod_json_exist():
    for mid in ("S1", "S2", "S3", "S4"):
        path = MODS_DIR / f"{mid}.json"
        assert path.exists(), f"缺少官方元数据 {path}"
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data.get("ID") == mid


def test_collections_mods_exist():
    """模组集里列出的模组 ID 有对应的 JSON 文件。"""
    data = json.loads((MODS_DIR / "collections.json").read_text(encoding="utf-8"))
    missing = []
    for c in data["collections"]:
        for mid in c.get("mods", []):
            if not (MODS_DIR / f"{mid}.json").exists():
                missing.append(f"{c['id']} → {mid}")
    assert not missing, f"模组集引用了不存在的模组：{missing}"

# ===== v1.16.0 标签筛选静态检查 =====

def test_mods_list_has_tag_filter_html():
    """mods 列表页必须包含标签栏容器与 data-tag 钩子。"""
    html = (WEB_DIR / "mods" / "index.html").read_text(encoding="utf-8")
    assert 'id="tag-list"' in html, "缺少标签栏容器 #tag-list"
    assert 'data-tag=' in html, "缺少 data-tag 钩子"


def test_search_js_has_tag_functions():
    """search.js 必须定义 extractTags 与 filterByTag。"""
    js = (WEB_DIR / "assets" / "js" / "search.js").read_text(encoding="utf-8")
    assert "function extractTags" in js, "缺少 extractTags()"
    assert "function filterByTag" in js, "缺少 filterByTag()"


def test_mods_list_loads_search_js():
    """mods 列表页必须引入 search.js（防漏加 script 标签）。"""
    html = (WEB_DIR / "mods" / "index.html").read_text(encoding="utf-8")
    assert re.search(r'<script[^>]+src=["\'][^"\']*search\.js', html), \
        "mods/index.html 未引入 search.js"

