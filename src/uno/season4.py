from .core import Skill, SkillType, GameEvent
import random

SEASON_ID = "S4"
SEASON_NAME = "补丁赛季"


class YanPin(Skill):
    def __init__(self, owner, game):
        super().__init__('赝品', SkillType.ACTIVE,
                         '将一张 UNO 牌变成想要的颜色或数字',
                         '在自己回合使用，选择手牌中的一张牌，将其改为指定颜色和/或数字。万能牌也可被改变。',
                         owner, game, urgency_weight=40)

    def can_trigger(self, event, context):
        if self.is_consumed or self.is_deleted:
            return False
        return event == GameEvent.TURN_START and context.get('player') == self.owner

    def activate(self, event, context):
        if not self.owner.hand:
            self.owner_print("赝品：无手牌可改。")
            return False
        if self.owner.is_human:
            self.owner_print("选择要改变的手牌：")
            for i, c in enumerate(self.owner.hand):
                self.owner_print(f"  {i}: {c}")
            try:
                idx = int(self.owner.ui.input("序号: ").strip())
                card = self.owner.hand[idx]
                new_color = self.owner.ui.input("新颜色 (红/蓝/绿/黄，回车保持不变): ").strip()
                new_value = self.owner.ui.input("新数字 (0-9，仅数字牌有效，回车保持): ").strip()
                if new_color in ['红', '蓝', '绿', '黄']:
                    card.color = new_color
                if new_value.isdigit() and 0 <= int(new_value) <= 9 and card.type == '数字':
                    card.value = int(new_value)
                self.owner_print(f"赝品：牌变为 {card}")
                self.is_consumed = True
                return True
            except Exception:
                pass
        else:
            card = random.choice(self.owner.hand)
            if card.type == '数字':
                card.color = random.choice(['红', '蓝', '绿', '黄'])
                card.value = random.randint(0, 9)
            else:
                card.color = random.choice(['红', '蓝', '绿', '黄'])
            self.owner_print(f"{self.owner.name} 使用赝品改变了手牌。")
            self.is_consumed = True
            return True
        return False


class TanNang(Skill):
    def __init__(self, owner, game):
        super().__init__('探囊', SkillType.ACTIVE,
                         '声明一张牌并指定一人，对方有则必须交给你',
                         '在自己回合使用，指定一名玩家和一张牌，如果对方有则交给使用。',
                         owner, game, urgency_weight=55)

    def can_trigger(self, event, context):
        if self.is_consumed or self.is_deleted:
            return False
        return event == GameEvent.TURN_START and context.get('player') == self.owner

    def evaluate_urgency(self, game):
        for p in game.players:
            if p != self.owner and not p.eliminated and p.hand_size() <= 2:
                return 75
        return 55

    def activate(self, event, context):
        target = self._choose_target()
        if not target:
            return False
        if self.owner.is_human:
            self.owner_print("声明要夺取的牌，例如：红5、蓝跳过、万能等")
            s = self.owner.ui.input("牌名: ").strip()
            card = self._parse_card(s)
            if card:
                for i, c in enumerate(target.hand):
                    if c.color == card.color and c.type == card.type and (c.type != '数字' or c.value == card.value):
                        target.hand.pop(i)
                        self.owner.hand.append(c)
                        self.owner_print(f"探囊成功，从 {target.name} 获得 {c}！")
                        self.is_consumed = True
                        return True
                self.owner_print(f"{target.name} 没有这张牌。")
        else:
            if target.hand:
                card = random.choice(target.hand)
                target.hand.remove(card)
                self.owner.hand.append(card)
                self.owner_print(f"{self.owner.name} 用探囊从 {target.name} 夺走一张牌。")
                self.is_consumed = True
                return True
        return False

    def _choose_target(self):
        active = [p for p in self.game.players if p != self.owner and not p.eliminated]
        if not active:
            return None
        if self.owner.is_human:
            self.owner_print("选择探囊目标：")
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

    def _parse_card(self, s):
        from .core import Card
        s = s.strip()
        if '万能+4' in s:
            return Card('黑', '万能+4')
        if '万能' in s:
            return Card('黑', '万能')
        for col in Card.COLORS:
            if s.startswith(col):
                rest = s[len(col):]
                if rest in ['跳过', '反转', '+2']:
                    return Card(col, rest)
                if rest.isdigit():
                    return Card(col, '数字', int(rest))
        return None


class XianLing(Skill):
    def __init__(self, owner, game):
        super().__init__('显灵', SkillType.ACTIVE,
                         '指定一种牌，知晓其他所有玩家手中该牌的总数',
                         '在自己回合使用，指定一张牌，系统会告知其他玩家手牌中该牌的总数。',
                         owner, game, urgency_weight=35)

    def can_trigger(self, event, context):
        if self.is_consumed or self.is_deleted:
            return False
        return event == GameEvent.TURN_START and context.get('player') == self.owner

    def activate(self, event, context):
        from .core import Card
        if self.owner.is_human:
            s = self.owner.ui.input("显灵：请输入要查询的牌（如红5、蓝跳过）: ").strip()
            target_card = None
            for col in Card.COLORS:
                if s.startswith(col):
                    rest = s[len(col):]
                    if rest.isdigit():
                        target_card = Card(col, '数字', int(rest))
                    elif rest in ['跳过', '反转', '+2']:
                        target_card = Card(col, rest)
                    break
            if target_card is None:
                self.owner_print("输入格式错误")
                return False
            count = 0
            for p in self.game.players:
                if p != self.owner and not p.eliminated:
                    for c in p.hand:
                        if c.color == target_card.color and c.type == target_card.type and (c.type != '数字' or c.value == target_card.value):
                            count += 1
            self.owner_print(f"显灵：其他玩家手中共有 {count} 张 {target_card}。")
        else:
            target_card = Card(random.choice(Card.COLORS), '数字', random.randint(0, 9))
            count = 0
            for p in self.game.players:
                if p != self.owner and not p.eliminated:
                    count += sum(1 for c in p.hand if c.color == target_card.color and c.type == '数字' and c.value == target_card.value)
            self.owner_print(f"{self.owner.name} 使用显灵，发现 {target_card} 共 {count} 张。")
        self.is_consumed = True
        return True


class JiaHuo(Skill):
    def __init__(self, owner, game):
        super().__init__('嫁祸', SkillType.ACTIVE,
                         '被技能攻击时，将该效果转移给另一人',
                         '当你被某个技能效果指定为目标时，消耗此牌，将效果转移给另一名玩家。',
                         owner, game, urgency_weight=60)

    def can_trigger(self, event, context):
        if self.is_consumed or self.is_deleted:
            return False
        if event == GameEvent.SKILL_ACTIVATED:
            orig = context.get('original_context', {})
            if orig.get('target') == self.owner:
                return True
        return False

    def activate(self, event, context):
        if event == GameEvent.SKILL_ACTIVATED:
            target = self._choose_target()
            if target:
                orig = context.get('original_context')
                self.owner_print(f"{self.owner.name} 发动嫁祸，将效果转移给 {target.name}！")
                orig['target'] = target
                self.is_consumed = True
                return True
        return False

    def _choose_target(self):
        active = [p for p in self.game.players if p != self.owner and not p.eliminated]
        if not active:
            return None
        if self.owner.is_human:
            self.owner_print("选择嫁祸目标：")
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


class JiFa(Skill):
    def __init__(self, owner, game):
        super().__init__('激发', SkillType.ACTIVE,
                         '所有玩家重抽技能。你从9张中选3张，他人随机3张',
                         '在自己回合使用，所有玩家弃掉当前全部技能，重新分配。',
                         owner, game, urgency_weight=30)

    def can_trigger(self, event, context):
        if self.is_consumed or self.is_deleted:
            return False
        return event == GameEvent.TURN_START and context.get('player') == self.owner

    def evaluate_urgency(self, game):
        return 30

    def activate(self, event, context):
        self.game.broadcast(f"{self.owner.name} 发动激发，所有玩家重抽技能！")
        for p in self.game.players:
            p.skills.clear()
        available_pool = [s for s in self.game.skill_pool if not s.is_consumed and s.owner is None]
        if len(available_pool) < 3 * len(self.game.players):
            self.owner_print("技能池不足，无法重抽。")
            return False
        for p in self.game.players:
            if p == self.owner:
                continue
            for _ in range(3):
                s = available_pool.pop()
                s.owner = p
                p.skills.append(s)
                self.game.skill_pool.remove(s)
        candidates = [available_pool.pop() for _ in range(9)]
        if self.owner.is_human:
            self.owner_print("激发：请从以下9张技能中选择3张：")
            for i, s in enumerate(candidates):
                self.owner_print(f"  {i}: {s.name} - {s.description}")
            chosen_indices = []
            while len(chosen_indices) < 3:
                try:
                    idx = int(self.owner.ui.input(f"选择第{len(chosen_indices)+1}张: ").strip())
                    if idx in chosen_indices:
                        self.owner_print("重复选择")
                    elif 0 <= idx < 9:
                        chosen_indices.append(idx)
                except Exception:
                    pass
            for i in chosen_indices:
                s = candidates[i]
                s.owner = self.owner
                self.owner.skills.append(s)
                self.game.skill_pool.remove(s)
        else:
            selected = random.sample(candidates, 3)
            for s in selected:
                s.owner = self.owner
                self.owner.skills.append(s)
                self.game.skill_pool.remove(s)
        for s in candidates:
            if s.owner is None:
                self.game.skill_pool.append(s)
        self.game.broadcast("激发完成，所有玩家技能已更新。")
        self.is_consumed = True
        return True


class YeLi(Skill):
    def __init__(self, owner, game):
        super().__init__('业力', SkillType.ACTIVE,
                         '猜一人手牌颜色偏向。猜对对方+8，猜错自己+5',
                         '在自己回合使用，指定一名玩家，猜测其手牌中最多的颜色。',
                         owner, game, urgency_weight=40)

    def can_trigger(self, event, context):
        if self.is_consumed or self.is_deleted:
            return False
        return event == GameEvent.TURN_START and context.get('player') == self.owner

    def activate(self, event, context):
        target = self._choose_target()
        if not target:
            return False
        color_count = {col: 0 for col in ['红', '蓝', '绿', '黄']}
        for c in target.hand:
            if c.color in color_count:
                color_count[c.color] += 1
        most_color = max(color_count, key=color_count.get)
        if self.owner.is_human:
            self.owner_print(f"目标 {target.name} 的手牌颜色分布（隐藏），请猜测主要颜色: ")
            guess = self.owner.ui.input("0红 1蓝 2绿 3黄: ").strip()
            guess_map = {'0': '红', '1': '蓝', '2': '绿', '3': '黄'}
            guess_color = guess_map.get(guess, '红')
        else:
            guess_color = random.choice(['红', '蓝', '绿', '黄'])
        self.owner_print(f"{self.owner.name} 猜测 {target.name} 的主要颜色为 {guess_color}，实际为 {most_color}")
        if guess_color == most_color:
            self.owner_print("猜测正确！目标+8张牌")
            self.game.apply_add_cards(target, 8)
        else:
            self.owner_print("猜测错误！自己+5张牌")
            self.game.apply_add_cards(self.owner, 5)
        self.is_consumed = True
        return True

    def _choose_target(self):
        active = [p for p in self.game.players if p != self.owner and not p.eliminated]
        if not active:
            return None
        if self.owner.is_human:
            self.owner_print("选择业力目标：")
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


class DuoXinPo(Skill):
    def __init__(self, owner, game):
        super().__init__('夺心魄', SkillType.ACTIVE,
                         '被加牌时，选任意数量其他玩家一起承受',
                         '当你即将被加牌时，消耗此牌，选择任意数量的其他玩家一起加牌。',
                         owner, game, urgency_weight=70)

    def can_trigger(self, event, context):
        if self.is_consumed or self.is_deleted:
            return False
        return event == GameEvent.BEING_ADDED_CARDS and context.get('target') == self.owner

    def activate(self, event, context):
        amount = context.get('amount', 0)
        active = [p for p in self.game.players if p != self.owner and not p.eliminated]
        if not active:
            return False
        if self.owner.is_human:
            self.owner_print("夺心魄：选择要一起承受加牌的玩家（多选，用逗号分隔序号，直接回车取消）:")
            for i, p in enumerate(active):
                self.owner_print(f"  {i}: {p.name}")
            choices = self.owner.ui.input("序号(如 0,1): ").strip()
            if choices == '':
                return False
            try:
                indices = [int(x.strip()) for x in choices.split(',')]
                for idx in indices:
                    if 0 <= idx < len(active):
                        p = active[idx]
                        self.owner_print(f"{p.name} 共同承受 {amount} 张加牌。")
                        self.game.apply_add_cards(p, amount)
                self.is_consumed = True
                return True
            except Exception:
                pass
        else:
            victims = random.sample(active, min(2, len(active)))
            for p in victims:
                self.owner_print(f"{self.owner.name} 使用夺心魄，{p.name} 一同承受 {amount} 张牌。")
                self.game.apply_add_cards(p, amount)
            self.is_consumed = True
            return True
        return False


class HunQian(Skill):
    def __init__(self, owner, game):
        super().__init__('魂迁', SkillType.ACTIVE,
                         '被加牌时，随机转移该效果（可转回自己）',
                         '当你即将被加牌时，消耗此牌，将加牌效果随机转移给任意一名玩家。',
                         owner, game, urgency_weight=65)

    def can_trigger(self, event, context):
        if self.is_consumed or self.is_deleted:
            return False
        return event == GameEvent.BEING_ADDED_CARDS and context.get('target') == self.owner

    def activate(self, event, context):
        amount = context.get('amount', 0)
        possible = [p for p in self.game.players if not p.eliminated]
        target = random.choice(possible)
        self.owner_print(f"{self.owner.name} 发动魂迁，将加牌转移给 {target.name}！")
        context['cancel'] = True
        self.is_consumed = True
        self.game.apply_add_cards(target, amount)
        return True


SKILL_CLASSES = [
    YanPin, TanNang, XianLing, JiaHuo,
    JiFa, YeLi, DuoXinPo, HunQian
]