"""三档 AI：蒙特卡洛树搜索（MCTS）。

设计要点：
- 状态隔离：每次 rollout 用 deepcopy 拷贝游戏，不污染真实 game
- POMDP：对手手牌只读数量，模拟时从未知牌池随机发牌
- Rollout 策略：强制使用 HeuristicAI（不读 player.ai_strategy），防递归
- 时间/迭代双上限，保证单步决策可控
"""
import copy
import math
import random
import time
from typing import List, Optional, Tuple

from uno.core import NullUI, Card
from uno.ai.base import BaseAI
from uno.ai.heuristic import HeuristicAI


class MctsNode:
    def __init__(self, action, parent=None):
        self.action = action
        self.parent = parent
        self.children: List["MctsNode"] = []
        self.visits = 0
        self.wins = 0.0
        self.untried_actions: List = []

    def is_fully_expanded(self):
        return not self.untried_actions

    def ucb1(self, c=1.414):
        if self.visits == 0:
            return float("inf")
        return self.wins / self.visits + c * math.sqrt(
            math.log(self.parent.visits) / self.visits)


class MctsAI(BaseAI):
    def __init__(self, max_iterations: int = 100, max_time: float = 1.0,
                 verbose: bool = False):
        self.max_iterations = max_iterations
        self.max_time = max_time
        self.verbose = verbose
        self._rollout_ai = HeuristicAI()

    # ---- 主入口 ----
    def choose_turn(self, player, game, top_card, current_color) -> Optional[int]:
        actions = self._legal_actions(player, game, top_card, current_color)
        if not actions:
            return None
        if len(actions) == 1:
            return actions[0]

        root = MctsNode(action=None)
        root.untried_actions = list(actions)
        t_start = time.perf_counter()
        deadline = t_start + self.max_time
        iterations_done = 0

        for _ in range(self.max_iterations):
            if time.perf_counter() >= deadline:
                break
            node_game = self._clone_for_sim(player, game)
            node = self._select(root, node_game, player.name)
            if node.untried_actions:
                node = self._expand(node, node_game, player.name)
            result = self._simulate(node_game, player)
            self._backpropagate(node, result)
            iterations_done += 1

        if self.verbose:
            dt = (time.perf_counter() - t_start) * 1000
            print(f"    [MCTS] {player.name}: {iterations_done} iters, "
                  f"{dt:.0f}ms, action={max(root.children, key=lambda n: n.visits).action if root.children else '?'}",
                  flush=True)

        if not root.children:
            return actions[0]
        best = max(root.children, key=lambda n: n.visits)
        return best.action

    def choose_color(self, player) -> str:
        color_count = {c: 0 for c in Card.COLORS}
        for card in player.hand:
            if card.color in color_count:
                color_count[card.color] += 1
        return max(color_count, key=color_count.get)

    # ---- 合法动作 ----
    def _legal_actions(self, player, game, top_card, current_color) -> List[int]:
        legal = [i for i, c in enumerate(player.hand)
                 if c.is_playable_on(top_card, current_color)]
        legal.append(-1)  # -1 表示抽牌
        return legal

    # ---- 状态克隆（POMDP）----
    def _clone_for_sim(self, me, game):
        g = copy.deepcopy(game)
        g.ui = NullUI()
        if hasattr(g, "deck") and g.deck is not None:
            g.deck.ui = NullUI()
        unknown_pool = self._build_unknown_pool(game, me)
        me_name = me.name
        for p in g.players:
            p.ui = NullUI()
            p.is_human = False
            # 关键：强制用轻量 rollout AI，防递归（对手也可能是 MctsAI）
            p.ai_strategy = self._rollout_ai
            if p.name != me_name:
                p.hand = self._deal_random(unknown_pool, p.hand_size())
        return g

    def _build_unknown_pool(self, game, me) -> List[Card]:
        seen = set(id(c) for c in me.hand)
        seen.update(id(c) for c in game.discard_pile)
        pool = []
        for c in game.deck.cards:
            if id(c) not in seen:
                pool.append(copy.deepcopy(c))
        return pool

    def _deal_random(self, pool, n):
        if not pool:
            return []
        n = min(n, len(pool))
        cards = random.sample(pool, n)
        for c in cards:
            pool.remove(c)
        return cards

    # ---- MCTS 四阶段 ----
    def _select(self, node, game, me_name):
        while not node.untried_actions and node.children:
            node = max(node.children, key=lambda n: n.ucb1())
        return node

    def _expand(self, node, game, me_name):
        action = node.untried_actions.pop(random.randrange(len(node.untried_actions)))
        child = MctsNode(action=action, parent=node)
        node.children.append(child)
        self._apply_action(game, child.action, me_name)
        return child

    def _simulate(self, game, me) -> float:
        me_name = me.name
        me_in_sim = next((p for p in game.players if p.name == me_name), None)
        if me_in_sim is None:
            return 0.0
        hard_deadline = time.perf_counter() + self.max_time
        for _ in range(200):
            if time.perf_counter() > hard_deadline:
                return 0.5
            winner = game.check_winner()
            if winner:
                return 1.0 if winner.name == me_name else 0.0
            if game.players[game.current_player_idx].name == me_name:
                idx = self._rollout_ai.choose_turn(
                    me_in_sim, game,
                    game.discard_pile[-1], game.current_color)
                self._apply_play(game, idx)
            else:
                game.play_turn()
        return 0.5

    def _backpropagate(self, node, result):
        while node is not None:
            node.visits += 1
            node.wins += result
            node = node.parent

    # ---- 状态操作 ----
    def _apply_action(self, game, action, me_name):
        me = next((p for p in game.players if p.name == me_name), None)
        if me is None:
            return
        if action == -1:
            from uno.core import GameEvent
            drawn = game.deck.draw(1)
            me.hand.append(drawn)
            if me.hand_size() > me.hand_limit:
                me.eliminate(game)
                game.skill_manager.trigger(GameEvent.PLAYER_DIED, {'player': me})
                return
            game.next_player()
        else:
            card = me.hand.pop(action)
            game.discard_pile.append(card)
            if card.type not in ('万能', '万能+4'):
                game.current_color = card.color
            skip = game.apply_card_effect(me, card)
            game.next_player(2 if skip else 1)

    def _apply_play(self, game, idx):
        cur = game.players[game.current_player_idx]
        if idx is None or idx < 0:
            from uno.core import GameEvent
            drawn = game.deck.draw(1)
            cur.hand.append(drawn)
            if cur.hand_size() > cur.hand_limit:
                cur.eliminate(game)
                game.skill_manager.trigger(GameEvent.PLAYER_DIED, {'player': cur})
                return
            game.next_player()
        else:
            card = cur.hand.pop(idx)
            game.discard_pile.append(card)
            if card.type not in ('万能', '万能+4'):
                game.current_color = card.color
            skip = game.apply_card_effect(cur, card)
            game.next_player(2 if skip else 1)
