"""启发式 AI：留底牌、卡下家、聪明选色。"""
from typing import Optional

from uno.core import SkillType, GameEvent, Card
from uno.ai.base import BaseAI


class HeuristicAI(BaseAI):
    """二档 AI。规则基于手牌、下家手牌数、牌型价值综合评分。"""

    KILL_ZONE_THRESHOLD = 2

    def choose_turn(self, player, game, top_card, current_color) -> Optional[int]:
        self._maybe_use_skill(player, game)
        if len(player.hand) == 0:
            return None

        playable = [
            (i, card) for i, card in enumerate(player.hand)
            if card.is_playable_on(top_card, current_color)
        ]
        if not playable:
            return None

        nxt = game.peek_next_player()
        next_hand = nxt.hand_size() if nxt else 99
        is_kill_zone = next_hand <= self.KILL_ZONE_THRESHOLD

        best_idx = playable[0][0]
        best_score = float("-inf")
        for i, card in playable:
            score = self._score_card(card, player, is_kill_zone)
            if score > best_score:
                best_score = score
                best_idx = i
        return best_idx

    def _score_card(self, card, player, is_kill_zone) -> float:
        score = 0.0
        t = card.type

        if is_kill_zone:
            if t in ("+2", "万能+4"):
                score += 100
            elif t == "跳过":
                score += 90
            elif t == "反转":
                score += 80
        else:
            if t == "万能+4":
                score -= 50
            elif t == "+2":
                score -= 20

        if card.color != "黑":
            same_color = sum(1 for c in player.hand if c.color == card.color)
            score += same_color * 10

        if t == "数字" and card.value is not None:
            score += card.value

        if len(player.hand) == 2 and t == "万能+4":
            score -= 30

        return score

    def _maybe_use_skill(self, player, game) -> None:
        if len(player.hand) <= 2:
            return
        usable = [
            s for s in player.skills
            if not s.is_consumed and not s.is_deleted
            and s.type in (SkillType.ACTIVE, SkillType.HYBRID)
            and s.can_trigger(GameEvent.TURN_START, {"player": player})
        ]
        if not usable:
            return

        nxt = game.peek_next_player()
        next_hand = nxt.hand_size() if nxt else 99
        if next_hand <= self.KILL_ZONE_THRESHOLD:
            best = max(usable, key=lambda s: s.evaluate_urgency(game))
            game.skill_manager.execute_skill(
                best, GameEvent.TURN_START, {"player": player})
            return

        best = max(usable, key=lambda s: s.evaluate_urgency(game))
        if best.evaluate_urgency(game) > 20:
            game.skill_manager.execute_skill(
                best, GameEvent.TURN_START, {"player": player})

    def choose_color(self, player) -> str:
        color_count = {c: 0 for c in Card.COLORS}
        for card in player.hand:
            if card.color in color_count:
                color_count[card.color] += 1
        return max(color_count, key=color_count.get)
