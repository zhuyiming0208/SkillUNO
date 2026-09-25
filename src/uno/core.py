import random
import os
from enum import Enum, auto
from typing import List, Optional, Dict, Any
from .combo_base import ComboBase
from .ui import ConsoleUI, NullUI, RichUI
from .achievements import AchievementManager, get_core_achievements


class SkillType(Enum):
    ACTIVE = auto()
    PASSIVE = auto()
    DEATH = auto()


class GameEvent(Enum):
    GAME_START = auto()
    TURN_START = auto()
    BEFORE_DRAW = auto()
    AFTER_DRAW = auto()
    BEFORE_PLAY = auto()
    AFTER_PLAY = auto()
    BEING_ADDED_CARDS = auto()
    CARDS_ADDED = auto()
    PLAYER_ELIMINATED = auto()
    SKILL_ACTIVATED = auto()
    PLAYER_DIED = auto()
    START_RANDOM = auto()
    END_RANDOM = auto()


class Card:
    COLORS = ['红', '蓝', '绿', '黄']
    TYPES = ['数字', '跳过', '反转', '+2', '万能', '万能+4']

    def __init__(self, color: str, card_type: str, value: int = None):
        self.color = color
        self.type = card_type
        self.value = value

    def __repr__(self):
        if self.type == '数字':
            return f"{self.color}{self.value}"
        elif self.type in ['万能', '万能+4']:
            return "万能+4" if self.type == '万能+4' else "万能"
        else:
            return f"{self.color}{self.type}"

    def is_playable_on(self, top_card: 'Card', chosen_color: str = None) -> bool:
        if self.type in ['万能', '万能+4']:
            return True
        effective_color = chosen_color if chosen_color else top_card.color
        if self.color == effective_color:
            return True
        if self.type == '数字' and top_card.type == '数字' and self.value == top_card.value:
            return True
        if self.type in ['跳过', '反转', '+2'] and self.type == top_card.type:
            return True
        return False


class Deck:
    def __init__(self, discard_pile: List[Card] = None, ui: ConsoleUI = None):
        self.cards: List[Card] = []
        self.discard = discard_pile if discard_pile is not None else []
        self.ui = ui
        self.build()
        self.shuffle()

    def _notify(self, msg: str):
        if self.ui is not None:
            self.ui.show(msg)
        else:
            print(msg)

    def build(self):
        for color in Card.COLORS:
            self.cards.append(Card(color, '数字', 0))
            for num in range(1, 10):
                self.cards.append(Card(color, '数字', num))
                self.cards.append(Card(color, '数字', num))
            for _ in range(2):
                self.cards.append(Card(color, '跳过'))
                self.cards.append(Card(color, '反转'))
                self.cards.append(Card(color, '+2'))
        for _ in range(4):
            self.cards.append(Card('黑', '万能'))
            self.cards.append(Card('黑', '万能+4'))

    def shuffle(self):
        random.shuffle(self.cards)

    def draw(self, count: int = 1):
        drawn = []
        for _ in range(count):
            if not self.cards:
                self.reshuffle_from_discard()
            drawn.append(self.cards.pop())
        return drawn if count > 1 else drawn[0]

    def draw_one(self) -> Card:
        return self.draw(1)

    def draw_many(self, count: int) -> List[Card]:
        result = []
        for _ in range(count):
            result.append(self.draw(1))
        return result

    def reshuffle_from_discard(self):
        if not self.discard:
            raise Exception("无牌可抽！")
        top = self.discard.pop()
        if self.discard:
            self.cards = self.discard[:]
            self.discard.clear()
            self.discard.append(top)
            self.shuffle()
            self._notify("[系统] 牌堆已重洗。")
        else:
            self.cards = [top]
            self.discard.clear()
            self.shuffle()
            self._notify("[系统] 牌堆已重洗（弃牌堆仅剩一张，已全部洗入）。")


class Skill:
    def __init__(self, name: str, skill_type: SkillType, description: str,
                 help_text: str = "", owner: 'Player' = None, game: 'UNOGame' = None,
                 combo_partners: tuple = None, combo_effect: type = None,
                 urgency_weight: int = 50):
        self.name = name
        self.type = skill_type
        self.description = description
        self.help_text = help_text
        self.owner = owner
        self.game = game
        self.is_consumed = False
        self.is_deleted = False
        self.combo_partners = combo_partners or ()
        self.combo_effect = combo_effect
        self.urgency_weight = urgency_weight

    def can_trigger(self, event: GameEvent, context: Dict[str, Any]) -> bool:
        return False

    def activate(self, event: GameEvent, context: Dict[str, Any]) -> bool:
        return False

    def evaluate_urgency(self, game) -> int:
        return self.urgency_weight

    def owner_print(self, text: str):
        if self.owner and self.owner.is_human:
            self.owner.ui.show(text)

    def __repr__(self):
        return self.name


class Player:
    def __init__(self, name: str, is_human: bool = False, ui: ConsoleUI = None):
        self.name = name
        self.is_human = is_human
        self.ui = ui or ConsoleUI()
        self.hand: List[Card] = []
        self.skills: List[Skill] = []
        self.eliminated = False
        self.hand_limit = 15

    def draw_cards(self, cards: List[Card]):
        self.hand.extend(cards)

    def hand_size(self) -> int:
        return len(self.hand)

    def eliminate(self, game: 'UNOGame'):
        self.eliminated = True
        game.discard_pile.extend(self.hand)
        self.hand.clear()
        game.broadcast(f"[淘汰] {self.name} 手牌超过{self.hand_limit}张，立刻淘汰！")
        game.skill_manager.trigger(GameEvent.PLAYER_ELIMINATED, {'player': self})
        game.record_event('player_eliminated', player=self.name,
                          reason='hand_limit', turn_number=game.turn_number)

    def show_hand(self) -> str:
        return '  '.join(f"[{i}]{card}" for i, card in enumerate(self.hand))

    def show_skills(self) -> List[str]:
        result = []
        for s in self.skills:
            if s.is_deleted:
                result.append("???")
            elif s.is_consumed:
                result.append(f"{s.name}(已用)")
            else:
                result.append(s.name)
        return result

    def get_available_combos(self):
        combos = []
        for s in self.skills:
            if s.is_consumed or s.is_deleted or not s.combo_effect:
                continue
            partners_ok = True
            for partner_name in s.combo_partners:
                found = any(p.name == partner_name and not p.is_consumed and not p.is_deleted
                            for p in self.skills)
                if not found:
                    partners_ok = False
                    break
            if partners_ok:
                combo_id = tuple(sorted(s.combo_partners))
                if combo_id not in [c[0] for c in combos]:
                    combos.append((combo_id, s.combo_effect))
        return [(f"组合技:{'/'.join(cid)}", ce) for cid, ce in combos]

    def choose_play(self, top_card: Card, current_color: str, game: 'UNOGame') -> Optional[int]:
        self.game = game
        if self.is_human:
            return self.human_choose(top_card, current_color)
        else:
            return self.ai_choose(top_card, current_color)

    def human_choose(self, top_card: Card, current_color: str) -> Optional[int]:
        if getattr(self.game, 'hotseat', False):
            self.ui.pause(f"请将屏幕转交给 {self.name}，按回车继续...")
            self.ui.clear_screen()

        ui = self.ui
        if isinstance(ui, RichUI):
            ui.show_turn_header(self)
            ui.print_inline("当前牌: ")
            ui.show_card(top_card)
            ui.show(f"有效颜色: {current_color or top_card.color}")
            ui.show("你的手牌:")
            ui.show_hand(self.hand)
            ui.print_inline("你的技能: ")
            for skill in self.skills:
                ui.show_skill(skill)
                ui.print_inline(' ')
            ui.show()
        else:
            ui.show(f"\n当前牌: {top_card}  有效颜色: {current_color or top_card.color}")
            ui.show(f"{self.name}的手牌 ({len(self.hand)}张): {self.show_hand()}")
            ui.show(f"{self.name}的技能: {self.show_skills()}")

        while True:
            choice = ui.input("请选择要出的牌序号(直接回车抽牌, s发动技能, help 技能名, h帮助, q退出): ").strip()
            if choice.lower() == 'q':
                exit()
            if choice.lower() == 'h':
                ui.show("""
=== UNO 帮助 ===
- 输入序号出牌，例如输入 3 打出第 4 张手牌。
- 直接回车抽一张牌。
- 抽到的牌如果可以出，会询问你是否立刻打出 (y/n)。
- 输入 s 选择并发动主动技能。
- 输入 help 技能名 查看该技能的详细说明。
- 万能牌打出时需选择颜色（0红 1蓝 2绿 3黄）。
- 手牌数量达到上限将立即淘汰。
=================
""")
                continue
            if choice.lower().startswith('help'):
                parts = choice.split(maxsplit=1)
                if len(parts) > 1:
                    skill_name = parts[1].strip()
                    found = None
                    for s in self.skills:
                        if s.name == skill_name:
                            found = s
                            break
                    if found:
                        ui.show(f"\n=== {found.name} ===")
                        ui.show(f"类型: {found.type.name}")
                        ui.show(f"简介: {found.description}")
                        ui.show(f"详细: {found.help_text}")
                    else:
                        glossary = getattr(self.game, 'skill_glossary', {})
                        desc = glossary.get(skill_name)
                        if desc:
                            ui.show(f"\n=== {skill_name} ===")
                            ui.show(f"简介: {desc}")
                        else:
                            ui.show(f"未找到技能 '{skill_name}'。")
                else:
                    ui.show("请输入 'help 技能名' 查看技能详情")
                continue
            if choice.lower() == 's':
                usable = [s for s in self.skills if not s.is_consumed and not s.is_deleted
                          and s.type == SkillType.ACTIVE
                          and s.can_trigger(GameEvent.TURN_START, {'player': self})]
                combos = self.get_available_combos()
                if not usable and not combos:
                    ui.show("没有可主动发动的技能。")
                    continue

                ui.show("可发动的技能：")
                for i, s in enumerate(usable):
                    ui.show(f"  {i}: {s.name} - {s.description}")
                combo_start = len(usable)
                for i, (cname, _) in enumerate(combos):
                    ui.show(f"  {combo_start + i}: {cname}")

                skill_choice = ui.input("选择技能序号(取消回车): ").strip()
                if skill_choice == '':
                    continue
                try:
                    idx = int(skill_choice)
                    if 0 <= idx < len(usable):
                        skill = usable[idx]
                        self.game.skill_manager.execute_skill(skill, GameEvent.TURN_START, {'player': self})
                        continue
                    elif len(usable) <= idx < len(usable) + len(combos):
                        combo_idx = idx - len(usable)
                        self.game.skill_manager.activate_combo(combos[combo_idx][1], self)
                        continue
                except Exception:
                    pass
                continue
            if choice == '':
                return None
            try:
                idx = int(choice)
                if 0 <= idx < len(self.hand):
                    card = self.hand[idx]
                    if card.is_playable_on(top_card, current_color):
                        return idx
                    else:
                        ui.show("这张牌不能出，请重选。")
                else:
                    ui.show("序号无效。")
            except ValueError:
                ui.show("输入无效。")

    def ai_choose(self, top_card: Card, current_color: str) -> Optional[int]:
        usable = [s for s in self.skills if not s.is_consumed and not s.is_deleted
                  and s.type == SkillType.ACTIVE
                  and s.can_trigger(GameEvent.TURN_START, {'player': self})]
        if usable:
            best_skill = max(usable, key=lambda s: s.evaluate_urgency(self.game))
            if best_skill.evaluate_urgency(self.game) > 20:
                self.game.skill_manager.execute_skill(best_skill, GameEvent.TURN_START, {'player': self})
                if len(self.hand) == 0:
                    return None
        for i, card in enumerate(self.hand):
            if card.is_playable_on(top_card, current_color):
                return i
        return None

    def choose_color(self) -> str:
        if self.is_human:
            self.ui.show("选择颜色: 0红 1蓝 2绿 3黄")
            while True:
                c = self.ui.input("请输入颜色序号: ").strip()
                if c in ['0', '1', '2', '3']:
                    return Card.COLORS[int(c)]
                self.ui.show("无效。")
        else:
            color_count = {c: 0 for c in Card.COLORS}
            for card in self.hand:
                if card.color in color_count:
                    color_count[card.color] += 1
            best = max(color_count, key=color_count.get)
            return best


class SkillManager:
    def __init__(self, game: 'UNOGame'):
        self.game = game
        self.debug = game.debug

    @staticmethod
    def _safe_repr(v):
        if hasattr(v, 'name'):
            return v.name
        if isinstance(v, Skill):
            return v.name
        return v

    def trigger(self, event: GameEvent, context: Dict[str, Any] = None):
        if context is None:
            context = {}
        if self.debug:
            self.game.ui.show(f"[DEBUG] 事件触发: {event.name}")
            if context:
                simple = {}
                for k, v in context.items():
                    if k == 'activated_skill':
                        simple[k] = self._safe_repr(v)
                    elif k == 'cards_info':
                        simple[k] = v
                    else:
                        simple[k] = self._safe_repr(v) if hasattr(v, 'name') else v
                self.game.ui.show(f"        上下文: {simple}")
        for player in self.game.players:
            if player.eliminated:
                continue
            for skill in player.skills[:]:
                if skill.can_trigger(event, context):
                    if self.debug:
                        self.game.ui.show(f"        => {player.name} 的技能 {skill.name} 可触发")
                    if event == GameEvent.GAME_START:
                        skill.activate(event, context)
                        self.game.record_event('skill_use', player=skill.owner.name, skill_name=skill.name)
                    elif skill.type in (SkillType.PASSIVE, SkillType.DEATH) or event in (GameEvent.START_RANDOM, GameEvent.END_RANDOM):
                        self.execute_skill(skill, event, context)

    def execute_skill(self, skill: Skill, event: GameEvent, context: Dict[str, Any]):
        if skill.is_consumed or skill.is_deleted:
            return
        skill_ctx = {
            'activated_skill': skill,
            'skill_name': skill.name,
            'skill_activation_name': skill.name,
            'skill_type': skill.type.name,
            'event': event,
            'original_context': context,
            'cancel': False
        }
        self._query_counters(skill_ctx)
        if skill_ctx['cancel']:
            return
        skill.activate(event, context)
        self.game.record_event('skill_use', player=skill.owner.name, skill_name=skill.name)

    def _query_counters(self, skill_ctx: Dict[str, Any]):
        event = GameEvent.SKILL_ACTIVATED
        skill = skill_ctx['activated_skill']
        for player in self.game.players:
            if player.eliminated:
                continue
            for skill_obj in player.skills[:]:
                if skill_obj.can_trigger(event, skill_ctx):
                    if player.is_human:
                        ans = player.ui.input(f"{player.name}，你有技能 {skill_obj.name} 可用，是否发动？(y/n): ").strip().lower()
                        if ans == 'y':
                            skill_obj.activate(event, skill_ctx)
                            self.game.record_event('skill_use', player=skill_obj.owner.name, skill_name=skill_obj.name)
                            if skill_ctx.get('cancel'):
                                return
                    else:
                        if random.random() < 0.6:
                            player.ui.show(f"{player.name} 发动 {skill_obj.name} 进行反制！")
                            skill_obj.activate(event, skill_ctx)
                            self.game.record_event('skill_use', player=skill_obj.owner.name, skill_name=skill_obj.name)
                            if skill_ctx.get('cancel'):
                                return

    def ask_human_intercept(self, player: Player, event: GameEvent, context: Dict[str, Any]) -> bool:
        intercept = [s for s in player.skills if not s.is_consumed and not s.is_deleted
                     and s.type == SkillType.ACTIVE and s.can_trigger(event, context)]
        if not intercept:
            return False
        player.ui.show(f"{player.name}，你受到加牌，可以使用以下技能：")
        for i, s in enumerate(intercept):
            player.ui.show(f"  {i}: {s.name} - {s.description}")
        choice = player.ui.input("选择技能序号（取消回车）: ").strip()
        if choice == '':
            return False
        try:
            idx = int(choice)
            if 0 <= idx < len(intercept):
                skill = intercept[idx]
                skill.activate(event, context)
                self.game.record_event('skill_use', player=skill.owner.name, skill_name=skill.name)
                return True
        except Exception:
            pass
        return False

    def activate_combo(self, combo_effect_class: type, player: Player):
        combo = combo_effect_class()
        combo.execute(player, self, self.game)
        self.game.record_event('combo_use', player=player.name, combo_name=combo_effect_class.__name__)


class UNOGame:
    def __init__(self, human_name: str = "你", enabled_seasons: List[str] = None, debug: bool = False,
                 dev_skills: Dict[str, List[type]] = None, use_rich_ui: bool = False,
                 recorder: 'GameRecorder' = None, players: List[str] = None,
                 human_ui: ConsoleUI = None, ai_ui: ConsoleUI = None,
                 hand_limit: int = 15, initial_hand_size: int = 7, initial_skill_count: int = 3):
        if enabled_seasons is None:
            enabled_seasons = ['S1']
        enabled_seasons = list(set(enabled_seasons))
        self.debug = debug
        self.recorder = recorder
        self.hand_limit = hand_limit
        self.initial_hand_size = initial_hand_size
        self.initial_skill_count = initial_skill_count

        if human_ui is not None:
            self.ui = human_ui
        else:
            if use_rich_ui:
                try:
                    self.ui = RichUI()
                except Exception:
                    print("RichUI 加载失败，将使用普通界面。")
                    self.ui = ConsoleUI()
            else:
                self.ui = ConsoleUI()

        if ai_ui is None:
            ai_ui = NullUI()

        if players and len(players) >= 2:
            self.hotseat = True
            self.players = [Player(name, is_human=True, ui=self.ui) for name in players]
        else:
            self.hotseat = False
            self.players = [
                Player(human_name, is_human=True, ui=self.ui),
                Player("电脑A", ui=ai_ui),
                Player("电脑B", ui=ai_ui),
                Player("电脑C", ui=ai_ui)
            ]

        for p in self.players:
            p.hand_limit = self.hand_limit

        self.discard_pile: List[Card] = []
        self.deck = Deck(self.discard_pile, ui=self.ui)
        self.current_color: str = None
        self.direction = 1
        self.current_player_idx = 0
        self.game_started = False
        self.dev_skills = dev_skills or {}
        self.turn_number = 0
        self.event_log = []

        from .skills_uno import SkillLoader
        self.skill_pool, self.skill_glossary, mod_achievements = SkillLoader.load_skills(enabled_seasons, self)
        self.skill_manager = SkillManager(self)

        self.achievements = AchievementManager(self, get_core_achievements())
        self.achievements.add_achievements(mod_achievements)

    def broadcast(self, message: str):
        seen_ids = set()
        for p in self.players:
            if p.eliminated:
                continue
            ui = p.ui
            if isinstance(ui, NullUI):
                continue
            if id(ui) in seen_ids:
                continue
            seen_ids.add(id(ui))
            ui.show(message)

    def record_event(self, event_type: str, **kwargs):
        record = {'type': event_type, **kwargs}
        self.event_log.append(record)
        if self.recorder:
            try:
                self.recorder.record(event_type, **kwargs)
            except Exception as e:
                if self.debug:
                    self.ui.show(f"[DEBUG] recorder.record 失败：{e}")

    def setup(self):
        for player in self.players:
            for _ in range(self.initial_skill_count):
                available = [s for s in self.skill_pool if s.owner is None]
                if available:
                    skill = available.pop()
                    skill.owner = player
                    player.skills.append(skill)
                    self.skill_pool.remove(skill)
                else:
                    break

        for player in self.players:
            player.hand = [self.deck.draw(1) for _ in range(self.initial_hand_size)]

        while True:
            first_card = self.deck.draw(1)
            self.discard_pile.append(first_card)
            if first_card.type == '数字':
                break
            self.ui.show(f"起始牌为功能牌 {first_card}，重新翻牌。")
            self.deck.cards.append(first_card)
            self.deck.shuffle()
            self.discard_pile.pop()
        self.current_color = first_card.color
        self.ui.show(f"起始牌: {first_card}")

        self.skill_manager.trigger(GameEvent.GAME_START)

        for player_name, skill_classes in self.dev_skills.items():
            for p in self.players:
                if p.name == player_name and not p.eliminated:
                    p.skills.clear()
                    for cls in skill_classes:
                        skill = cls(owner=p, game=self)
                        p.skills.append(skill)
                    self.ui.show(f"[DEV] 已覆写 {p.name} 的技能：{[s.name for s in p.skills]}")
                    break

        if self.discard_pile:
            top = self.discard_pile[-1]
            if top.color != '黑':
                self.current_color = top.color

        self.game_started = True

    def next_player(self, step: int = 1):
        total = len(self.players)
        for _ in range(total):
            self.current_player_idx = (self.current_player_idx + self.direction * step) % total
            if not self.players[self.current_player_idx].eliminated:
                return

    def peek_next_player(self, step: int = 1) -> Optional[Player]:
        idx = self.current_player_idx
        total = len(self.players)
        for _ in range(total):
            idx = (idx + self.direction * step) % total
            if not self.players[idx].eliminated:
                return self.players[idx]
        return None

    def current_player(self) -> Player:
        return self.players[self.current_player_idx]

    def check_winner(self) -> Optional[Player]:
        active = [p for p in self.players if not p.eliminated]
        for p in active:
            if len(p.hand) == 0:
                return p
        if len(active) == 1:
            return active[0]
        return None

    def apply_add_cards(self, target: Player, amount: int):
        if self.debug:
            self.ui.show(f"[DEBUG] apply_add_cards: 目标 {target.name}, 数量 {amount}")

        context = {
            'target': target,
            'amount': amount,
            'add_multiplier': 1.0,
            'cancel': False
        }
        self.skill_manager.trigger(GameEvent.BEING_ADDED_CARDS, context)

        if target.is_human and not context['cancel']:
            self.skill_manager.ask_human_intercept(target, GameEvent.BEING_ADDED_CARDS, context)

        if context['cancel']:
            self.broadcast("加牌效果被取消。")
            return

        final_amount = int(amount * context['add_multiplier'])
        if final_amount <= 0:
            self.broadcast(f"加牌倍数导致数量为 {final_amount}，无牌可加。")
            return

        final_target = context['target']
        try:
            cards = self.deck.draw(final_amount) if final_amount > 1 else [self.deck.draw(1)]
        except Exception:
            self.broadcast("牌堆耗尽，无法加牌。")
            return
        final_target.draw_cards(cards)
        self.broadcast(f"{final_target.name} 抽了 {final_amount} 张牌。")

        cards_info = []
        for c in cards:
            info = [c.color, c.value if c.type == '数字' else None, c.type if c.type != '数字' else None]
            cards_info.append(info)

        self.record_event('add_cards', target=final_target.name, amount=final_amount, cards=cards_info)

        self.skill_manager.trigger(GameEvent.CARDS_ADDED, {
            'target': final_target, 'amount': final_amount,
            'add_multiplier': context['add_multiplier'], 'cards_info': cards_info
        })

        if final_target.hand_size() > final_target.hand_limit:
            final_target.eliminate(self)
            self.skill_manager.trigger(GameEvent.PLAYER_DIED, {'player': final_target})

    def show_opponent_hand_counts(self):
        counts = []
        for p in self.players:
            if p != self.current_player() and not p.eliminated:
                counts.append(f"{p.name}:{p.hand_size()}张")
        if counts:
            self.broadcast("  [" + " | ".join(counts) + "]")

    def show_hand_colors(self):
        if self.debug:
            self.ui.show("[DEBUG] 各玩家手牌颜色分布:")
            for p in self.players:
                if p.eliminated:
                    continue
                color_count = {c: 0 for c in ['红', '蓝', '绿', '黄']}
                wild_count = 0
                for card in p.hand:
                    if card.type in ['万能', '万能+4']:
                        wild_count += 1
                    elif card.color in color_count:
                        color_count[card.color] += 1
                parts = [f"{col}:{cnt}" for col, cnt in color_count.items()]
                parts.append(f"万能:{wild_count}")
                self.ui.show(f"  {p.name}({len(p.hand)}张): {', '.join(parts)}")

    def uno_reminder(self, player: Player):
        if len(player.hand) != 1:
            return
        if isinstance(self.ui, RichUI):
            self.ui.show_uno_reminder(player)
        else:
            self.broadcast(f"🔔 {player.name} 喊了 UNO！")

    def apply_card_effect(self, player: Player, card: Card) -> bool:
        self.skill_manager.trigger(GameEvent.BEFORE_PLAY, {'player': player, 'card': card})
        skip = False
        if card.type == '跳过':
            self.broadcast(f"{player.name} 打出 跳过")
            skip = True
        elif card.type == '反转':
            self.broadcast(f"{player.name} 打出 反转")
            self.direction *= -1
            active_count = len([p for p in self.players if not p.eliminated])
            if active_count == 2:
                skip = True
        elif card.type == '+2':
            self.broadcast(f"{player.name} 打出 +2")
            next_p = self.peek_next_player()
            if next_p:
                self.apply_add_cards(next_p, 2)
            skip = True
        elif card.type == '万能':
            self.broadcast(f"{player.name} 打出 万能")
            new_color = player.choose_color()
            self.current_color = new_color
        elif card.type == '万能+4':
            self.broadcast(f"{player.name} 打出 万能+4")
            new_color = player.choose_color()
            self.current_color = new_color
            next_p = self.peek_next_player()
            if next_p:
                self.apply_add_cards(next_p, 4)
            skip = True
        self.skill_manager.trigger(GameEvent.AFTER_PLAY, {'player': player, 'card': card})
        return skip

    def play_turn(self):
        player = self.current_player()
        if player.eliminated:
            self.next_player()
            return

        self.turn_number += 1
        self.record_event('turn_start', player=player.name, turn_number=self.turn_number,
                          hand_size=player.hand_size(), current_color=self.current_color)

        if isinstance(self.ui, RichUI):
            self.ui.show_turn_header(player)
        else:
            self.broadcast(f"\n===== {player.name} 的回合 =====")

        self.show_opponent_hand_counts()
        if self.debug:
            self.ui.show("[DEBUG] 当前所有玩家技能:")
            for p in self.players:
                if not p.eliminated:
                    self.ui.show(f"  {p.name}: {', '.join(p.show_skills())}")
            self.show_hand_colors()

        self.skill_manager.trigger(GameEvent.TURN_START, {'player': player})
        if self.check_winner():
            return

        top_card = self.discard_pile[-1]
        chosen_idx = player.choose_play(top_card, self.current_color, self)
        if chosen_idx is None:
            drawn = self.deck.draw(1)
            player.hand.append(drawn)
            self.record_event('draw_card', player=player.name, card=str(drawn),
                              hand_after=player.hand_size())
            self.broadcast(f"{player.name} 抽了一张牌: {drawn}")
            if player.hand_size() > player.hand_limit:
                player.eliminate(self)
                self.skill_manager.trigger(GameEvent.PLAYER_DIED, {'player': player})
                return
            if player.is_human and drawn.is_playable_on(top_card, self.current_color):
                ans = self.ui.input("抽到的牌可以出，要打出吗？(y/n, 默认n): ").strip().lower()
                if ans == 'y':
                    player.hand.pop()
                    card = drawn
                    self.discard_pile.append(card)
                    self.record_event('play_card', player=player.name, card=str(card),
                                      hand_after=player.hand_size())
                    self.broadcast(f"{player.name} 打出了抽到的牌: {card}")
                    skip = self.apply_card_effect(player, card)
                    self.uno_reminder(player)
                    if self.check_winner():
                        return
                    self.next_player(2 if skip else 1)
                    return
            elif not player.is_human and drawn.is_playable_on(top_card, self.current_color):
                player.hand.pop()
                card = drawn
                self.discard_pile.append(card)
                self.record_event('play_card', player=player.name, card=str(card),
                                  hand_after=player.hand_size())
                self.broadcast(f"{player.name} 打出了抽到的牌: {card}")
                skip = self.apply_card_effect(player, card)
                self.uno_reminder(player)
                if self.check_winner():
                    return
                self.next_player(2 if skip else 1)
                return
            self.next_player()
        else:
            card = player.hand.pop(chosen_idx)
            self.discard_pile.append(card)
            self.record_event('play_card', player=player.name, card=str(card),
                              hand_after=player.hand_size())
            if isinstance(self.ui, RichUI):
                self.ui.print_inline(f"{player.name} 打出: ")
                self.ui.show_card(card)
            else:
                self.broadcast(f"{player.name} 打出: {card}")
            if card.type not in ['万能', '万能+4']:
                self.current_color = card.color
            skip = self.apply_card_effect(player, card)
            self.uno_reminder(player)
            if self.check_winner():
                return
            self.next_player(2 if skip else 1)

    def _end_single_game(self, human: Player, winner: Player):
        from .archive import update_record, show_record
        if winner == human:
            self.broadcast(f"\n🎉 {human.name} 获胜！")
        else:
            self.broadcast(f"\n{winner.name} 获胜！")
            self.broadcast(f"💀 {human.name} 失败了。")
        self.record_event('game_end', winner=winner.name)
        achievements = self.achievements.evaluate(self.event_log)
        update_record(human.name, winner == human, list(achievements))
        show_record(human.name)

    def _end_hotseat_game(self, winner: Optional[Player]):
        from .archive import update_record, show_record

        if winner:
            self.broadcast(f"\n🎉 {winner.name} 获胜！")
            self.record_event('game_end', winner=winner.name)
        else:
            self.broadcast("\n游戏结束，没有胜者。")
            self.record_event('game_end', winner='?')

        for p in self.players:
            if not p.is_human:
                continue
            update_record(p.name, p == winner, [])
            show_record(p.name)

    def run(self):
        self.setup()
        self.current_player_idx = 0
        primary_human = None if self.hotseat else self.players[0]

        top_card_str = str(self.discard_pile[-1]) if self.discard_pile else ""
        if self.recorder:
            self.recorder.players = [p.name for p in self.players]
            self.recorder.seasons = list(self.skill_glossary.keys())[:1]
            self.recorder.initial_top_card = top_card_str
        self.record_event("game_start", top_card=top_card_str)

        while True:
            if self.hotseat:
                active = [p for p in self.players if not p.eliminated]
                if len(active) <= 1:
                    self._end_hotseat_game(active[0] if active else None)
                    break
            else:
                if primary_human.eliminated:
                    self.broadcast(f"\n💀 {primary_human.name} 被淘汰了！")
                    survivors = [p for p in self.players if not p.eliminated]
                    winner_name = survivors[0].name if survivors else '?'
                    self.record_event('game_end', winner=winner_name)
                    from .archive import update_record, show_record
                    achievements = self.achievements.evaluate(self.event_log)
                    update_record(primary_human.name, False, list(achievements))
                    show_record(primary_human.name)
                    break

            winner = self.check_winner()
            if winner:
                if self.hotseat:
                    self._end_hotseat_game(winner)
                else:
                    self._end_single_game(primary_human, winner)
                break

            self.play_turn()

        if self.recorder:
            saved_path = self.recorder.save()
            self.broadcast(f"录像已保存至 {saved_path}")