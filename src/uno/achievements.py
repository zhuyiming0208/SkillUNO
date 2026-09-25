from abc import ABC, abstractmethod

class Achievement(ABC):
    def __init__(self, id: str, name: str, description: str, hidden: bool = False):
        self.id = id
        self.name = name
        self.description = description
        self.hidden = hidden

    @abstractmethod
    def check(self, game, events: list) -> bool:
        pass

    def __repr__(self):
        return f"{self.name}({self.id})"


class Comeback1v3Achievement(Achievement):
    def __init__(self):
        super().__init__('comeback_1v3', '一穿三', '在只剩自己一人的情况下逆转获胜')

    def check(self, game, events):
        human = game.players[0]
        if any(e['type'] == 'player_eliminated' and e['player'] == human.name for e in events):
            return False
        all_others_eliminated = all(
            any(e['type'] == 'player_eliminated' and e['player'] == p.name for e in events)
            for p in game.players if p != human
        )
        if not all_others_eliminated:
            return False
        if not any(e['type'] == 'game_end' and e.get('winner') == human.name for e in events):
            return False
        return True


class CounterMasterAchievement(Achievement):
    def __init__(self):
        super().__init__('counter_master', '反制大师', '单局成功反制 3 次以上')

    def check(self, game, events):
        counter_events = [
            e for e in events
            if e['type'] == 'skill_use' and e.get('skill_name') in ('破万法', '储能')
        ]
        return len(counter_events) >= 3


class InstantKillAchievement(Achievement):
    def __init__(self):
        super().__init__('instant_kill', '秒杀', '在对手起手阶段就使其手牌超过 15 张')

    def check(self, game, events):
        for e in events:
            if e['type'] == 'player_eliminated' and e.get('turn_number', 0) <= 2:
                if e.get('reason') == 'hand_limit':
                    return True
        return False


class NoDrawVictoryAchievement(Achievement):
    def __init__(self):
        super().__init__(
            'no_draw_victory',
            '被遗忘的战术',
            '你从未主动抽取过一张牌，仿佛早已预知一切。',
            hidden=True
        )

    def check(self, game, events):
        human = game.players[0]
        if not any(e['type'] == 'game_end' and e.get('winner') == human.name for e in events):
            return False
        draw_events = [e for e in events if e['type'] == 'draw_card' and e.get('player') == human.name]
        return len(draw_events) == 0


def get_core_achievements():
    """工厂函数：每次调用返回全新的成就类列表"""
    return [
        Comeback1v3Achievement,
        CounterMasterAchievement,
        InstantKillAchievement,
        NoDrawVictoryAchievement,
    ]


class AchievementManager:
    def __init__(self, game, achievement_classes):
        self.game = game
        self.achievements = [cls() for cls in achievement_classes]

    def add_achievements(self, achievement_classes):
        for cls in achievement_classes:
            self.achievements.append(cls())

    def evaluate(self, events):
        achieved = set()
        for ach in self.achievements:
            try:
                if ach.check(self.game, events):
                    achieved.add(ach.name)
            except Exception as e:
                print(f"[成就] 评估 {ach.name} 时出错：{e}")
        return achieved