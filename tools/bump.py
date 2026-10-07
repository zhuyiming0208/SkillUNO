#!/usr/bin/env python3
"""版本号一键升级工具。

用法：
    python tools/bump.py 1.7.0
    python tools/bump.py v1.7.0 --date 2026-10-08
    python tools/bump.py 1.7.0 --dry-run          # 只看不改
    python tools/bump.py 1.7.0 --new-entry "阶段四：下载与安装"

作用：
    自动同步以下文件的版本号：
    - pyproject.toml        → version = "X.Y.Z"
    - src/uno/main.py       → VERSION = "vX.Y.Z"
    - docs/DEVELOPER_GUIDE.md
        · **版本：vX.Y.Z**
        · 当前稳定版本：**vX.Y.Z**
    - docs/VersionBriefHistory.md
        · 从 v0.1.0 到 vX.Y.Z 期间
        · **当前版本：vX.Y.Z**（日期）

    可选 --new-entry 时，会在 VersionBriefHistory.md 顶部
    插入一条新版本条目骨架（标题 + 日期 + 空内容）。

不动的部分：
    - 所有历史条目（## v1.5.0（...）等）
    - 版本历史正文
    - git（不自动 commit / push）
"""
import argparse
import datetime
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def normalize(ver: str) -> str:
    """去掉前缀 v，规范为 X.Y.Z。"""
    ver = ver.strip()
    if ver.startswith('v'):
        ver = ver[1:]
    if not re.fullmatch(r'\d+\.\d+\.\d+', ver):
        raise ValueError(f"版本号格式错误：{ver!r}，应为 X.Y.Z")
    return ver


def replace_pattern(path: Path, pattern: str, repl: str, desc: str,
                    dry_run: bool = False) -> bool:
    """替换文件里的版本号。返回是否成功。"""
    if not path.exists():
        print(f"  [跳过] {path} 不存在")
        return False

    text = path.read_text(encoding='utf-8')
    new_text, count = re.subn(pattern, repl, text, flags=re.MULTILINE)

    if count == 0:
        print(f"  [未匹配] {path} — {desc}")
        return False

    if new_text == text:
        print(f"  [无变化] {path} — {desc}（可能已是目标版本）")
        return True

    if not dry_run:
        path.write_text(new_text, encoding='utf-8')

    tag = "预览" if dry_run else "已改"
    print(f"  [{tag}] {path} — {desc}（{count} 处）")
    return True


def insert_new_entry(path: Path, ver: str, date: str, title: str,
                     dry_run: bool = False):
    """在 VersionBriefHistory.md 的 `---` 分隔线后插入新条目。"""
    if not path.exists():
        print(f"  [跳过] {path} 不存在")
        return

    text = path.read_text(encoding='utf-8')
    entry = f"## v{ver}（{date}）\n\n{title}\n\n- （待补充）\n\n---\n"

    # 找第一个 "---" 分隔线（顶部元信息之后）
    marker = "\n---\n"
    idx = text.find(marker)
    if idx == -1:
        print(f"  [未匹配] {path} — 找不到分隔线 ---")
        return

    insert_at = idx + len(marker)
    new_text = text[:insert_at] + "\n" + entry + text[insert_at:]

    if not dry_run:
        path.write_text(new_text, encoding='utf-8')

    tag = "预览" if dry_run else "已改"
    print(f"  [{tag}] {path} — 插入 v{ver} 条目骨架")
    print(f"      标题：{title}")


def main():
    parser = argparse.ArgumentParser(description="版本号一键升级")
    parser.add_argument("version", help="新版本号，如 1.7.0 或 v1.7.0")
    parser.add_argument("--date", default=None,
                        help="日期（YYYY-MM-DD），默认今天")
    parser.add_argument("--dry-run", action="store_true",
                        help="只显示改动，不写入文件")
    parser.add_argument("--new-entry", default=None,
                        help="在 VersionBriefHistory.md 顶部插入新条目标题")
    args = parser.parse_args()

    try:
        ver = normalize(args.version)
    except ValueError as e:
        print(f"错误：{e}")
        sys.exit(1)

    date = args.date or datetime.date.today().isoformat()

    print(f"\n目标版本：v{ver}（{date}）")
    if args.dry_run:
        print("模式：预览（不写入）")
    print()

    ok_count = 0

    # 1. pyproject.toml
    ok_count += replace_pattern(
        ROOT / "pyproject.toml",
        r'^version\s*=\s*"[^"]+"',
        f'version = "{ver}"',
        "project.version",
        args.dry_run,
    )

    # 2. src/uno/main.py
    ok_count += replace_pattern(
        ROOT / "src/uno/main.py",
        r'^VERSION\s*=\s*"[^"]+"',
        f'VERSION = "v{ver}"',
        "VERSION",
        args.dry_run,
    )

    # 3. docs/DEVELOPER_GUIDE.md
    guide = ROOT / "docs/DEVELOPER_GUIDE.md"
    ok_count += replace_pattern(
        guide,
        r'\*\*版本：v[\d.]+',
        f'**版本：v{ver}',
        "版本标识",
        args.dry_run,
    )
    ok_count += replace_pattern(
        guide,
        r'当前稳定版本：\*\*v[\d.]+',
        f'当前稳定版本：**v{ver}',
        "当前稳定版本",
        args.dry_run,
    )

    # 4. docs/VersionBriefHistory.md
    history = ROOT / "docs/VersionBriefHistory.md"
    ok_count += replace_pattern(
        history,
        r'到 v[\d.]+ 期间',
        f'到 v{ver} 期间',
        "顶部版本范围",
        args.dry_run,
    )
    ok_count += replace_pattern(
        history,
        r'\*\*当前版本：v[\d.]+\*\*（[^）]+）',
        f'**当前版本：v{ver}**（{date}）',
        "当前版本标注",
        args.dry_run,
    )

    # 5. 可选：插入新条目
    if args.new_entry:
        print()
        insert_new_entry(history, ver, date, args.new_entry, args.dry_run)

    print()
    print(f"完成，共 {ok_count} 处文件处理。")

    if args.dry_run:
        print("（预览模式，未写入任何文件）")
    else:
        print("\n下一步建议：")
        print(f"  git add -A && git commit -m 'chore: 版本号升级到 v{ver}'")


if __name__ == "__main__":
    main()
