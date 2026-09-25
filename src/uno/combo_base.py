from abc import ABC, abstractmethod

class ComboBase(ABC):
    @abstractmethod
    def execute(self, player, skill_manager, game):
        """执行组合技效果"""
        pass