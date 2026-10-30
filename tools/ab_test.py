"""A/B 对局：HeuristicAI vs SimpleAI。

用法：
    PYTHONPATH=src python tools/ab_test.py [局数]

设计：
- 4 名玩家全部 is_human=False，2 名 HeuristicAI + 2 名 SimpleAI。
- 不调用 UNOGame.run()（会卡人类输入、写存档）。
- 自己写回合循环，带回合上限防死循环。
- 以「首个剩 0 张手牌」为获胜，与 check_winner 一致。
"""
import os
import sys
import random

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from uno.core import UNOGame, NullUI
from uno.ai.simple import SimpleAI
from uno.ai.heuristic import HeuristicAI


MAX_TURNS = 1000


def _build_game(strategies):
    # players= 触发 hotseat，但随后全部 is_human=False 走 AI 分支
    game = UNOGame(
        debug=False,
        use_rich_ui=False,
        players=["A", "B", "C", "D"],
        enabled_seasons=["S1"],
    )
    game.ui = NullUI()
    # broadcast 遍历的是每个玩家的 p.ui，不是 game.ui
    for p, strat in zip(game.players, strategies):
        p.is_human = False
        p.ui = NullUI()
        p.ai_strategy = strat
    return game


def play_one(strategy_h, strategy_s, seed):
    random.seed(seed)
    h = HeuristicAI()
    s = SimpleAI()
    game = _build_game([h, s, h, s])

    try:
        game.setup()
    except Exception as e:
        return ("setup_error", str(e))

    game.current_player_idx = 0
    for turn in range(MAX_TURNS):
        winner = game.check_winner()
        if winner:
            tag = "H" if winner.ai_strategy is h else "S"
            return ("ok", tag)
        try:
            game.play_turn()
        except Exception as e:
            return ("play_error", f"turn={turn} {type(e).__name__}: {e}")
    return ("timeout", f">{MAX_TURNS} turns")


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 100
    stats = {"H": 0, "S": 0, "setup_error": 0, "play_error": 0, "timeout": 0}
    first_error = None

    for i in range(n):
        kind, val = play_one(HeuristicAI, SimpleAI, seed=i)
        if kind == "ok":
            stats[val] += 1
        else:
            stats[kind] += 1
            if first_error is None:
                first_error = (i, kind, val)

    total_ok = stats["H"] + stats["S"]
    print(f"\n=== A/B 结果（{n} 局）===")
    print(f"HeuristicAI 胜: {stats['H']}")
    print(f"SimpleAI   胜: {stats['S']}")
    if total_ok:
        print(f"H 胜率: {stats['H'] / total_ok * 100:.1f}%")
    print(f"setup_error: {stats['setup_error']}")
    print(f"play_error:  {stats['play_error']}")
    print(f"timeout:     {stats['timeout']}")
    if first_error:
        print(f"\n首个错误：局 {first_error[0]} / {first_error[1]} / {first_error[2]}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
