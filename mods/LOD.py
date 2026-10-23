"""SkillUNO 生死赛季（LOD）。

6 个技能围绕生死博弈。依赖 uno.core 的 Skill/SkillType/GameEvent
和 uno.achievements 的 Achievement。

类型分配：
- Peek / GetAway / MutualDestruction：HYBRID（主动 + 被动混合）
- Die / Rebirth：ACTIVE
- FakeDeath：PASSIVE（监听 CARDS_ADDED）
"""
import random

from uno.core import Skill, SkillType, GameEvent
from uno.achievements import Achievement

SEASON_ID = "LOD"
SEASON_NAME = "生死赛季"


def _is_owner_turn(event, context, owner):
    return event == GameEvent.TURN_START and context.get('player') is owner


class Peek(Skill):
    def __init__(self, owner, game):
        super().__init__('偷看', SkillType.HYBRID,
                         '主动看牌顶3张选1；被动查看发动技能者的可用技能',
                         '自己回合主动使用：查看牌顶3张，选1张加入手牌，其余放回。'
                         '被动：任意其他玩家发动技能时，查看其剩余可用技能（不消耗）。',
                         owner, game, urgency_weight=30)

    def can_trigger(self, event, context):
        if self.is_consumed or self.is_deleted:
            return False
        if _is_owner_turn(event, context, self.owner):
            return True
        if event == GameEvent.SKILL_ACTIVATED:
            activated = context.get('activated_skill')
            if activated and getattr(activated, 'owner', None) != self.owner:
                return True
        return False

    def activate(self, event, context):
        # 被动分支：看对方技能，不消耗
        if event == GameEvent.SKILL_ACTIVATED:
            activated = context.get('activated_skill')
            if not activated:
                return False
            other = activated.owner
            names = [s.name for s in other.skills
                     if not s.is_consumed and not s.is_deleted]
            self.game.broadcast(
                f"【偷看】{self.owner.name} 察觉 {other.name} 发动技能，"
                f"其可用技能：{', '.join(names) if names else '无'}")
            return True

        # 主动分支：看牌顶 3 张
        if not self.game.deck.cards:
            self.game.deck.reshuffle_from_discard()
        if len(self.game.deck.cards) < 3:
            return False

        c1 = self.game.deck.cards.pop()
        c2 = self.game.deck.cards.pop()
        c3 = self.game.deck.cards.pop()
        options = [c1, c2, c3]

        if self.owner.is_human:
            self.owner_print("牌顶3张：")
            for i, c in enumerate(options):
                self.owner_print(f"  {i}: {c}")
            try:
                idx = int(self.owner.ui.input("选择一张加入手牌(0-2)：").strip())
            except Exception:
                idx = -1
            if not (0 <= idx < 3):
                for c in reversed(options):
                    self.game.deck.cards.append(c)
                return False
        else:
            idx = random.randrange(3)

        chosen = options[idx]
        rest = [c for i, c in enumerate(options) if i != idx]
        for c in reversed(rest):
            self.game.deck.cards.append(c)

        self.owner.hand.append(chosen)
        self.owner_print(f"偷看：获得 {chosen}")
        self.is_consumed = True
        return True


class GetAway(Skill):
    def __init__(self, owner, game):
        super().__init__('逃离', SkillType.HYBRID,
                         '主动进入警戒反弹加牌；手牌剩1张直接获胜',
                         '主动：进入警戒状态，下次被加牌时取消并反弹。'
                         '被动：自己打出牌后手牌剩 1 张，直接获胜。',
                         owner, game, urgency_weight=40)
        self.armed = False

    def can_trigger(self, event, context):
        if self.is_deleted:
            return False
        if _is_owner_turn(event, context, self.owner) and not self.is_consumed:
            return True
        if (event == GameEvent.BEING_ADDED_CARDS
                and context.get('target') == self.owner
                and self.armed):
            return True
        if (event == GameEvent.AFTER_PLAY
                and context.get('player') == self.owner
                and len(self.owner.hand) == 1
                and not self.is_consumed):
            return True
        return False

    def activate(self, event, context):
        if _is_owner_turn(event, context, self.owner):
            self.armed = True
            self.owner_print(f"{self.owner.name} 进入逃离警戒，下次被加牌将反弹。")
            return True

        if event == GameEvent.BEING_ADDED_CARDS:
            amount = int(context.get('amount', 0))
            context['cancel'] = True
            attacker = context.get('attacker') or self.game.current_player()
            if attacker and attacker != self.owner and not attacker.eliminated:
                cards = self.game.deck.draw_many(amount)
                attacker.draw_cards(cards)
                self.game.broadcast(
                    f"{self.owner.name} 发动逃离，取消加牌并反弹 {amount} 张给 {attacker.name}！")
                if attacker.hand_size() > attacker.hand_limit:
                    attacker.eliminate(self.game)
                    self.game.skill_manager.trigger(
                        GameEvent.PLAYER_DIED, {'player': attacker})
            else:
                self.game.broadcast(f"{self.owner.name} 发动逃离，取消加牌！")
            self.armed = False
            self.is_consumed = True
            return True

        if event == GameEvent.AFTER_PLAY:
            self.owner.hand.clear()
            self.game.broadcast(f"{self.owner.name} 手牌剩1张，逃离成功，直接获胜！")
            self.is_consumed = True
            return True

        return False


class Die(Skill):
    def __init__(self, owner, game):
        super().__init__('死', SkillType.ACTIVE,
                         '给自己加15张牌（通常触发上限淘汰）',
                         '自己回合主动使用：立刻给自己加 15 张牌。'
                         '若有假死等防御技能，可能反而存活。',
                         owner, game, urgency_weight=10)

    def can_trigger(self, event, context):
        if self.is_consumed or self.is_deleted:
            return False
        return _is_owner_turn(event, context, self.owner)

    def activate(self, event, context):
        self.owner_print(f"{self.owner.name} 发动【死】，给自己加15张牌！")
        self.is_consumed = True
        self.game.apply_add_cards(self.owner, 15)
        return True


class Rebirth(Skill):
    def __init__(self, owner, game):
        super().__init__('绝处逢生', SkillType.ACTIVE,
                         '弃光所有手牌，重新抽5张',
                         '自己回合主动使用：弃置全部手牌，重新抽 5 张。',
                         owner, game, urgency_weight=45)

    def can_trigger(self, event, context):
        if self.is_consumed or self.is_deleted:
            return False
        return _is_owner_turn(event, context, self.owner)

    def activate(self, event, context):
        self.owner_print(f"{self.owner.name} 发动【绝处逢生】，弃光手牌重抽5张！")
        self.owner.hand.clear()
        self.owner.hand.extend(self.game.deck.draw_many(5))
        self.is_consumed = True
        return True


class MutualDestruction(Skill):
    def __init__(self, owner, game):
        super().__init__('同归于尽', SkillType.HYBRID,
                         '下家加10张，自己手牌变成2张',
                         '主动：自己回合使用，给下家加 10 张，自己手牌变为 2 张。'
                         '被动：打出最后一张牌时自动触发同样效果（阻止自己立刻获胜）。',
                         owner, game, urgency_weight=60)

    def can_trigger(self, event, context):
        if self.is_consumed or self.is_deleted:
            return False
        if _is_owner_turn(event, context, self.owner):
            return True
        if (event == GameEvent.AFTER_PLAY
                and context.get('player') == self.owner
                and len(self.owner.hand) == 0):
            return True
        return False

    def activate(self, event, context):
        nxt = self.game.peek_next_player()
        if not nxt or nxt.eliminated:
            return False
        self._set_hand_to_two()
        cards = self.game.deck.draw_many(10)
        nxt.draw_cards(cards)
        self.game.broadcast(
            f"{self.owner.name} 发动【同归于尽】：{nxt.name} 加10张，自己手牌变为2张！")
        if nxt.hand_size() > nxt.hand_limit:
            nxt.eliminate(self.game)
            self.game.skill_manager.trigger(GameEvent.PLAYER_DIED, {'player': nxt})
        self.is_consumed = True
        return True

    def _set_hand_to_two(self):
        while len(self.owner.hand) > 2:
            self.game.discard_pile.append(self.owner.hand.pop())
        while len(self.owner.hand) < 2:
            self.owner.hand.extend(self.game.deck.draw_many(1))


class FakeDeath(Skill):
    def __init__(self, owner, game):
        super().__init__('假死', SkillType.PASSIVE,
                         '手牌超上限时清到5张，抵消一次淘汰',
                         '被动：手牌超过上限时自动触发，将手牌清至 5 张，'
                         '抵消本次淘汰。',
                         owner, game)

    def can_trigger(self, event, context):
        if self.is_consumed or self.is_deleted:
            return False
        return (event == GameEvent.CARDS_ADDED
                and context.get('target') == self.owner
                and self.owner.hand_size() > self.owner.hand_limit)

    def activate(self, event, context):
        while self.owner.hand_size() > 5:
            self.owner.hand.pop()
        self.game.broadcast(
            f"{self.owner.name} 发动【假死】，手牌清至5张，躲过淘汰！")
        self.is_consumed = True
        return True


class DancingWithDeath(Achievement):
    def __init__(self):
        super().__init__('dancing_with_death', '与死神共舞',
                         '主动使用【死】加了15张牌，但依然存活并最终获胜')

    def check(self, game, events):
        human = game.players[0]
        used_die = any(
            e['type'] == 'skill_use'
            and e.get('skill_name') == '死'
            and e.get('player') == human.name
            for e in events
        )
        if not used_die:
            return False
        if any(e['type'] == 'player_eliminated' and e['player'] == human.name
               for e in events):
            return False
        return any(e['type'] == 'game_end' and e.get('winner') == human.name
                   for e in events)


SKILL_CLASSES = [
    Peek, GetAway, Die, Rebirth, MutualDestruction, FakeDeath,
]

ACHIEVEMENTS = [
    DancingWithDeath,
]
