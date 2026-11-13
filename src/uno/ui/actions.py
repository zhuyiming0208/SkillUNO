"""结构化 UI 动作协议。

设计目的：
- 让 TextualUI 可以返回「点击出牌」「点击抽牌」这类结构化动作
- ConsoleUI 默认返回 None，走原有 human_choose 循环，CLI 体验零变化
- core.py 的 choose_play 看到 Action 直接消费，看到 None 走旧流程
"""
from dataclasses import dataclass


@dataclass
class PlayCardAction:
    """玩家选择打出某张手牌。"""
    card_index: int


@dataclass
class DrawCardAction:
    """玩家选择抽牌。"""
    pass


@dataclass
class QuitGameAction:
    """玩家选择退出当前对局。"""
    pass
