"""HeuristicAI 启发式规则测试。"""
import os
import sys

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)
SRC_DIR = os.path.join(PROJECT_ROOT, "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from uno.ai.heuristic import HeuristicAI
from uno.core import Player, Card


class _FakeNext:
    def __init__(self, hand_size):
        self._n = hand_size
    def hand_size(self):
        return self._n


class _FakeGame:
    def __init__(self, next_hand_size=99, skill_manager=None):
        self._next = _FakeNext(next_hand_size)
        self.skill_manager = skill_manager
    def peek_next_player(self):
        return self._next


def _mk_ai_player(hand):
    p = Player("测试AI")
    p.hand = list(hand)
    return p


def test_kill_zone_prefers_plus2():
    """下家剩 1 张，手里有 +2 和普通牌，必须出 +2。"""
    ai = HeuristicAI()
    p = _mk_ai_player([Card('红', '数字', 3), Card('红', '+2')])
    game = _FakeGame(next_hand_size=1)
    idx = ai.choose_turn(p, game, Card('红', '数字', 5), '红')
    assert p.hand[idx].type == '+2'


def test_not_kill_zone_saves_plus4():
    """下家手牌多，手里有万能+4 和普通牌，必须出普通牌。"""
    ai = HeuristicAI()
    p = _mk_ai_player([Card('黑', '万能+4'), Card('红', '数字', 3)])
    game = _FakeGame(next_hand_size=5)
    idx = ai.choose_turn(p, game, Card('红', '数字', 5), '红')
    assert p.hand[idx].type == '数字'


def test_color_picks_most():
    """红 3 张、蓝 1 张，选红。"""
    ai = HeuristicAI()
    p = _mk_ai_player([
        Card('红', '数字', 1), Card('红', '数字', 2), Card('红', '数字', 3),
        Card('蓝', '数字', 4),
    ])
    assert ai.choose_color(p) == '红'


def test_color_picks_most_even_when_next_is_low():
    """下家剩 1 张，自己红 1 蓝 5，仍选蓝（自己最多）。"""
    ai = HeuristicAI()
    p = _mk_ai_player([
        Card('红', '数字', 1),
        Card('蓝', '数字', 2), Card('蓝', '数字', 3), Card('蓝', '数字', 4),
        Card('蓝', '数字', 5), Card('蓝', '数字', 6),
    ])
    assert ai.choose_color(p) == '蓝'


def test_skip_preferred_in_kill_zone():
    """下家剩 1 张，跳过得分高于普通牌。"""
    ai = HeuristicAI()
    p = _mk_ai_player([Card('红', '数字', 3), Card('红', '跳过')])
    game = _FakeGame(next_hand_size=1)
    idx = ai.choose_turn(p, game, Card('红', '数字', 5), '红')
    assert p.hand[idx].type == '跳过'


def test_no_playable_returns_none():
    """无可出牌返回 None。"""
    ai = HeuristicAI()
    p = _mk_ai_player([Card('蓝', '数字', 3)])
    game = _FakeGame(next_hand_size=5)
    idx = ai.choose_turn(p, game, Card('红', '数字', 5), '红')
    assert idx is None


def test_plus4_saved_when_two_cards_left():
    """手里只剩 2 张，优先出普通牌保留 +4。"""
    ai = HeuristicAI()
    p = _mk_ai_player([Card('黑', '万能+4'), Card('红', '数字', 3)])
    game = _FakeGame(next_hand_size=5)
    idx = ai.choose_turn(p, game, Card('红', '数字', 5), '红')
    assert p.hand[idx].type == '数字'
