#!/usr/bin/env python
"""版本号一键升级工具。

用法：
    setver 1.13.0                            # 只升级版本号
    setver 1.13.0 "标题"                      # 升级 + 插入版本历史条目
    setver 1.13.0 "标题" "详情（\\n 换行）"    # 带详情
    setver 1.13.0 "标题" "详情" --git          # 完成后询问是否 git 提交
    setver 1.13.0 --dry-run                  # 预览，不写入

作用：
    自动同步：
    - pyproject.toml
    - src/uno/main.py
    - docs/DEVELOPER_GUIDE.md
    - docs/VersionBriefHistory.md
    如果给了标题，会在版本历史顶部插入新条目。
"""
import argparse
import datetime
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def normalize(ver: str) -> str:
    ver = ver.strip()
    if ver.startswith('v'):
        ver = ver[1:]
    if not re.fullmatch(r'\d+\.\d+\.\d+', ver):
        raise ValueError(f"版本号格式错误：{ver!r}，应为 X.Y.Z")
    return ver


def replace_pattern(path, pattern, repl, desc, dry_run=False):
    if not path.exists():
        print(f"  [跳过] {path} 不存在")
        return False
    text = path.read_text(encoding='utf-8')
    new_text, count = re.subn(pattern, repl, text, flags=re.MULTILINE)
    if count == 0:
        print(f"  [未匹配] {path} — {desc}")
        return False
    if new_text == text:
        print(f"  [无变化] {path} — {desc}")
        return True
    if not dry_run:
        path.write_text(new_text, encoding='utf-8')
    tag = "预览" if dry_run else "已改"
    print(f"  [{tag}] {path} — {desc}（{count} 处）")
    return True


def insert_new_entry(path, ver, date, subject, details, dry_run=False):
    """在版本历史顶部插入新条目。"""
    if not path.exists():
        print(f"  [跳过] {path} 不存在")
        return
    text = path.read_text(encoding='utf-8')

    # 防重复：同一版本号已在历史中则跳过
    if re.search(rf'^## v{re.escape(ver)}(?:\s|（|$)', text, re.MULTILINE):
        print(f"  [跳过] 版本历史中已存在 v{ver}，无需重复插入")
        return

    body = subject
    if details:
        details_text = details.replace('\\n', '\n')
        body += f"\n\n{details_text}"

    entry = f"## v{ver}（{date}）\n\n{body}\n\n---\n\n"

    m = re.search(r'^## v[\d.]+', text, re.MULTILINE)
    if not m:
        print(f"  [跳过] {path} — 找不到 ## vX.Y.Z 条目")
        return
    idx = m.start()
    new_text = text[:idx] + entry + text[idx:]

    if not dry_run:
        path.write_text(new_text, encoding='utf-8')
    tag = "预览" if dry_run else "已改"
    print(f"  [{tag}] {path} — 插入 v{ver} 条目")


def ask_and_run_git(commit_msg):
    print()
    answer = input("是否立即 git 提交并推送？(y/N，回车跳过) ").strip().lower()
    if answer != 'y':
        print("已跳过 git 操作（如需预览不写文件，请用 --dry-run；")
        print("             如需只改文件不提交，请去掉 --git 参数）")
        return
    try:
        print("→ git add -A")
        subprocess.run(["git", "add", "-A"], check=True, cwd=ROOT)
        print(f"→ git commit -m {commit_msg!r}")
        subprocess.run(["git", "commit", "-m", commit_msg], check=True, cwd=ROOT)
        print("→ git push")
        subprocess.run(["git", "push"], check=True, cwd=ROOT)
        print("✅ 已提交并推送")
    except subprocess.CalledProcessError as e:
        print(f"❌ git 操作失败：{e}")
    except Exception as e:
        print(f"❌ 意外错误：{e}")


def main():
    parser = argparse.ArgumentParser(
        description="版本号一键升级",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""示例：
  setver 1.13.0
  setver 1.13.0 "新增 X 功能"
  setver 1.13.0 "新增 X 功能" "- 加了 A\\n- 修了 B" --git
""",
    )
    parser.add_argument("version", help="新版本号，如 1.13.0 或 v1.13.0")
    parser.add_argument("subject", nargs="?", default=None,
                        help="版本历史标题（可选）")
    parser.add_argument("details", nargs="?", default=None,
                        help="版本历史详情，用 \\n 表示换行（可选）")
    parser.add_argument("--date", default=None,
                        help="日期（YYYY-MM-DD），默认今天")
    parser.add_argument("--dry-run", action="store_true",
                        help="只显示改动，不写入文件")
    parser.add_argument("--git", action="store_true",
                        help="完成后询问是否 git 提交并推送")
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

    replace_pattern(
        ROOT / "pyproject.toml",
        r'^version\s*=\s*"[^"]+"',
        f'version = "{ver}"',
        "project.version",
        args.dry_run,
    )

    replace_pattern(
        ROOT / "src/uno/main.py",
        r'^VERSION\s*=\s*"[^"]+"',
        f'VERSION = "v{ver}"',
        "VERSION",
        args.dry_run,
    )

    guide = ROOT / "docs/DEVELOPER_GUIDE.md"
    replace_pattern(guide, r'\*\*版本：v[\d.]+',
                    f'**版本：v{ver}', "版本标识", args.dry_run)
    replace_pattern(guide, r'当前稳定版本：\*\*v[\d.]+',
                    f'当前稳定版本：**v{ver}', "当前稳定版本", args.dry_run)
    replace_pattern(guide, r'\*\*最后更新：[\d-]+\*\*',
                    f'**最后更新：{date}**', "头部最后更新", args.dry_run)

    history = ROOT / "docs/VersionBriefHistory.md"
    replace_pattern(history, r'到 v[\d.]+ 期间',
                    f'到 v{ver} 期间', "顶部版本范围", args.dry_run)
    replace_pattern(history, r'\*\*当前版本：v[\d.]+\*\*（[^）]+）',
                    f'**当前版本：v{ver}**（{date}）', "当前版本标注", args.dry_run)
    replace_pattern(history, r'最后更新：[\d-]+ · v[\d.]+',
                    f'最后更新：{date} · v{ver}', "尾部最后更新", args.dry_run)

    if args.subject:
        print()
        insert_new_entry(history, ver, date, args.subject, args.details, args.dry_run)

    print()
    print("完成。")

    if args.dry_run:
        print("（预览模式，未写入任何文件）")
        return

    if args.git:
        commit_msg = args.subject or f"chore: 版本号升级到 v{ver}"
        ask_and_run_git(commit_msg)
    else:
        print(f"\n下一步：git add -A && git commit -m '...' && git push")


if __name__ == "__main__":
    main()
