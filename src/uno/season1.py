from .core import Skill, SkillType, GameEvent
import random

SEASON_ID = "S1"
SEASON_NAME = "经典赛季"


class PoWanFa(Skill):
    def __init__(self, owner, game):
        super().__init__('破万法', SkillType.ACTIVE,
                         '破除任意技能效果',
                         '当有其他技能发动时，可以消耗此牌，使该技能无效并消耗。对【金身】的反制无效。',
                         owner, game, urgency_weight=55)

    def can_trigger(self, event, context):
        if self.is_consumed or self.is_deleted:
            return False
        return event == GameEvent.SKILL_ACTIVATED and context.get('activated_skill') is not None

    def activate(self, event, context):
        target_skill = context.get('activated_skill')
        if target_skill and target_skill.owner != self.owner:
            self.owner_print(f"{self.owner.name} 发动破万法，破除 {target_skill.name}！")
            target_skill.is_consumed = True
            context['cancel'] = True
            self.is_consumed = True
            return True
        return False


class QiaoWu(Skill):
    def __init__(self, owner, game):
        super().__init__('巧物', SkillType.ACTIVE,
                         '变成任意一张技能牌并立即发动',
                         '在自己回合主动使用，从可用技能池中选择一张技能复制并立刻触发其效果。可以复制巧物本身。',
                         owner, game, urgency_weight=50)

    def can_trigger(self, event, context):
        if self.is_consumed or self.is_deleted:
            return False
        return event == GameEvent.TURN_START

    def activate(self, event, context):
        available = [s for s in self.game.skill_pool if not s.is_consumed]
        if not available:
            self.owner_print("没有可用技能复制。")
            return False
        if self.owner.is_human:
            self.owner_print("可复制的技能：")
            for i, s in enumerate(available):
                self.owner_print(f"  {i}: {s.name}")
            choice = self.owner.ui.input("选择技能序号：").strip()
            try:
                idx = int(choice)
                if 0 <= idx < len(available):
                    chosen_cls = available[idx].__class__
                    temp_skill = chosen_cls(self.owner, self.game)
                    self.game.skill_manager.execute_skill(temp_skill, event, context)
                    self.is_consumed = True
                    return True
            except Exception:
                pass
        else:
            chosen_cls = random.choice(available).__class__
            temp_skill = chosen_cls(self.owner, self.game)
            self.game.skill_manager.execute_skill(temp_skill, event, context)
            self.is_consumed = True
            return True
        return False


class ShengShengBuXi(Skill):
    def __init__(self, owner, game):
        super().__init__('生生不息', SkillType.ACTIVE,
                         '死亡时复活，手牌上限永久变为25',
                         '当你因手牌上限淘汰时自动触发，复活并清除淘汰状态，手牌上限变为25，补5张手牌。可被破万法破除。',
                         owner, game)

    def can_trigger(self, event, context):
        if self.is_consumed or self.is_deleted:
            return False
        return event == GameEvent.PLAYER_DIED and context.get('player') == self.owner

    def activate(self, event, context):
        self.owner_print(f"{self.owner.name} 发动生生不息，复活并提升手牌上限至25！")
        self.owner.eliminated = False
        self.owner.hand_limit = 25
        self.owner.hand = self.game.deck.draw_many(5)
        self.is_consumed = True
        return True


class ChuNeng(Skill):
    def __init__(self, owner, game):
        super().__init__('储能', SkillType.ACTIVE,
                         '无效并夺取对方刚刚发动的技能',
                         '当其他玩家发动技能时，消耗此牌，使该技能无效并将其夺取到自己手中（技能重新可用）。',
                         owner, game, urgency_weight=55)

    def can_trigger(self, event, context):
        if self.is_consumed or self.is_deleted:
            return False
        return event == GameEvent.SKILL_ACTIVATED and context.get('activated_skill') is not None

    def activate(self, event, context):
        target_skill = context.get('activated_skill')
        if target_skill and target_skill.owner != self.owner:
            self.owner_print(f"{self.owner.name} 发动储能，夺取 {target_skill.name}！")
            target_skill.owner.skills.remove(target_skill)
            target_skill.owner = self.owner
            self.owner.skills.append(target_skill)
            target_skill.is_consumed = False
            context['cancel'] = True
            self.is_consumed = True
            return True
        return False


class QiangYun(Skill):
    def __init__(self, owner, game):
        super().__init__('强运', SkillType.ACTIVE,
                         '开局时使用，额外获得1~2张技能牌',
                         '游戏开始阶段自动使用，从技能池随机抽取1或2张技能加入手牌。',
                         owner, game)

    def can_trigger(self, event, context):
        if self.is_consumed or self.is_deleted:
            return False
        return event == GameEvent.GAME_START

    def activate(self, event, context):
        extra = random.randint(1, 2)
        self.owner_print(f"{self.owner.name} 发动强运，额外获得 {extra} 张技能牌。")
        for _ in range(extra):
            available = [s for s in self.game.skill_pool if not s.is_consumed and s.owner is None]
            if available:
                new_skill = random.choice(available)
                new_skill.owner = self.owner
                self.owner.skills.append(new_skill)
                self.game.skill_pool.remove(new_skill)
                self.owner_print(f"  获得 {new_skill.name}")
        self.is_consumed = True
        return True


class LiXi(Skill):
    def __init__(self, owner, game):
        super().__init__('离析', SkillType.ACTIVE,
                         '被加牌时使用，消除此次加牌效果',
                         '当你即将被加牌时（包括+2/+4/技能），消耗此牌，完全抵消此次加牌。',
                         owner, game, urgency_weight=50)

    def can_trigger(self, event, context):
        if self.is_consumed or self.is_deleted:
            return False
        return event == GameEvent.BEING_ADDED_CARDS and context.get('target') == self.owner

    def activate(self, event, context):
        self.owner_print(f"{self.owner.name} 发动离析，消除加牌效果！")
        context['cancel'] = True
        self.is_consumed = True
        return True

    def evaluate_urgency(self, game):
        return 80 if self.owner.hand_size() >= 10 else 50


class HuaXing(Skill):
    def __init__(self, owner, game):
        super().__init__('化形', SkillType.ACTIVE,
                         '与一名玩家交换全部手牌，或交换全部技能',
                         '在自己回合使用，选择一名玩家，随机决定交换手牌或技能（人类可选）。交换后技能所有权转移。',
                         owner, game, urgency_weight=45)

    def can_trigger(self, event, context):
        if self.is_consumed or self.is_deleted:
            return False
        return event == GameEvent.TURN_START

    def evaluate_urgency(self, game):
        if self.owner.hand_size() >= 12:
            return 20
        if self.owner.hand_size() <= 4:
            return 70
        return 45

    def activate(self, event, context):
        target = self.choose_target()
        if target:
            mode = '手牌' if random.choice([True, False]) else '技能'
            if self.owner.is_human:
                ans = self.owner.ui.input("交换手牌(1)还是技能(2)？").strip()
                mode = '手牌' if ans == '1' else '技能'
            if mode == '手牌':
                self.owner.hand, target.hand = target.hand, self.owner.hand
                self.owner_print(f"{self.owner.name} 与 {target.name} 交换了手牌！")
            else:
                self.owner.skills, target.skills = target.skills, self.owner.skills
                for s in self.owner.skills:
                    s.owner = self.owner
                for s in target.skills:
                    s.owner = target
                self.owner_print(f"{self.owner.name} 与 {target.name} 交换了技能！")
            self.is_consumed = True
            return True
        return False

    def choose_target(self):
        active = [p for p in self.game.players if p != self.owner and not p.eliminated]
        if not active:
            return None
        if self.owner.is_human:
            self.owner_print("选择目标玩家：")
            for i, p in enumerate(active):
                self.owner_print(f"  {i}: {p.name}")
            choice = self.owner.ui.input("序号：").strip()
            try:
                idx = int(choice)
                if 0 <= idx < len(active):
                    return active[idx]
            except Exception:
                pass
            return None
        return random.choice(active)


class HuoShui(Skill):
    def __init__(self, owner, game):
        super().__init__('祸水', SkillType.ACTIVE,
                         '自己被加牌时使用，指定另一人代替承受',
                         '当你即将被加牌时，消耗此牌，将加牌效果转移给另一名玩家。',
                         owner, game, urgency_weight=50)

    def can_trigger(self, event, context):
        if self.is_consumed or self.is_deleted:
            return False
        return event == GameEvent.BEING_ADDED_CARDS and context.get('target') == self.owner

    def evaluate_urgency(self, game):
        return 80 if self.owner.hand_size() >= 10 else 50

    def activate(self, event, context):
        target = self.choose_target()
        if target:
            self.owner_print(f"{self.owner.name} 发动祸水，将加牌转移给 {target.name}！")
            context['target'] = target
            self.is_consumed = True
            return True
        return False

    def choose_target(self):
        active = [p for p in self.game.players if p != self.owner and not p.eliminated]
        if not active:
            return None
        if self.owner.is_human:
            self.owner_print("选择祸水目标：")
            for i, p in enumerate(active):
                self.owner_print(f"  {i}: {p.name}")
            choice = self.owner.ui.input("序号：").strip()
            try:
                idx = int(choice)
                if 0 <= idx < len(active):
                    return active[idx]
            except Exception:
                pass
            return None
        return random.choice(active)


class BuMie(Skill):
    def __init__(self, owner, game):
        super().__init__('不灭', SkillType.DEATH,
                         '死亡时复活，手牌弃至10张，并丢弃1张技能牌',
                         '当你因手牌上限淘汰时自动触发，复活并保留最多10张手牌，然后随机丢弃一张其他技能。',
                         owner, game)

    def can_trigger(self, event, context):
        if self.is_consumed or self.is_deleted:
            return False
        return event == GameEvent.PLAYER_DIED and context.get('player') == self.owner

    def activate(self, event, context):
        self.owner_print(f"{self.owner.name} 触发不灭，复活！")
        self.owner.eliminated = False
        while len(self.owner.hand) > 10:
            self.owner.hand.pop()
        other_skills = [s for s in self.owner.skills if s != self]
        if other_skills:
            discarded = random.choice(other_skills)
            self.owner.skills.remove(discarded)
            self.owner_print(f"  丢弃了技能 {discarded.name}")
        self.is_consumed = True
        return True


class WuJianDao(Skill):
    def __init__(self, owner, game):
        super().__init__('无间道', SkillType.ACTIVE,
                         '绑定一名玩家，持续3回合。对方加牌时，你减等量牌',
                         '在自己回合使用，绑定目标。之后每当目标加牌，你从手牌中移除等量牌（至少移除至0）。持续3个加牌事件后自动结束。',
                         owner, game, urgency_weight=50)
        self.bound_target = None
        self.times_left = 0

    def can_trigger(self, event, context):
        if self.is_consumed or self.is_deleted:
            return False
        if event == GameEvent.TURN_START and self.bound_target is None:
            return True
        elif event == GameEvent.CARDS_ADDED and self.bound_target and context.get('target') == self.bound_target:
            return True
        return False

    def activate(self, event, context):
        if event == GameEvent.TURN_START:
            target = self.choose_target()
            if target:
                self.bound_target = target
                self.times_left = 3
                self.owner_print(f"{self.owner.name} 对 {target.name} 发动无间道，绑定3次加牌效果。")
                return True
        elif event == GameEvent.CARDS_ADDED and self.bound_target:
            amount = context.get('amount', 0)
            removed = min(amount, len(self.owner.hand))
            if removed > 0:
                del self.owner.hand[-removed:]
                self.owner_print(f"无间道：{self.owner.name} 减少 {removed} 张手牌。")
            self.times_left -= 1
            if self.times_left <= 0:
                self.bound_target = None
                self.is_consumed = True
                self.owner_print(f"{self.owner.name} 的无间道效果结束。")
            return False
        return False

    def choose_target(self):
        active = [p for p in self.game.players if p != self.owner and not p.eliminated]
        if not active:
            return None
        if self.owner.is_human:
            self.owner_print("选择无间道目标：")
            for i, p in enumerate(active):
                self.owner_print(f"  {i}: {p.name}")
            choice = self.owner.ui.input("序号：").strip()
            try:
                idx = int(choice)
                if 0 <= idx < len(active):
                    return active[idx]
            except Exception:
                pass
            return None
        return random.choice(active)


class DuXin(Skill):
    def __init__(self, owner, game):
        super().__init__('读心', SkillType.ACTIVE,
                         '查看一名玩家的手牌，或其全部技能',
                         '在自己回合使用，选择一名玩家，查看其手牌或技能列表（人类可选）。',
                         owner, game, urgency_weight=40)

    def can_trigger(self, event, context):
        if self.is_consumed or self.is_deleted:
            return False
        return event == GameEvent.TURN_START

    def activate(self, event, context):
        target = self.choose_target()
        if target:
            mode = '手牌' if random.choice([True, False]) else '技能'
            if self.owner.is_human:
                ans = self.owner.ui.input("查看手牌(1)还是技能(2)？").strip()
                mode = '手牌' if ans == '1' else '技能'
            if mode == '手牌':
                self.owner_print(f"{target.name} 的手牌：{target.show_hand()}")
            else:
                visible = [s for s in target.skills if not s.is_deleted]
                self.owner_print(f"{target.name} 的技能：{[s.name for s in visible]}")
            self.is_consumed = True
            return True
        return False

    def choose_target(self):
        active = [p for p in self.game.players if p != self.owner and not p.eliminated]
        if not active:
            return None
        if self.owner.is_human:
            self.owner_print("选择读心目标：")
            for i, p in enumerate(active):
                self.owner_print(f"  {i}: {p.name}")
            choice = self.owner.ui.input("序号：").strip()
            try:
                idx = int(choice)
                if 0 <= idx < len(active):
                    return active[idx]
            except Exception:
                pass
            return None
        return random.choice(active)


class DianRen(Skill):
    def __init__(self, owner, game):
        super().__init__('癫人', SkillType.DEATH,
                         '获得场上所有死亡玩家的技能',
                         '当你因手牌上限淘汰时自动触发，获取所有已被淘汰玩家拥有的、未被消耗且未删除的技能。',
                         owner, game)

    def can_trigger(self, event, context):
        if self.is_consumed or self.is_deleted:
            return False
        return event == GameEvent.PLAYER_DIED and context.get('player') == self.owner

    def activate(self, event, context):
        dead_skills = []
        for p in self.game.players:
            if p.eliminated:
                dead_skills.extend([s for s in p.skills if not s.is_consumed and not s.is_deleted])
        if dead_skills:
            self.owner_print(f"{self.owner.name} 发动癫人，获得死者技能：{[s.name for s in dead_skills]}")
            for s in dead_skills:
                s.owner = self.owner
                self.owner.skills.append(s)
        self.is_consumed = True
        return True


class ZhaoZai(Skill):
    def __init__(self, owner, game):
        super().__init__('招灾', SkillType.ACTIVE,
                         '转盘指到谁，谁加5张牌',
                         '在自己回合使用，随机指定一名存活玩家（包括自己），使其加5张牌。',
                         owner, game, urgency_weight=40)

    def can_trigger(self, event, context):
        if self.is_consumed or self.is_deleted:
            return False
        return event == GameEvent.TURN_START

    def evaluate_urgency(self, game):
        for p in game.players:
            if p != self.owner and not p.eliminated and p.hand_size() <= 2:
                return 90
        return 40

    def activate(self, event, context):
        active = [p for p in self.game.players if not p.eliminated]
        if not active:
            return False
        random_ctx = {
            'source_skill': self,
            'player': self.owner,
            'choices': active,
            'result': None,
            'retry': False
        }
        self.game.skill_manager.trigger(GameEvent.START_RANDOM, random_ctx)
        target = random.choice(active)
        if random_ctx.get('retry'):
            self.owner_print("双生花被动触发，重掷转盘！")
            target = random.choice(active)
        random_ctx['result'] = target
        self.game.skill_manager.trigger(GameEvent.END_RANDOM, random_ctx)
        self.owner_print(f"招灾转盘指向 {target.name}，加5张牌！")
        self.game.apply_add_cards(target, 5)
        self.is_consumed = True
        return True


class JingLei(Skill):
    def __init__(self, owner, game):
        super().__init__('惊雷', SkillType.ACTIVE,
                         '投骰子，点数≥5无惩罚；否则自己加5张（所有人依次投掷）',
                         '在自己回合使用，所有存活玩家依次投掷六面骰。点数≥5则无事发生；点数<5则该玩家加5张牌。',
                         owner, game, urgency_weight=0)

    def can_trigger(self, event, context):
        if self.is_consumed or self.is_deleted:
            return False
        return event == GameEvent.TURN_START

    def evaluate_urgency(self, game):
        if self.owner.hand_size() >= 12:
            return 10
        if self.owner.hand_size() <= 3:
            return 40
        return 0

    def activate(self, event, context):
        self.owner_print(f"{self.owner.name} 发动惊雷！所有玩家开始投骰子判定。")
        for p in self.game.players:
            if p.eliminated:
                continue
            random_ctx = {
                'source_skill': self,
                'player': p,
                'dice': True,
                'result': None,
                'retry': False
            }
            self.game.skill_manager.trigger(GameEvent.START_RANDOM, random_ctx)
            dice = random.randint(1, 6)
            if random_ctx.get('retry'):
                self.owner_print(f"双生花被动触发，{p.name} 重掷骰子！")
                dice = random.randint(1, 6)
            random_ctx['result'] = dice
            self.game.skill_manager.trigger(GameEvent.END_RANDOM, random_ctx)
            self.owner_print(f"  {p.name} 掷出 {dice} 点", )
            if dice >= 5:
                self.owner_print("，免受惩罚。")
            else:
                self.owner_print(f"，受到惩罚，加5张牌！")
                self.game.apply_add_cards(p, 5)
        self.is_consumed = True
        return True


class NongYan(Skill):
    def __init__(self, owner, game):
        super().__init__('浓烟', SkillType.ACTIVE,
                         '开局使用，挑选其他玩家各隐藏一个技能',
                         '游戏开始时自动发动，从其他每位玩家技能中随机隐藏一个（技能变为不可见不可用，相当于删除）。',
                         owner, game)

    def can_trigger(self, event, context):
        if self.is_consumed or self.is_deleted:
            return False
        return event == GameEvent.GAME_START

    def activate(self, event, context):
        targets = [p for p in self.game.players if p != self.owner]
        for t in targets:
            available = [s for s in t.skills if not s.is_deleted]
            if available:
                hidden = random.choice(available)
                hidden.is_deleted = True
                self.owner_print(f"浓烟：{t.name} 的一个技能被隐藏。")
        self.is_consumed = True
        return True


SKILL_CLASSES = [
    PoWanFa, QiaoWu, ShengShengBuXi, ChuNeng, QiangYun,
    LiXi, HuaXing, HuoShui, BuMie, WuJianDao,
    DuXin, DianRen, ZhaoZai, JingLei, NongYan
]