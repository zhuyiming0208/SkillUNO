import sys
import os
import unittest
from unittest.mock import patch, MagicMock

# ==================== 路径配置 ====================
# 本测试文件位于 SkillUNO/tests/test_all.py
# 需要把 SkillUNO/src 加入 sys.path，才能 import uno
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)          # SkillUNO/
SRC_DIR = os.path.join(PROJECT_ROOT, 'src')          # SkillUNO/src/
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from uno.core import (
    Card, Deck, Player, Skill, SkillType, GameEvent,
    UNOGame, SkillManager, ConsoleUI, NullUI, RichUI
)
from uno.replay import GameRecorder, GameReplayer
from uno.skills_uno import SkillLoader
from uno.achievements import (
    AchievementManager, get_core_achievements,
    Comeback1v3Achievement, CounterMasterAchievement,
    InstantKillAchievement, NoDrawVictoryAchievement
)
import uno.season1 as season1
import uno.season2 as season2
import uno.season4 as season4


# ==================== 卡牌逻辑 ====================
class TestCard(unittest.TestCase):
    def test_playable_same_color(self):
        top = Card('红', '数字', 5)
        card = Card('红', '数字', 3)
        self.assertTrue(card.is_playable_on(top))

    def test_playable_same_number(self):
        top = Card('蓝', '数字', 5)
        card = Card('红', '数字', 5)
        self.assertTrue(card.is_playable_on(top))

    def test_playable_wild(self):
        top = Card('黄', '数字', 7)
        card = Card('黑', '万能')
        self.assertTrue(card.is_playable_on(top))

    def test_not_playable(self):
        top = Card('绿', '数字', 7)
        card = Card('红', '数字', 2)
        self.assertFalse(card.is_playable_on(top))

    def test_playable_same_action(self):
        top = Card('蓝', '+2')
        card = Card('红', '+2')
        self.assertTrue(card.is_playable_on(top))


# ==================== 牌堆 ====================
class TestDeck(unittest.TestCase):
    def test_initial_size(self):
        deck = Deck()
        self.assertEqual(len(deck.cards), 108)

    def test_draw_reduces_size(self):
        deck = Deck()
        size_before = len(deck.cards)
        deck.draw()
        self.assertEqual(len(deck.cards), size_before - 1)

    def test_reshuffle_uses_discard(self):
        discard = [Card('红', '数字', 1), Card('蓝', '数字', 2)]
        deck = Deck(discard_pile=discard)
        deck.cards = []  # 强制空
        drawn = deck.draw()  # 触发重洗
        self.assertIsNotNone(drawn)
        # 重洗后弃牌堆应只保留顶部一张
        self.assertEqual(len(deck.discard), 1)

    def test_draw_one_and_many(self):
        deck = Deck()
        one = deck.draw_one()
        self.assertIsInstance(one, Card)
        many = deck.draw_many(3)
        self.assertEqual(len(many), 3)
        self.assertTrue(all(isinstance(c, Card) for c in many))


# ==================== 玩家 ====================
class TestPlayer(unittest.TestCase):
    def setUp(self):
        self.ui = ConsoleUI()
        self.player = Player("测试", is_human=False, ui=self.ui)

    def test_hand_limit(self):
        self.player.hand = [Card('红', '数字', i) for i in range(15)]
        game = UNOGame(debug=False, use_rich_ui=False)
        game.players = [self.player]
        with patch('builtins.print'):
            self.player.eliminate(game)
        self.assertTrue(self.player.eliminated)
        self.assertEqual(len(self.player.hand), 0)

    def test_skill_display(self):
        s = Skill('测试技能', SkillType.ACTIVE, '描述', owner=self.player)
        self.player.skills.append(s)
        self.assertEqual(self.player.show_skills(), ['测试技能'])
        s.is_consumed = True
        self.assertEqual(self.player.show_skills(), ['测试技能(已用)'])
        s.is_deleted = True
        self.assertEqual(self.player.show_skills(), ['???'])


# ==================== 技能管理器 ====================
class TestSkillManager(unittest.TestCase):
    def setUp(self):
        self.game = UNOGame(debug=False, use_rich_ui=False)
        self.game.skill_manager = SkillManager(self.game)

    def test_trigger_auto_skill(self):
        class FakeSkill(Skill):
            def __init__(self, game):
                super().__init__('测试', SkillType.ACTIVE, 'desc',
                                 owner=game.players[0], game=game)
                self.triggered = False

            def can_trigger(self, event, context):
                return event == GameEvent.GAME_START

            def activate(self, event, context):
                self.triggered = True
                return True

        skill = FakeSkill(self.game)
        self.game.players[0].skills.append(skill)
        self.game.skill_manager.trigger(GameEvent.GAME_START)
        self.assertTrue(skill.triggered)

    def test_intercept_ask_human(self):
        class InterceptSkill(Skill):
            def can_trigger(self, event, context):
                return True

            def activate(self, event, context):
                return True

        player = self.game.players[0]
        player.is_human = True
        skill = InterceptSkill('拦截', SkillType.ACTIVE, 'desc', owner=player)
        player.skills.append(skill)
        with patch('builtins.input', return_value='0'):
            result = self.game.skill_manager.ask_human_intercept(
                player, GameEvent.BEING_ADDED_CARDS,
                {'target': player, 'amount': 2}
            )
        self.assertTrue(result)


# ==================== 游戏流程 ====================
class TestGameFlow(unittest.TestCase):
    def test_full_ai_game(self):
        """运行一局完全由 AI 进行的游戏，确保不崩溃"""
        game = UNOGame(debug=False, use_rich_ui=False)
        for p in game.players:
            p.is_human = False
        for p in game.players:
            p.hand_limit = 5
        with patch('builtins.input', return_value=''):
            game.run()
        self.assertTrue(any(p.hand_size() == 0 or p.eliminated for p in game.players))

    def test_add_cards_with_multiplier(self):
        game = UNOGame(debug=False, use_rich_ui=False)
        player = game.players[0]
        player.hand_limit = 100
        initial_hand = len(player.hand)
        game.apply_add_cards(player, 2)
        self.assertEqual(len(player.hand), initial_hand + 2)

    def test_dev_skills(self):
        from uno.season1 import PoWanFa, ZhaoZai
        dev = {'你': [PoWanFa, ZhaoZai]}
        game = UNOGame(debug=False, use_rich_ui=False, dev_skills=dev)
        game.setup()
        self.assertEqual([s.name for s in game.players[0].skills], ['破万法', '招灾'])

    def test_custom_room_rules(self):
        game = UNOGame(
            debug=False,
            use_rich_ui=False,
            hand_limit=10,
            initial_hand_size=5,
            initial_skill_count=1
        )
        game.setup()
        for p in game.players:
            self.assertEqual(p.hand_limit, 10)
            self.assertEqual(len(p.hand), 5)
            self.assertEqual(len(p.skills), 1)

    def test_hotseat_mode_creation(self):
        players = ['Alice', 'Bob']
        game = UNOGame(debug=False, use_rich_ui=False, players=players)
        self.assertTrue(game.hotseat)
        self.assertEqual(len(game.players), 2)
        for p in game.players:
            self.assertTrue(p.is_human)

    def test_ui_decoupling(self):
        """human_ui 与 ai_ui 应分别应用到不同玩家"""
        from uno.ui import ConsoleUI, NullUI
        human_ui = ConsoleUI()
        ai_ui = NullUI()
        game = UNOGame(
            "你", ['S1'],
            use_rich_ui=False,
            human_ui=human_ui,
            ai_ui=ai_ui
        )
        self.assertIs(game.players[0].ui, human_ui)
        for p in game.players[1:]:
            self.assertIs(p.ui, ai_ui)


# ==================== 加载器 ====================
class TestLoader(unittest.TestCase):
    """依赖、排斥、容忍测试（使用真实临时 Mod 文件）"""

    def setUp(self):
        # mods 目录位于 SkillUNO/mods
        self.mods_dir = os.path.join(PROJECT_ROOT, 'mods')
        os.makedirs(self.mods_dir, exist_ok=True)
        # 确保 mods 是 Python 包
        mods_init = os.path.join(self.mods_dir, '__init__.py')
        if not os.path.exists(mods_init):
            open(mods_init, 'w').close()
        self.temp_files = []

    def tearDown(self):
        for f in self.temp_files:
            if os.path.exists(f):
                os.remove(f)

    def _create_mod_file(self, filename, content):
        path = os.path.join(self.mods_dir, filename)
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        self.temp_files.append(path)
        return path

    def test_dependency_missing(self):
        self._create_mod_file('test_mod_dep.py', """
SEASON_ID = "MOD_DEP"
SEASON_NAME = "依赖测试"
RELY_ON = ("S2", "需要 S2 的技能")
SKILL_CLASSES = []
""")
        skills, glossary, ach = SkillLoader.load_skills(
            ['MOD_DEP'], UNOGame(debug=False, use_rich_ui=False)
        )
        self.assertEqual(skills, [])

    def test_reject_conflict(self):
        self._create_mod_file('test_mod_reject.py', """
SEASON_ID = "MOD_REJ"
SEASON_NAME = "排斥测试"
REJECT = {"S1": "冲突"}
SKILL_CLASSES = []
""")
        skills, glossary, ach = SkillLoader.load_skills(
            ['S1', 'MOD_REJ'], UNOGame(debug=False, use_rich_ui=False)
        )
        self.assertEqual(skills, [])

    def test_tolerate(self):
        self._create_mod_file('test_mod_tolerate.py', """
SEASON_ID = "MOD_TOL"
SEASON_NAME = "容忍测试"
ONLY_TOLERATE = ("S1",)
SKILL_CLASSES = []
""")
        skills, glossary, ach = SkillLoader.load_skills(
            ['S1', 'S2', 'MOD_TOL'], UNOGame(debug=False, use_rich_ui=False)
        )
        # S2 应被排除，因此不应包含 S2 的专属技能（如始皇帝）
        self.assertFalse(any(s.name == '始皇帝' for s in skills))


# ==================== 成就系统 ====================
class TestAchievements(unittest.TestCase):
    def _create_mock_game(self):
        game = MagicMock()
        human = MagicMock()
        human.name = '你'
        computer1 = MagicMock()
        computer1.name = '电脑A'
        computer2 = MagicMock()
        computer2.name = '电脑B'
        computer3 = MagicMock()
        computer3.name = '电脑C'
        game.players = [human, computer1, computer2, computer3]
        return game

    def test_no_draw_victory(self):
        game = self._create_mock_game()
        events = [{'type': 'game_end', 'winner': '你'}]
        ach = NoDrawVictoryAchievement()
        self.assertTrue(ach.check(game, events))

    def test_no_draw_victory_fail_with_draw(self):
        game = self._create_mock_game()
        events = [
            {'type': 'draw_card', 'player': '你', 'card': '红1'},
            {'type': 'game_end', 'winner': '你'}
        ]
        ach = NoDrawVictoryAchievement()
        self.assertFalse(ach.check(game, events))

    def test_comeback_1v3(self):
        game = self._create_mock_game()
        events = [
            {'type': 'player_eliminated', 'player': '电脑A', 'reason': 'hand_limit', 'turn_number': 5},
            {'type': 'player_eliminated', 'player': '电脑B', 'reason': 'hand_limit', 'turn_number': 10},
            {'type': 'player_eliminated', 'player': '电脑C', 'reason': 'hand_limit', 'turn_number': 15},
            {'type': 'game_end', 'winner': '你'}
        ]
        ach = Comeback1v3Achievement()
        self.assertTrue(ach.check(game, events))

    def test_comeback_1v3_fail_human_eliminated(self):
        game = self._create_mock_game()
        events = [
            {'type': 'player_eliminated', 'player': '你', 'reason': 'hand_limit', 'turn_number': 1},
            {'type': 'game_end', 'winner': '电脑A'}
        ]
        ach = Comeback1v3Achievement()
        self.assertFalse(ach.check(game, events))

    def test_counter_master(self):
        game = self._create_mock_game()
        events = [
            {'type': 'skill_use', 'player': '你', 'skill_name': '破万法'},
            {'type': 'skill_use', 'player': '你', 'skill_name': '储能'},
            {'type': 'skill_use', 'player': '你', 'skill_name': '破万法'},
        ]
        ach = CounterMasterAchievement()
        self.assertTrue(ach.check(game, events))

    def test_counter_master_fail_less_than_3(self):
        game = self._create_mock_game()
        events = [
            {'type': 'skill_use', 'player': '你', 'skill_name': '破万法'},
            {'type': 'skill_use', 'player': '你', 'skill_name': '储能'},
        ]
        ach = CounterMasterAchievement()
        self.assertFalse(ach.check(game, events))

    def test_instant_kill(self):
        game = self._create_mock_game()
        events = [
            {'type': 'player_eliminated', 'player': '电脑A', 'reason': 'hand_limit', 'turn_number': 1},
        ]
        ach = InstantKillAchievement()
        self.assertTrue(ach.check(game, events))

    def test_instant_kill_fail_later_turn(self):
        game = self._create_mock_game()
        events = [
            {'type': 'player_eliminated', 'player': '电脑A', 'reason': 'hand_limit', 'turn_number': 3},
        ]
        ach = InstantKillAchievement()
        self.assertFalse(ach.check(game, events))

    def test_achievement_manager_registers_all(self):
        game = self._create_mock_game()
        manager = AchievementManager(game, get_core_achievements())
        # 至少包含 4 个核心成就
        self.assertGreaterEqual(len(manager.achievements), 4)


# ==================== 回放 ====================
class TestReplay(unittest.TestCase):
    def test_recorder_save_load(self):
        recorder = GameRecorder()
        recorder.players = ['你', '电脑A']
        recorder.seasons = ['S1']
        recorder.initial_top_card = '红5'
        recorder.record('turn_start', player='你', hand_size=7)
        recorder.record('play_card', player='你', card='红5')
        recorder.record('game_end', winner='你')
        path = recorder.save()
        self.assertTrue(os.path.exists(path))

        ui = ConsoleUI()
        replayer = GameReplayer(path, ui)
        self.assertEqual(replayer.data['players'], ['你', '电脑A'])
        events = []
        while True:
            ev = replayer.next_event()
            if ev is None:
                break
            events.append(ev)
        self.assertEqual(len(events), 3)

        os.remove(path)


# ==================== 入口 ====================
if __name__ == '__main__':
    unittest.main()