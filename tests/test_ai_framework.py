"""AI 策略模式框架测试。"""
import os
import sys

import pytest

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)
SRC_DIR = os.path.join(PROJECT_ROOT, "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from uno.ai.base import BaseAI
from uno.ai.simple import SimpleAI
from uno.core import Player, Card


class _FixedAI(BaseAI):
    """测试用：总是返回固定牌索引和固定颜色。"""
    def __init__(self, card_idx=0, color="蓝"):
        self.card_idx = card_idx
        self.color = color
        self.choose_turn_calls = 0
        self.choose_color_calls = 0

    def choose_turn(self, player, game, top_card, current_color):
        self.choose_turn_calls += 1
        return self.card_idx

    def choose_color(self, player):
        self.choose_color_calls += 1
        return self.color


def test_player_default_strategy_is_simple():
    """不传策略时，AI 玩家默认 SimpleAI。"""
    p = Player("电脑X")
    assert isinstance(p.ai_strategy, SimpleAI)


def test_player_human_also_gets_strategy():
    """人类玩家也持有策略对象（防止 is_human 翻转后崩溃）。"""
    p = Player("我", is_human=True)
    assert isinstance(p.ai_strategy, SimpleAI)


def test_player_injected_strategy():
    """注入 Mock 策略后，Player 使用注入的实例。"""
    mock = _FixedAI(card_idx=2)
    p = Player("电脑X", ai_strategy=mock)
    assert p.ai_strategy is mock


def test_player_injected_class_is_instantiated():
    """传入类时自动实例化。"""
    p = Player("电脑X", ai_strategy=SimpleAI)
    assert isinstance(p.ai_strategy, SimpleAI)


def test_ai_choose_calls_injected_strategy():
    """ai_choose 真的委托给策略。"""
    mock = _FixedAI(card_idx=1)
    p = Player("电脑X", ai_strategy=mock)
    p.hand = [Card('红', '数字', 1), Card('蓝', '数字', 2)]
    p.game = None  # 不影响 mock，因为 mock 不访问 game

    class _DummyGame:
        pass

    p.game = _DummyGame()
    idx = p.ai_choose(Card('红', '数字', 5), '红')
    assert idx == 1
    assert mock.choose_turn_calls == 1


def test_choose_color_calls_injected_strategy():
    """choose_color 的 AI 分支委托给策略。"""
    mock = _FixedAI(color="绿")
    p = Player("电脑X", ai_strategy=mock)
    p.hand = [Card('红', '数字', 1)]
    assert p.choose_color() == "绿"
    assert mock.choose_color_calls == 1


def test_game_accepts_ai_strategy_kwarg():
    """UNOGame 接受 ai_strategy 注入并传递给 AI 玩家。"""
    from uno.core import UNOGame
    mock = _FixedAI()
    game = UNOGame(debug=False, use_rich_ui=False, ai_strategy=mock)
    ai_players = [p for p in game.players if not p.is_human]
    assert len(ai_players) >= 1
    for p in ai_players:
        assert p.ai_strategy is mock
