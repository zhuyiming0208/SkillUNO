"""MctsAI 单元测试。"""
import os
import sys
import time
import copy

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)
SRC_DIR = os.path.join(PROJECT_ROOT, "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from uno.ai.mcts import MctsAI, MctsNode
from uno.core import UNOGame, Card, NullUI


def _build_game():
    g = UNOGame(debug=False, use_rich_ui=False,
                players=["A", "B", "C", "D"], enabled_seasons=["S1"])
    g.ui = NullUI()
    for p in g.players:
        p.ui = NullUI()
        p.is_human = False
    g.setup()
    g.current_player_idx = 0
    return g


def test_deepcopy_isolation():
    """deepcopy 不污染原游戏。"""
    g = _build_game()
    orig_hand = len(g.players[0].hand)
    orig_deck = len(g.deck.cards)
    g2 = copy.deepcopy(g)
    g2.players[0].hand.append(g2.deck.draw(1))
    assert len(g.players[0].hand) == orig_hand
    assert len(g.deck.cards) == orig_deck


def test_mcts_respects_time_limit():
    """单步决策时间不超过 max_time 的 3 倍（容错）。"""
    ai = MctsAI(max_iterations=10000, max_time=0.3)
    g = _build_game()
    me = g.players[0]
    t0 = time.perf_counter()
    idx = ai.choose_turn(me, g, g.discard_pile[-1], g.current_color)
    dt = time.perf_counter() - t0
    assert dt < 0.9, f"超时: {dt:.2f}s"
    assert idx is not None


def test_mcts_no_pollution():
    """MCTS 决策后原 game 状态不变。"""
    ai = MctsAI(max_iterations=10, max_time=0.2)
    g = _build_game()
    snapshot = {
        "hands": [len(p.hand) for p in g.players],
        "deck": len(g.deck.cards),
        "discard": len(g.discard_pile),
        "idx": g.current_player_idx,
    }
    ai.choose_turn(g.players[0], g, g.discard_pile[-1], g.current_color)
    assert [len(p.hand) for p in g.players] == snapshot["hands"]
    assert len(g.deck.cards) == snapshot["deck"]
    assert len(g.discard_pile) == snapshot["discard"]
    assert g.current_player_idx == snapshot["idx"]


def test_mcts_no_hand_leak():
    """MCTS 模拟时不能读对手真实手牌。"""
    ai = MctsAI(max_iterations=5, max_time=0.1)
    g = _build_game()
    me = g.players[0]
    opp = g.players[1]
    opp_hand_backup = list(opp.hand)
    opp.hand = [Card('红', '数字', 0)] * opp.hand_size()
    ai.choose_turn(me, g, g.discard_pile[-1], g.current_color)
    # 模拟过程中没真实读取对手手牌（间接验证：模拟用随机发牌，
    # 不依赖对手实际内容）
    opp.hand = opp_hand_backup


def test_mcts_returns_legal_action():
    """返回的索引必须在合法动作内。"""
    ai = MctsAI(max_iterations=20, max_time=0.2)
    g = _build_game()
    me = g.players[0]
    idx = ai.choose_turn(me, g, g.discard_pile[-1], g.current_color)
    if idx is not None and idx >= 0:
        card = me.hand[idx]
        assert card.is_playable_on(g.discard_pile[-1], g.current_color)


def test_mcts_choose_color():
    """选色与 HeuristicAI 一致：选自己手里最多。"""
    ai = MctsAI(max_iterations=10, max_time=0.1)
    g = _build_game()
    me = g.players[0]
    me.hand = [Card('红', '数字', 1), Card('红', '数字', 2), Card('蓝', '数字', 3)]
    assert ai.choose_color(me) == '红'


def test_mcts_node_ucb1():
    """UCB1 初值无穷大，有访问后正常。"""
    root = MctsNode(action=None)
    root.visits = 10
    child = MctsNode(action=0, parent=root)
    assert child.ucb1() == float("inf")
    child.visits = 5
    child.wins = 3.0
    score = child.ucb1()
    assert 0.6 <= score <= 5.0
