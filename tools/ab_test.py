"""A/B 对局工具。

用法：
    PYTHONPATH=src python tools/ab_test.py [局数] [模式]

模式（可选）：
    hs   HeuristicAI vs SimpleAI（默认）
    mh   MctsAI vs HeuristicAI

示例：
    PYTHONPATH=src python tools/ab_test.py 100 hs
    PYTHONPATH=src python tools/ab_test.py 20 mh

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
from uno.ai.mcts import MctsAI


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


def play_one(mode, seed):
    random.seed(seed)
    if mode == "mh":
        a = MctsAI(max_iterations=100, max_time=1.0, verbose=True)
        b = HeuristicAI()
        tag_a, tag_b = "M", "H"
        game = _build_game([a, b, a, b])
    elif mode == "m3":
        # 1 MCTS vs 3 Heuristic，检验单挑能力
        a = MctsAI(max_iterations=100, max_time=1.0, verbose=True)
        b = HeuristicAI()
        tag_a, tag_b = "M", "H"
        game = _build_game([a, b, b, b])
    else:  # hs
        a = HeuristicAI()
        b = SimpleAI()
        tag_a, tag_b = "H", "S"
        game = _build_game([a, b, a, b])

    try:
        game.setup()
    except Exception as e:
        return ("setup_error", str(e))

    print(f"  [新局] seed={seed}", flush=True)
    game.current_player_idx = 0
    for turn in range(MAX_TURNS):
        winner = game.check_winner()
        if winner:
            tag = tag_a if winner.ai_strategy is a else tag_b
            print(f"  [局结束] turn={turn}, winner={winner.name}({tag})", flush=True)
            return ("ok", tag)
        try:
            game.play_turn()
        except Exception as e:
            return ("play_error", f"turn={turn} {type(e).__name__}: {e}")
    return ("timeout", f">{MAX_TURNS} turns")


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 100
    mode = sys.argv[2] if len(sys.argv) > 2 else "m3"
    if mode not in ("hs", "mh", "m3"):
        print(f"未知模式: {mode}，可选 hs / mh / m3")
        return 2

    if mode in ("mh", "m3"):
        stats = {"M": 0, "H": 0, "setup_error": 0, "play_error": 0, "timeout": 0}
        label_a, label_b = "MctsAI", "HeuristicAI"
    else:
        stats = {"H": 0, "S": 0, "setup_error": 0, "play_error": 0, "timeout": 0}
        label_a, label_b = "HeuristicAI", "SimpleAI"

    tag_a, tag_b = ("M", "H") if mode in ("mh", "m3") else ("H", "S")
    first_error = None
    import time
    t0 = time.perf_counter()

    for i in range(n):
        kind, val = play_one(mode, seed=i)
        if kind == "ok":
            stats[val] += 1
        else:
            stats[kind] += 1
            if first_error is None:
                first_error = (i, kind, val)
        if (i + 1) % 5 == 0 or i + 1 == n:
            elapsed = time.perf_counter() - t0
            print(f"  [进度] {i+1}/{n}，已耗时 {elapsed:.0f}s", flush=True)

    total_ok = stats[tag_a] + stats[tag_b]
    elapsed = time.perf_counter() - t0
    print(f"\n=== A/B 结果（{n} 局，模式={mode}）===")
    print(f"{label_a} 胜: {stats[tag_a]}")
    print(f"{label_b} 胜: {stats[tag_b]}")
    if total_ok:
        print(f"{label_a[0]} 胜率: {stats[tag_a] / total_ok * 100:.1f}%")
    print(f"总耗时: {elapsed:.1f}s（{elapsed/n:.1f}s/局）")
    print(f"setup_error: {stats['setup_error']}")
    print(f"play_error:  {stats['play_error']}")
    print(f"timeout:     {stats['timeout']}")
    if first_error:
        print(f"\n首个错误：局 {first_error[0]} / {first_error[1]} / {first_error[2]}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
