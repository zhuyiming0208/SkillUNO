"""默认 AI 策略：先按紧迫度发动技能，再选第一张可出的牌。"""
from typing import Optional

from uno.core import SkillType, GameEvent, Card
from uno.ai.base import BaseAI


class SimpleAI(BaseAI):
    """当前默认 AI，行为与原 Player.ai_choose / choose_color 完全一致。"""

    def choose_turn(self, player, game, top_card, current_color) -> Optional[int]:
        usable = [s for s in player.skills if not s.is_consumed and not s.is_deleted
                  and s.type in (SkillType.ACTIVE, SkillType.HYBRID)
                  and s.can_trigger(GameEvent.TURN_START, {'player': player})]
        if usable:
            best_skill = max(usable, key=lambda s: s.evaluate_urgency(game))
            if best_skill.evaluate_urgency(game) > 20:
                game.skill_manager.execute_skill(best_skill, GameEvent.TURN_START, {'player': player})
                if len(player.hand) == 0:
                    return None
        for i, card in enumerate(player.hand):
            if card.is_playable_on(top_card, current_color):
                return i
        return None

    def choose_color(self, player) -> str:
        color_count = {c: 0 for c in Card.COLORS}
        for card in player.hand:
            if card.color in color_count:
                color_count[card.color] += 1
        best = max(color_count, key=color_count.get)
        return best
