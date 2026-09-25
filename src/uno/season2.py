from .core import Skill, SkillType, GameEvent
from .combo_base import ComboBase
import random

SEASON_ID = "S2"
SEASON_NAME = "被动觉醒赛季"


class SuQinZhangYiCombo(ComboBase):
    def execute(self, player, skill_manager, game):
        for s in player.skills:
            if s.name == '苏秦' and not s.is_consumed:
                s.is_consumed = True
            if s.name == '张仪' and not s.is_consumed:
                s.is_consumed = True
        game.broadcast(f"{player.name} 发动组合技「合纵连横·骰子审判」！")
        game.broadcast("所有玩家开始投骰子判定...")
        for p in game.players:
            if p.eliminated:
                continue
            random_ctx = {'player': p, 'dice': True, 'retry': False}
            skill_manager.trigger(GameEvent.START_RANDOM, random_ctx)
            dice = random.randint(1, 6)
            if random_ctx.get('retry'):
                game.broadcast(f"  双生花被动触发，{p.name} 重掷骰子！")
                dice = random.randint(1, 6)
            game.broadcast(f"  {p.name} 掷出 {dice} 点")
            if dice >= 5:
                game.broadcast("，免受惩罚。")
            else:
                game.broadcast("，受到惩罚，加5张牌！")
                game.apply_add_cards(p, 5)


class ShiHuangDi(Skill):
    def __init__(self, owner, game):
        super().__init__('始皇帝', SkillType.ACTIVE,
                         '被动：开局从牌堆顶14张中自选7张起手。主动「车同轨」：指定一色，全员弃掉该色以外所有牌。',
                         '被动在游戏开始时自动触发。主动在己方回合使用。',
                         owner, game, urgency_weight=70)
        self.passive_used = False

    def can_trigger(self, event, context):
        if self.is_consumed or self.is_deleted:
            return False
        if event == GameEvent.GAME_START and not self.passive_used:
            return True
        if event == GameEvent.TURN_START and context.get('player') == self.owner:
            return True
        return False

    def evaluate_urgency(self, game):
        max_opp = max((p.hand_size() for p in game.players if p != self.owner and not p.eliminated), default=0)
        return 90 if max_opp >= 10 else 70

    def activate(self, event, context):
        if event == GameEvent.GAME_START:
            self.passive_used = True
            self.game.discard_pile.extend(self.owner.hand)
            self.owner.hand.clear()
            top14 = self.game.deck.draw_many(14)
            if self.owner.is_human:
                self.owner_print("始皇帝：请从以下14张牌中选择7张作为起始手牌：")
                for i, c in enumerate(top14):
                    self.owner_print(f"  {i}: {c}")
                selected = []
                while len(selected) < 7:
                    try:
                        idx = int(self.owner.ui.input(f"选择第{len(selected)+1}张: ").strip())
                        if 0 <= idx < len(top14):
                            selected.append(top14.pop(idx))
                    except Exception:
                        pass
                self.owner.hand = selected
                self.game.deck.cards.extend(top14)
                self.game.deck.shuffle()
            else:
                random.shuffle(top14)
                self.owner.hand = top14[:7]
                self.game.deck.cards.extend(top14[7:])
                self.game.deck.shuffle()
            self.owner_print(f"{self.owner.name} 发动始皇帝被动，重选7张起手牌。")
            return False
        elif event == GameEvent.TURN_START:
            self.owner_print(f"{self.owner.name} 发动始皇帝主动技「车同轨」！")
            if self.owner.is_human:
                self.owner_print("选择颜色: 0红 1蓝 2绿 3黄")
                c = self.owner.ui.input("请输入颜色序号: ").strip()
                chosen_color = ['红', '蓝', '绿', '黄'][int(c)] if c in ['0', '1', '2', '3'] else '红'
            else:
                color_count = {col: 0 for col in ['红', '蓝', '绿', '黄']}
                for card in self.owner.hand:
                    if card.color in color_count:
                        color_count[card.color] += 1
                chosen_color = max(color_count, key=color_count.get)
            self.game.broadcast(f"车同轨：所有玩家必须弃掉 {chosen_color} 以外的所有牌！")
            for p in self.game.players:
                if p.eliminated:
                    continue
                to_discard = [c for c in p.hand if c.color != chosen_color]
                p.hand = [c for c in p.hand if c.color == chosen_color]
                self.game.discard_pile.extend(to_discard)
                self.game.broadcast(f"  {p.name} 弃掉了 {len(to_discard)} 张牌，剩余 {len(p.hand)} 张")
                if len(p.hand) == 0:
                    self.game.broadcast(f"  {p.name} 打光了手牌，车同轨规则：加一张牌。")
                    p.hand.append(self.game.deck.draw(1))
            if self.game.discard_pile:
                top = self.game.discard_pile[-1]
                if top.color != '黑':
                    self.game.current_color = top.color
            self.is_consumed = True
            return True
        return False


class SuQin(Skill):
    def __init__(self, owner, game):
        super().__init__('苏秦', SkillType.ACTIVE,
                         '被动：开局自己抽5张，他人抽9张。主动：现有加牌变减牌。与张仪组合发动全场骰子审判。',
                         '被动在游戏开始时触发。主动可在被加牌时使用。',
                         owner, game, urgency_weight=50,
                         combo_partners=('苏秦', '张仪'), combo_effect=SuQinZhangYiCombo)
        self.passive_used = False

    def can_trigger(self, event, context):
        if self.is_consumed or self.is_deleted:
            return False
        if event == GameEvent.GAME_START and not self.passive_used:
            return True
        if event == GameEvent.BEING_ADDED_CARDS and context.get('target') == self.owner:
            return True
        return False

    def evaluate_urgency(self, game):
        return 70 if self.owner.hand_size() >= 8 else 30

    def activate(self, event, context):
        if event == GameEvent.GAME_START:
            self.passive_used = True
            for p in self.game.players:
                if not p.eliminated:
                    self.game.discard_pile.extend(p.hand)
                    p.hand.clear()
            self.owner.hand = self.game.deck.draw_many(5)
            for p in self.game.players:
                if p != self.owner and not p.eliminated:
                    p.hand = self.game.deck.draw_many(9)
            self.game.broadcast("苏秦发动被动：合纵连横，起手牌数改变。")
            return False
        elif event == GameEvent.BEING_ADDED_CARDS:
            amount = context.get('amount', 0)
            self.owner_print(f"{self.owner.name} 发动苏秦主动技，将加牌转为减牌！")
            removed = min(amount, len(self.owner.hand))
            if removed > 0:
                del self.owner.hand[-removed:]
                self.owner_print(f"  移除了 {removed} 张手牌。")
            context['cancel'] = True
            self.is_consumed = True
            return True
        return False


class ZhangYi(Skill):
    def __init__(self, owner, game):
        super().__init__('张仪', SkillType.ACTIVE,
                         '被动：开局自己抽5张，他人抽9张。主动：数字≤4的牌变加牌。与苏秦组合发动全场骰子审判。',
                         '被动在游戏开始时触发。主动在己方回合可选择一张数字≤4的牌，将其打出并让下家+2。',
                         owner, game, urgency_weight=50,
                         combo_partners=('苏秦', '张仪'), combo_effect=SuQinZhangYiCombo)
        self.passive_used = False

    def can_trigger(self, event, context):
        if self.is_consumed or self.is_deleted:
            return False
        if event == GameEvent.GAME_START and not self.passive_used:
            return True
        if event == GameEvent.TURN_START and context.get('player') == self.owner:
            return True
        return False

    def evaluate_urgency(self, game):
        targets = [c for c in self.owner.hand if c.type == '数字' and c.value <= 4]
        if not targets:
            return 0
        next_p = game.peek_next_player()
        if next_p and next_p.hand_size() <= 2:
            return 90
        return 50

    def activate(self, event, context):
        if event == GameEvent.GAME_START:
            self.passive_used = True
            for p in self.game.players:
                if not p.eliminated:
                    self.game.discard_pile.extend(p.hand)
                    p.hand.clear()
            self.owner.hand = self.game.deck.draw_many(5)
            for p in self.game.players:
                if p != self.owner and not p.eliminated:
                    p.hand = self.game.deck.draw_many(9)
            self.game.broadcast("张仪发动被动：连横，起手牌数改变。")
            return False
        elif event == GameEvent.TURN_START:
            targets = [c for c in self.owner.hand if c.type == '数字' and c.value <= 4]
            if not targets:
                return False
            if self.owner.is_human:
                self.owner_print("张仪主动技：选择一张数字≤4的牌，将其变为+2效果")
                for i, c in enumerate(self.owner.hand):
                    if c.type == '数字' and c.value <= 4:
                        self.owner_print(f"  {i}: {c}")
                try:
                    idx = int(self.owner.ui.input("请输入序号: ").strip())
                    card = self.owner.hand[idx]
                    if card.type == '数字' and card.value <= 4:
                        self.owner.hand.pop(idx)
                        self.game.discard_pile.append(card)
                        next_p = self.game.peek_next_player()
                        if next_p:
                            self.game.apply_add_cards(next_p, 2)
                        self.is_consumed = True
                        return True
                except Exception:
                    pass
            else:
                card = random.choice(targets)
                idx = self.owner.hand.index(card)
                self.owner.hand.pop(idx)
                self.game.discard_pile.append(card)
                next_p = self.game.peek_next_player()
                if next_p:
                    self.game.apply_add_cards(next_p, 2)
                self.is_consumed = True
                return True
        return False


class ShuangShengHua(Skill):
    def __init__(self, owner, game):
        super().__init__('双生花', SkillType.ACTIVE,
                         '被动：涉及自己的骰子/转盘可重来一次。主动：与一人同盟，共享技能池，伤害同步。',
                         '被动：涉及随机时可重掷。主动：结盟，伤害同步。孤勇者不可结盟。',
                         owner, game, urgency_weight=60)
        self.ally = None

    def can_trigger(self, event, context):
        if self.is_consumed or self.is_deleted:
            return False
        if event == GameEvent.START_RANDOM and context.get('player') == self.owner:
            return True
        if event == GameEvent.TURN_START and context.get('player') == self.owner and self.ally is None:
            return True
        if event == GameEvent.CARDS_ADDED and self.ally and context.get('target') == self.ally:
            return True
        return False

    def evaluate_urgency(self, game):
        return 70 if self.ally is None else 0

    def activate(self, event, context):
        if event == GameEvent.START_RANDOM and context.get('player') == self.owner:
            if self.owner.is_human:
                ans = self.owner.ui.input(f"{self.owner.name}，双生花被动：是否重掷？(y/n): ").strip().lower()
                if ans == 'y':
                    context['retry'] = True
            else:
                if random.random() < 0.5:
                    context['retry'] = True
            return False
        elif event == GameEvent.TURN_START and self.ally is None:
            target = self._choose_ally()
            if target:
                has_guyongzhe = any(s.name == '孤勇者' for s in target.skills)
                if has_guyongzhe:
                    self.owner_print("双生花无法绑定孤勇者！")
                    return False
                self.ally = target
                self.game.broadcast(f"{self.owner.name} 与 {target.name} 结为双生花同盟，伤害同步！")
                return False
        elif event == GameEvent.CARDS_ADDED and self.ally and context.get('target') == self.ally:
            amount = context.get('amount', 0)
            if amount > 0:
                self.game.broadcast(f"双生花同步：{self.owner.name} 同样受到 {amount} 张加牌。")
                self.game.apply_add_cards(self.owner, amount)
            return False
        return False

    def _choose_ally(self):
        active = [p for p in self.game.players if p != self.owner and not p.eliminated]
        if not active:
            return None
        if self.owner.is_human:
            self.owner_print("选择双生花同盟目标：")
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


class JinShen(Skill):
    def __init__(self, owner, game):
        super().__init__('金身', SkillType.ACTIVE,
                         '被动：免≥8张加牌。主动：反制破万法。',
                         '被动：当即将被加牌且数量≥8时，自动抵消。主动：反制破万法。',
                         owner, game, urgency_weight=60)

    def can_trigger(self, event, context):
        if self.is_consumed or self.is_deleted:
            return False
        if event == GameEvent.BEING_ADDED_CARDS and context.get('target') == self.owner:
            if context.get('amount', 0) >= 8:
                return True
        if event == GameEvent.SKILL_ACTIVATED:
            activated_skill = context.get('activated_skill')
            if activated_skill and type(activated_skill).__name__ == 'PoWanFa':
                return True
        return False

    def activate(self, event, context):
        if event == GameEvent.BEING_ADDED_CARDS:
            self.owner_print(f"{self.owner.name} 金身护体，抵消了{context['amount']}张加牌！")
            context['cancel'] = True
            return True
        elif event == GameEvent.SKILL_ACTIVATED:
            target_skill = context['activated_skill']
            if type(target_skill).__name__ == 'PoWanFa':
                self.owner_print(f"{self.owner.name} 发动金身，反制破万法！")
                target_skill.is_consumed = True
                context['cancel'] = True
                self.is_consumed = True
                return True
        return False


class YingYan(Skill):
    def __init__(self, owner, game):
        super().__init__('鹰眼', SkillType.ACTIVE,
                         '被动：开局看一人技能。主动：看牌堆顶5张。',
                         '被动在游戏开始时自动触发。主动在己方回合使用。',
                         owner, game, urgency_weight=40)

    def can_trigger(self, event, context):
        if self.is_consumed or self.is_deleted:
            return False
        if event == GameEvent.GAME_START:
            return True
        if event == GameEvent.TURN_START and context.get('player') == self.owner:
            return True
        return False

    def evaluate_urgency(self, game):
        return 30

    def activate(self, event, context):
        if event == GameEvent.GAME_START:
            targets = [p for p in self.game.players if p != self.owner]
            if targets:
                target = random.choice(targets)
                visible = [s for s in target.skills if not s.is_deleted]
                self.owner_print(f"鹰眼：{target.name} 的技能有 {[s.name for s in visible]}")
            return False
        elif event == GameEvent.TURN_START:
            self.owner_print("鹰眼主动：牌堆顶5张牌")
            top5 = self.game.deck.draw_many(5)
            for i, c in enumerate(top5):
                self.owner_print(f"  {i}: {c}")
            self.game.deck.cards.extend(top5)
            self.is_consumed = True
            return True
        return False


class GuYongZhe(Skill):
    def __init__(self, owner, game):
        super().__init__('孤勇者', SkillType.PASSIVE,
                         '被动：取消一切同盟。主动：攒7次抽牌后全场+7，被发现作废。',
                         '被动：任何同盟效果对你无效。主动：抽牌达7次时，可发动全场其他玩家各加7张。',
                         owner, game, urgency_weight=50)
        self.draw_count = 0
        self.exposed = False

    def can_trigger(self, event, context):
        if self.is_consumed or self.is_deleted:
            return False
        if event == GameEvent.AFTER_DRAW and context.get('player') == self.owner:
            self.draw_count += 1
            return False
        if event == GameEvent.TURN_START and context.get('player') == self.owner and self.draw_count >= 7 and not self.exposed:
            return True
        return False

    def evaluate_urgency(self, game):
        return 90 if self.draw_count >= 7 and not self.exposed else 0

    def activate(self, event, context):
        if event == GameEvent.TURN_START and self.draw_count >= 7 and not self.exposed:
            self.game.broadcast(f"{self.owner.name} 发动孤勇者主动技：全场+7！")
            for p in self.game.players:
                if not p.eliminated and p != self.owner:
                    self.game.apply_add_cards(p, 7)
            self.draw_count = 0
            return True
        return False


class WangYou(Skill):
    def __init__(self, owner, game):
        super().__init__('忘忧', SkillType.DEATH,
                         '死后从弃牌堆偷一技能，用后真死（可被救）。',
                         '当你因手牌上限淘汰时，从场上所有玩家的已消耗技能中随机偷取一张。',
                         owner, game)

    def can_trigger(self, event, context):
        if self.is_consumed or self.is_deleted:
            return False
        return event == GameEvent.PLAYER_DIED and context.get('player') == self.owner

    def activate(self, event, context):
        available = []
        for p in self.game.players:
            for s in p.skills:
                if s.is_consumed and not s.is_deleted and s != self:
                    available.append(s)
        if not available:
            self.owner_print("忘忧：没有可偷取的技能。")
            self.is_consumed = True
            return True
        chosen = random.choice(available)
        chosen.owner = self.owner
        chosen.is_consumed = False
        self.owner.skills.append(chosen)
        self.owner_print(f"{self.owner.name} 发动忘忧，偷取技能 {chosen.name} 并立即使用！")
        self.game.skill_manager.execute_skill(chosen, GameEvent.TURN_START, {'player': self.owner})
        self.is_consumed = True
        return True


SKILL_CLASSES = [
    ShiHuangDi, SuQin, ZhangYi, ShuangShengHua,
    JinShen, YingYan, GuYongZhe, WangYou
]