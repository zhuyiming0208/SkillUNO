"""键盘输入处理。

【为什么不支持方向键】
在 Termux / Android 软键盘上，方向键通过 \\x1b[A/B/C/D 发送，
但字节间隔经常超过 0.5 秒，无法可靠拼接识别。因此改用单字符键。

【键位映射表】
    u  → UP
    d  → DOWN
    l  → LEFT
    r  → RIGHT
    s  → SEARCH
    h  → HELP
    q  → QUIT
    ~  → BACK（代替 ESC）
    x  → DELETE（阶段三预留）

【确认键有多种写法】
回车（\\r、\\n）、空格、字母 e 都视为 ENTER，
兼容软键盘（回车发送 \\r，软键盘备用 'e'）。

【非 TTY 环境】
CI（GitHub Actions）里 sys.stdin 不是终端，termios.tcgetattr()
会抛异常。read_key() 捕获所有异常后返回 None，调用方需处理 None。
"""
import os
import sys
from typing import Optional


# ---------- 键位常量 ----------
KEY_UP = 'u'
KEY_DOWN = 'd'
KEY_LEFT = 'l'
KEY_RIGHT = 'r'
KEY_SEARCH = 's'
KEY_HELP = 'h'
KEY_QUIT = 'q'
KEY_BACK = '~'
KEY_DELETE = 'x'
KEY_CONFIRM_CHARS = ('\r', '\n', ' ', 'e')


# ---------- 事件类型 ----------
class EventType:
    UP = "UP"
    DOWN = "DOWN"
    LEFT = "LEFT"
    RIGHT = "RIGHT"
    ENTER = "ENTER"
    BACK = "BACK"
    QUIT = "QUIT"
    SEARCH = "SEARCH"
    HELP = "HELP"
    DELETE = "DELETE"
    CHAR = "CHAR"
    UNKNOWN = "UNKNOWN"


class KeyEvent:
    """统一的键盘事件对象。"""

    def __init__(self, type: str, char: Optional[str] = None):
        self.type = type
        self.char = char

    def __repr__(self):
        return f"KeyEvent({self.type}, {self.char!r})"

    def __eq__(self, other):
        if not isinstance(other, KeyEvent):
            return NotImplemented
        return self.type == other.type and self.char == other.char


# ---------- 读取 ----------
def read_key() -> Optional[KeyEvent]:
    """读取单个按键。

    - 非 TTY 环境返回 None
    - Ctrl+C 抛 KeyboardInterrupt
    - 其他异常返回 None（保护 CI）
    """
    try:
        if os.name == 'nt':
            ch = _read_win()
        else:
            ch = _read_unix()
    except KeyboardInterrupt:
        raise
    except Exception:
        return None

    if ch is None or ch == '':
        return None

    # Ctrl+C
    if ch == '\x03':
        raise KeyboardInterrupt()

    return _map_char(ch)


def _read_win() -> Optional[str]:
    try:
        import msvcrt
        return msvcrt.getwch()
    except Exception:
        return None


def _read_unix() -> Optional[str]:
    import tty
    import termios

    try:
        if not sys.stdin.isatty():
            return None
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
    except (termios.error, OSError, ValueError):
        return None

    try:
        tty.setraw(fd)
        ch = sys.stdin.read(1)
    finally:
        # 必须恢复终端状态，防止崩溃后卡在 raw 模式
        try:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        except Exception:
            pass
    return ch


def _map_char(ch: str) -> KeyEvent:
    """字符 → KeyEvent。字母统一小写化后再匹配。"""
    lowered = ch.lower()

    # 确认键（先判断，避免 'e' 与字母键冲突）
    # lowered 处理过大小写，所以 'E' 也能识别为 ENTER
    if lowered in KEY_CONFIRM_CHARS:
        return KeyEvent(EventType.ENTER, ch)

    if lowered == KEY_UP:
        return KeyEvent(EventType.UP)
    if lowered == KEY_DOWN:
        return KeyEvent(EventType.DOWN)
    if lowered == KEY_LEFT:
        return KeyEvent(EventType.LEFT)
    if lowered == KEY_RIGHT:
        return KeyEvent(EventType.RIGHT)
    if lowered == KEY_SEARCH:
        return KeyEvent(EventType.SEARCH)
    if lowered == KEY_HELP:
        return KeyEvent(EventType.HELP)
    if lowered == KEY_QUIT:
        return KeyEvent(EventType.QUIT)
    if lowered == KEY_BACK:
        return KeyEvent(EventType.BACK)
    if lowered == KEY_DELETE:
        return KeyEvent(EventType.DELETE)

    return KeyEvent(EventType.CHAR, ch)