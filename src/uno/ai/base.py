"""AI 策略抽象基类。"""
from abc import ABC, abstractmethod
from typing import Optional, List


class BaseAI(ABC):
    """所有 AI 策略的基类。

    设计说明：
    - choose_turn 是单一入口，内部可先发动技能再选牌，与现有 SimpleAI 行为一致。
      未来 HeuristicAI 可在自己内部拆分 choose_skill / choose_card。
    - choose_color 只处理 AI 选色逻辑；人类输入仍由 Player.choose_color 处理。
    - choose_skill 预留给未来主动选技能场景，默认返回 None（不发动）。
    """

    @abstractmethod
    def choose_turn(self, player, game, top_card, current_color) -> Optional[int]:
        """选择要出的牌的索引，返回 None 表示抽牌。"""
        pass

    @abstractmethod
    def choose_color(self, player) -> str:
        """打出万能牌时选择颜色，返回 Card.COLORS 中的一种。"""
        pass

    def choose_skill(self, player, game, available_skills) -> Optional[int]:
        """选择要发动的技能索引。默认不发动（返回 None）。"""
        return None
