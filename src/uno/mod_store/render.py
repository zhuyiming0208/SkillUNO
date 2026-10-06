"""终端渲染：画框、对齐、着色、清屏。

中文字符按 2 宽度计算；ANSI 颜色在无 TTY 或 NO_COLOR 环境下自动降级。
"""
import os
import sys
import re
import unicodedata


# ANSI 转义序列正则（用于在宽度计算中跳过）
_ANSI_RE = re.compile(r'\x1b\[[0-9;]*m')


# ---------- 显示宽度 ----------
def display_width(text: str) -> int:
    """计算字符串的终端显示宽度。

    - 中文/全角字符 = 2
    - ASCII = 1
    - 组合字符 = 0
    - emoji 一律当 1（不做复杂处理）
    - ANSI 转义序列忽略
    """
    text = _ANSI_RE.sub('', text)
    width = 0
    for ch in text:
        if unicodedata.combining(ch):
            continue
        ea = unicodedata.east_asian_width(ch)
        if ea in ('W', 'F'):
            width += 2
        else:
            width += 1
    return width


def pad_text(text: str, width: int, align: str = "left") -> str:
    """按显示宽度对齐文本。

    align: 'left' | 'right' | 'center'
    若文本显示宽度已 >= width，原样返回。
    """
    w = display_width(text)
    if w >= width:
        return text
    padding = width - w
    if align == "right":
        return " " * padding + text
    if align == "center":
        left = padding // 2
        right = padding - left
        return " " * left + text + " " * right
    # 默认左对齐
    return text + " " * padding


# ---------- 颜色 ----------
_COLOR_CODES = {
    "reset": "\x1b[0m",
    "bold": "\x1b[1m",
    "dim": "\x1b[2m",
    "red": "\x1b[31m",
    "green": "\x1b[32m",
    "yellow": "\x1b[33m",
    "blue": "\x1b[34m",
    "magenta": "\x1b[35m",
    "cyan": "\x1b[36m",
    "white": "\x1b[37m",
    "bright_cyan": "\x1b[96m",
    "bright_yellow": "\x1b[93m",
    "bright_black": "\x1b[90m",
    "bg_blue": "\x1b[44m",
    "bg_cyan": "\x1b[46m",
}


def supports_color() -> bool:
    """检测当前终端是否支持 ANSI 颜色。

    - 环境变量 NO_COLOR 存在 → 禁用
    - 环境变量 FORCE_COLOR 存在 → 强制启用
    - 否则看 sys.stdout.isatty()
    """
    if os.environ.get("NO_COLOR"):
        return False
    if os.environ.get("FORCE_COLOR"):
        return True
    try:
        return sys.stdout.isatty()
    except (AttributeError, ValueError):
        return False


def colorize(text: str, color: str) -> str:
    """给文本上色。不支持颜色或颜色名未知时返回原文。"""
    if not supports_color():
        return text
    code = _COLOR_CODES.get(color)
    if code is None:
        return text
    return f"{code}{text}{_COLOR_CODES['reset']}"


# ---------- 清屏 / 光标 ----------
def clear_screen() -> None:
    """清屏。"""
    if os.name == 'nt':
        os.system('cls')
    else:
        sys.stdout.write('\x1b[2J\x1b[H')
        sys.stdout.flush()


def move_cursor(row: int, col: int) -> None:
    """把光标移动到指定行列（1-based）。"""
    sys.stdout.write(f'\x1b[{row};{col}H')
    sys.stdout.flush()


# ---------- 画框 ----------
def draw_box(lines, width: int, title: str = "") -> str:
    """绘制带标题的边框。

    lines: 内容行列表
    width: 内宽（不含两侧竖线）
    title: 可选标题，居中显示在顶边

    返回完整多行字符串。
    """
    result = []

    # 顶边
    if title:
        title_w = display_width(title)
        if width >= title_w + 4:
            side_total = width - title_w - 2  # 两侧各留 1 空格
            left = side_total // 2
            right = side_total - left
            top = "╔" + "═" * left + " " + title + " " + "═" * right + "╗"
        else:
            top = "╔" + "═" * width + "╗"
    else:
        top = "╔" + "═" * width + "╗"
    result.append(top)

    # 内容
    for line in lines:
        line_w = display_width(line)
        pad = width - line_w
        if pad < 0:
            # 超宽：不截断（可能破坏对齐，但优先保留内容）
            pad = 0
        result.append("║" + line + " " * pad + "║")

    # 底边
    result.append("╚" + "═" * width + "╝")
    return "\n".join(result)