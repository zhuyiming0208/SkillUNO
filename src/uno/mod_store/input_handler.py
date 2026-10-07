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
    \\x7f / \\x08 → BACKSPACE

【确认键有多种写法】
回车（\\r、\\n）、空格、字母 e 都视为 ENTER，
兼容软键盘（回车发送 \\r，软键盘备用 'e'）。

【UTF-8 多字节字符】
Termux 的中文输入发送 3 字节 UTF-8 序列（如 "示" → e7 a4 ba）。
read_key() 根据首字节判断 UTF-8 长度，自动补读后续字节，
返回完整的 KeyEvent(CHAR, "示")。

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
    BACKSPACE = "BACKSPACE"
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
    """读取单个按键（含 UTF-8 多字节字符）。"""
    try:
        first = _read_bytes()
    except KeyboardInterrupt:
        raise
    except Exception:
        return None

    if first is None:
        return None

    # Ctrl+C 在 raw 模式下不触发 KeyboardInterrupt，需要显式判断
    if first == b'\x03':
        raise KeyboardInterrupt()

    # 根据首字节判断 UTF-8 总长度
    b0 = first[0]
    if b0 < 0x80:
        total = 1
    elif (b0 & 0xE0) == 0xC0:
        total = 2
    elif (b0 & 0xF0) == 0xE0:
        total = 3
    elif (b0 & 0xF8) == 0xF0:
        total = 4
    else:
        total = 1  # 非法起始字节，当单字节处理

    buf = first
    while len(buf) < total:
        try:
            more = _read_bytes()
        except Exception:
            break
        if more is None:
            break
        buf += more

    try:
        ch = buf.decode('utf-8')
    except UnicodeDecodeError:
        ch = buf.decode('utf-8', errors='replace')

    return _map_char(ch)


def _read_bytes() -> Optional[bytes]:
    """读一个字节。"""
    if os.name == 'nt':
        return _read_win_bytes()
    return _read_unix_bytes()


def _read_win_bytes() -> Optional[bytes]:
    try:
        import msvcrt
        ch = msvcrt.getwch()
        if not ch:
            return None
        return ch.encode('utf-8')
    except Exception:
        return None


def _read_unix_bytes() -> Optional[bytes]:
    import tty
    import termios

    try:
        if not sys.stdin.isatty():
            return None
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
    except (termios.error, OSError, ValueError, AttributeError):
        return None

    try:
        tty.setraw(fd)
        data = os.read(fd, 1)
    finally:
        # 必须恢复终端状态，防止崩溃后卡在 raw 模式
        try:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        except Exception:
            pass

    return data if data else None


def _map_char(ch: str) -> KeyEvent:
    """字符 → KeyEvent。字母统一小写化后再匹配。"""
    lowered = ch.lower()

    # 退格（先判断）
    if ch in ('\x7f', '\x08'):
        return KeyEvent(EventType.BACKSPACE)

    # 确认键（'e' 与字母键冲突，先判断）
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