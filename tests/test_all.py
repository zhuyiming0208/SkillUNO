"""
SkillUNO 完整测试套件（pytest 风格）

运行：
    cd /storage/emulated/0/AGHSU/SkillUNO
    python -m pytest tests/ -v

带覆盖率：
    python -m pytest tests/ -v --cov=src/uno --cov-report=term-missing
"""
import sys
import os
import base64
import json
import tempfile
from unittest.mock import MagicMock, patch

import pytest

# ==================== 路径配置 ====================
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)                # SkillUNO/
SRC_DIR = os.path.join(PROJECT_ROOT, 'src')                # SkillUNO/src/
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
import uno.presets as presets_module
import uno.season1 as season1
import uno.season2 as season2
import uno.season3 as season3
import uno.season4 as season4


# ==================== 共享 Fixtures ====================
@pytest.fixture
def mock_game():
    """构造一个 UI 完全被 mock 的游戏对象，默认所有玩家为 AI，避免 input() 阻塞。"""
    game = UNOGame(debug=False, use_rich_ui=False, enabled_seasons=['S1'])
    game.ui = MagicMock()
    for p in game.players:
        p.ui = MagicMock()
        p.is_human = False
    return game


@pytest.fixture
def owner(mock_game):
    """返回 AI 玩家（players[0]），避免卡 input()。"""
    return mock_game.players[0]


@pytest.fixture
def other_player(mock_game):
    return mock_game.players[1]


@pytest.fixture
def human_player(mock_game):
    """显式需要人类分支时使用，自动 mock input。"""
    p = mock_game.players[0]
    p.is_human = True
    p.ui.input = MagicMock(return_value='0')
    return p


@pytest.fixture
def clean_presets_file(tmp_path, monkeypatch):
    """把 presets.PRESET_FILE 指向一个临时文件，避免污染真实数据。"""
    fake_file = tmp_path / "presets.json"
    monkeypatch.setattr(presets_module, 'PRESET_FILE', str(fake_file))
    return fake_file


# ==================== 防回归 Smoke Test ====================
class TestFixtureSafety:
    def test_mock_game_owner_is_ai(self, mock_game):
        for p in mock_game.players:
            assert p.is_human is False

    def test_human_player_fixture_is_human(self, human_player):
        assert human_player.is_human is True


# ==================== Card ====================
class TestCard:
    def test_playable_same_color(self):
        top = Card('红', '数字', 5)
        assert Card('红', '数字', 3).is_playable_on(top)

    def test_playable_same_number(self):
        top = Card('蓝', '数字', 5)
        assert Card('红', '数字', 5).is_playable_on(top)

    def test_playable_wild(self):
        top = Card('黄', '数字', 7)
        assert Card('黑', '万能').is_playable_on(top)

    def test_not_playable(self):
        top = Card('绿', '数字', 7)
        assert not Card('红', '数字', 2).is_playable_on(top)

    def test_playable_same_action(self):
        top = Card('蓝', '+2')
        assert Card('红', '+2').is_playable_on(top)

    def test_repr_number(self):
        assert repr(Card('红', '数字', 5)) == '红5'

    def test_repr_wild(self):
        assert repr(Card('黑', '万能')) == '万能'
        assert repr(Card('黑', '万能+4')) == '万能+4'

    def test_repr_action(self):
        assert repr(Card('蓝', '跳过')) == '蓝跳过'
        assert repr(Card('绿', '反转')) == '绿反转'


# ==================== Deck ====================
class TestDeck:
    def test_initial_size(self):
        assert len(Deck().cards) == 108

    def test_draw_reduces_size(self):
        deck = Deck()
        before = len(deck.cards)
        deck.draw()
        assert len(deck.cards) == before - 1

    def test_reshuffle_uses_discard(self):
        discard = [Card('红', '数字', 1), Card('蓝', '数字', 2)]
        deck = Deck(discard_pile=discard)
        deck.cards = []
        drawn = deck.draw()
        assert drawn is not None
        assert len(deck.discard) == 1

    def test_draw_one_and_many(self):
        deck = Deck()
        assert isinstance(deck.draw_one(), Card)
        many = deck.draw_many(3)
        assert len(many) == 3
        assert all(isinstance(c, Card) for c in many)

    def test_reshuffle_empty_discard_raises(self):
        deck = Deck()
        deck.cards = []
        deck.discard.clear()
        with pytest.raises(Exception):
            deck.draw()


# ==================== Player ====================
class TestPlayer:
    def test_hand_limit(self, mock_game):
        p = mock_game.players[0]
        p.hand = [Card('红', '数字', i) for i in range(15)]
        mock_game.players = [p]
        with patch.object(mock_game, 'broadcast'):
            p.eliminate(mock_game)
        assert p.eliminated
        assert len(p.hand) == 0

    def test_skill_display(self, owner):
        s = Skill('测试技能', SkillType.ACTIVE, '描述', owner=owner)
        owner.skills = [s]
        assert owner.show_skills() == ['测试技能']
        s.is_consumed = True
        assert owner.show_skills() == ['测试技能(已用)']
        s.is_deleted = True
        assert owner.show_skills() == ['???']

    def test_show_hand(self, owner):
        owner.hand = [Card('红', '数字', 1), Card('蓝', '数字', 2)]
        text = owner.show_hand()
        assert '红1' in text
        assert '蓝2' in text

    def test_choose_color_ai_picks_most(self, owner):
        """owner 强制为 AI，避免走 input() 分支卡住。"""
        owner.is_human = False
        owner.hand = [Card('红', '数字', 1), Card('红', '数字', 2),
                      Card('蓝', '数字', 3)]
        assert owner.choose_color() == '红'

    def test_get_available_combos_empty(self, owner):
        owner.skills = []
        assert owner.get_available_combos() == []

    def test_draw_cards(self, owner):
        owner.hand = []
        owner.draw_cards([Card('红', '数字', 1), Card('蓝', '数字', 2)])
        assert len(owner.hand) == 2


# ==================== SkillManager ====================
class TestSkillManager:
    def test_trigger_auto_skill(self, mock_game):
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

        skill = FakeSkill(mock_game)
        mock_game.players[0].skills.append(skill)
        mock_game.skill_manager.trigger(GameEvent.GAME_START)
        assert skill.triggered

    def test_intercept_ask_human(self, mock_game, human_player):
        class InterceptSkill(Skill):
            def can_trigger(self, event, context):
                return True

            def activate(self, event, context):
                return True

        skill = InterceptSkill('拦截', SkillType.ACTIVE, 'desc', owner=human_player)
        human_player.skills = [skill]
        result = mock_game.skill_manager.ask_human_intercept(
            human_player, GameEvent.BEING_ADDED_CARDS,
            {'target': human_player, 'amount': 2}
        )
        assert result is True

    def test_intercept_no_skills_returns_false(self, mock_game):
        player = mock_game.players[0]
        player.skills = []
        result = mock_game.skill_manager.ask_human_intercept(
            player, GameEvent.BEING_ADDED_CARDS,
            {'target': player, 'amount': 2}
        )
        assert result is False

    def test_execute_skill_skips_consumed(self, mock_game):
        skill = Skill('测试', SkillType.ACTIVE, 'desc',
                      owner=mock_game.players[0], game=mock_game)
        skill.is_consumed = True
        mock_game.skill_manager.execute_skill(skill, GameEvent.TURN_START, {})

    def test_activate_combo(self, mock_game):
        from uno.combo_base import ComboBase
        called = []

        class TestCombo(ComboBase):
            def execute(self, player, skill_manager, game):
                called.append(player.name)

        player = mock_game.players[0]
        mock_game.skill_manager.activate_combo(TestCombo, player)
        assert called == [player.name]
        assert any(e['type'] == 'combo_use' for e in mock_game.event_log)


# ==================== 游戏机制 ====================
class TestGameMechanics:
    def test_next_player_basic(self, mock_game):
        for p in mock_game.players:
            p.eliminated = False
        mock_game.current_player_idx = 0
        mock_game.next_player()
        assert mock_game.current_player_idx == 1

    def test_next_player_skips_eliminated(self, mock_game):
        for p in mock_game.players:
            p.eliminated = False
        mock_game.players[1].eliminated = True
        mock_game.current_player_idx = 0
        mock_game.next_player()
        assert mock_game.current_player_idx == 2

    def test_next_player_direction_reverse(self, mock_game):
        for p in mock_game.players:
            p.eliminated = False
        mock_game.direction = -1
        mock_game.current_player_idx = 0
        mock_game.next_player()
        assert mock_game.current_player_idx == 3

    def test_peek_next_player_does_not_advance(self, mock_game):
        for p in mock_game.players:
            p.eliminated = False
        mock_game.current_player_idx = 0
        nxt = mock_game.peek_next_player()
        assert nxt is mock_game.players[1]
        assert mock_game.current_player_idx == 0

    def test_peek_next_player_all_eliminated(self, mock_game):
        for p in mock_game.players:
            p.eliminated = True
        assert mock_game.peek_next_player() is None

    def test_current_player(self, mock_game):
        mock_game.current_player_idx = 2
        assert mock_game.current_player() is mock_game.players[2]

    def test_check_winner_hand_empty(self, mock_game):
        """先给每个玩家一张手牌，再清空 players[2]，确保胜者是 players[2]。"""
        for p in mock_game.players:
            p.eliminated = False
            p.hand = [Card('红', '数字', 1)]
        mock_game.players[2].hand = []
        assert mock_game.check_winner() is mock_game.players[2]

    def test_check_winner_only_one_active(self, mock_game):
        for p in mock_game.players:
            p.eliminated = True
        mock_game.players[3].eliminated = False
        assert mock_game.check_winner() is mock_game.players[3]

    def test_check_winner_none(self, mock_game):
        for p in mock_game.players:
            p.eliminated = False
            p.hand = [Card('红', '数字', 1)]
        assert mock_game.check_winner() is None

    def test_broadcast_reaches_all_ui(self, mock_game):
        ui1 = MagicMock()
        ui2 = MagicMock()
        mock_game.players[0].ui = ui1
        mock_game.players[1].ui = ui2
        mock_game.players[2].ui = NullUI()
        mock_game.players[3].ui = NullUI()
        mock_game.broadcast("测试消息")
        ui1.show.assert_called_once_with("测试消息")
        ui2.show.assert_called_once_with("测试消息")

    def test_broadcast_skips_null_ui(self, mock_game):
        for p in mock_game.players:
            p.ui = NullUI()
        mock_game.broadcast("测试消息")

    def test_broadcast_dedupes_shared_ui(self, mock_game):
        shared = MagicMock()
        for p in mock_game.players:
            p.ui = shared
        mock_game.broadcast("消息")
        assert shared.show.call_count == 1

    def test_record_event(self, mock_game):
        mock_game.record_event('test_event', foo='bar')
        assert mock_game.event_log[-1]['type'] == 'test_event'
        assert mock_game.event_log[-1]['foo'] == 'bar'

    def test_apply_card_effect_skip(self, mock_game):
        player = mock_game.players[0]
        assert mock_game.apply_card_effect(player, Card('红', '跳过')) is True

    def test_apply_card_effect_reverse(self, mock_game):
        player = mock_game.players[0]
        old_dir = mock_game.direction
        result = mock_game.apply_card_effect(player, Card('红', '反转'))
        assert result is False
        assert mock_game.direction == -old_dir

    def test_apply_card_effect_draw_two(self, mock_game):
        player = mock_game.players[0]
        with patch.object(mock_game, 'apply_add_cards') as mock_add:
            result = mock_game.apply_card_effect(player, Card('红', '+2'))
        assert result is True
        mock_add.assert_called_once()
        assert mock_add.call_args[0][0] is mock_game.players[1]
        assert mock_add.call_args[0][1] == 2

    def test_apply_card_effect_draw_four(self, mock_game):
        player = mock_game.players[0]
        with patch.object(mock_game, 'apply_add_cards') as mock_add, \
             patch.object(player, 'choose_color', return_value='红'):
            result = mock_game.apply_card_effect(player, Card('黑', '万能+4'))
        assert result is True
        assert mock_add.call_args[0][1] == 4
        assert mock_game.current_color == '红'

    def test_apply_card_effect_wild_color(self, mock_game):
        player = mock_game.players[0]
        with patch.object(player, 'choose_color', return_value='蓝'):
            result = mock_game.apply_card_effect(player, Card('黑', '万能'))
        assert result is False
        assert mock_game.current_color == '蓝'

    def test_uno_reminder_one_card(self, mock_game):
        player = mock_game.players[1]
        player.hand = [Card('红', '数字', 1)]
        mock_game.uno_reminder(player)

    def test_uno_reminder_not_triggered(self, mock_game):
        player = mock_game.players[1]
        player.hand = [Card('红', '数字', 1), Card('红', '数字', 2)]
        mock_game.uno_reminder(player)

    def test_skill_urgency_static(self):
        assert Skill('测试', SkillType.ACTIVE, 'desc',
                     urgency_weight=77).urgency_weight == 77

    def test_skill_urgency_default(self):
        assert Skill('测试', SkillType.ACTIVE, 'desc').urgency_weight == 50

    def test_skill_urgency_custom(self, mock_game):
        class CustomSkill(Skill):
            def evaluate_urgency(self, game):
                return 42

        assert CustomSkill('x', SkillType.ACTIVE, 'd').evaluate_urgency(mock_game) == 42


# ==================== 游戏流程 ====================
class TestGameFlow:
    def test_full_ai_game(self):
        """验证 AI 对局能推进（限制回合数，避免无限跑）。"""
        game = UNOGame(debug=False, use_rich_ui=False)
        game.ui = MagicMock()
        for p in game.players:
            p.is_human = False
            p.ui = MagicMock()
        game.setup()

        with patch('builtins.input', return_value=''):
            for _ in range(50):
                game.play_turn()
                if game.check_winner():
                    break
        assert True

    def test_add_cards_with_multiplier(self, mock_game):
        player = mock_game.players[0]
        player.hand_limit = 100
        before = len(player.hand)
        mock_game.apply_add_cards(player, 2)
        assert len(player.hand) == before + 2

    def test_dev_skills(self):
        from uno.season1 import PoWanFa, ZhaoZai
        dev = {'你': [PoWanFa, ZhaoZai]}
        game = UNOGame(debug=False, use_rich_ui=False, dev_skills=dev)
        game.ui = MagicMock()
        for p in game.players:
            p.ui = MagicMock()
            p.is_human = False
        game.setup()
        assert [s.name for s in game.players[0].skills] == ['破万法', '招灾']

    def test_custom_room_rules(self):
        game = UNOGame(
            debug=False, use_rich_ui=False,
            hand_limit=10, initial_hand_size=5, initial_skill_count=1
        )
        game.ui = MagicMock()
        for p in game.players:
            p.ui = MagicMock()
            p.is_human = False
        game.setup()
        for p in game.players:
            assert p.hand_limit == 10
            assert len(p.hand) == 5
            assert len(p.skills) == 1

    def test_hotseat_mode_creation(self):
        game = UNOGame(debug=False, use_rich_ui=False, players=['Alice', 'Bob'])
        assert game.hotseat is True
        assert len(game.players) == 2
        assert all(p.is_human for p in game.players)

    def test_ui_decoupling(self):
        human_ui = ConsoleUI()
        ai_ui = NullUI()
        game = UNOGame("你", ['S1'], use_rich_ui=False,
                       human_ui=human_ui, ai_ui=ai_ui)
        assert game.players[0].ui is human_ui
        for p in game.players[1:]:
            assert p.ui is ai_ui

    def test_end_single_game_records_winner(self, mock_game):
        mock_game.setup()
        human = mock_game.players[0]
        ai = mock_game.players[1]
        with patch('uno.archive.update_record'), \
             patch('uno.archive.show_record'):
            mock_game._end_single_game(human, ai)
        assert any(e['type'] == 'game_end' and e.get('winner') == ai.name
                   for e in mock_game.event_log)

    def test_end_hotseat_game_records_all_humans(self):
        """热座模式下，每位人类玩家的胜负都应被正确记录。"""
        game = UNOGame(debug=False, use_rich_ui=False, players=['A', 'B'])
        game.ui = MagicMock()
        for p in game.players:
            p.ui = MagicMock()
        game.setup()

        assert all(p.is_human for p in game.players)
        assert len(game.players) == 2

        winner = game.players[0]  # A 获胜

        with patch('uno.archive.update_record') as mock_update, \
             patch('uno.archive.show_record'):
            game._end_hotseat_game(winner)

        assert mock_update.call_count == 2
        calls = {call.args[0]: call.args[1] for call in mock_update.call_args_list}
        assert calls['A'] is True
        assert calls['B'] is False


# ==================== Presets ====================
class TestPresets:
    def test_load_empty(self, clean_presets_file):
        assert presets_module.load_presets() == []

    def test_load_when_file_empty(self, clean_presets_file):
        clean_presets_file.write_text('', encoding='utf-8')
        assert presets_module.load_presets() == []

    def test_load_invalid_data(self, clean_presets_file):
        clean_presets_file.write_text('not-valid-base64!!!', encoding='ascii')
        assert presets_module.load_presets() == []

    def test_save_and_load(self, clean_presets_file):
        data = [{'name': 'P1', 'hand_limit': 10,
                 'initial_hand_size': 5, 'initial_skill_count': 2}]
        presets_module.save_presets(data)
        assert presets_module.load_presets() == data

    def test_add_new(self, clean_presets_file):
        presets_module.add_preset("测试预设", 10, 5, 2)
        presets = presets_module.load_presets()
        assert len(presets) == 1
        assert presets[0]['name'] == "测试预设"
        assert presets[0]['hand_limit'] == 10
        assert presets[0]['initial_hand_size'] == 5
        assert presets[0]['initial_skill_count'] == 2

    def test_add_updates_existing(self, clean_presets_file):
        presets_module.add_preset("测试预设", 10, 5, 2)
        presets_module.add_preset("测试预设", 20, 8, 3)
        presets = presets_module.load_presets()
        assert len(presets) == 1
        assert presets[0]['hand_limit'] == 20
        assert presets[0]['initial_hand_size'] == 8
        assert presets[0]['initial_skill_count'] == 3

    def test_add_multiple(self, clean_presets_file):
        presets_module.add_preset("预设A", 10, 5, 2)
        presets_module.add_preset("预设B", 15, 7, 3)
        presets = presets_module.load_presets()
        assert len(presets) == 2
        assert {p['name'] for p in presets} == {"预设A", "预设B"}

    def test_get_existing(self, clean_presets_file):
        presets_module.add_preset("测试预设", 10, 5, 2)
        p = presets_module.get_preset("测试预设")
        assert p is not None
        assert p['hand_limit'] == 10

    def test_get_missing_returns_none(self, clean_presets_file):
        assert presets_module.get_preset("不存在") is None

    def test_file_is_base64_json(self, clean_presets_file):
        presets_module.add_preset("测试预设", 10, 5, 2)
        content = clean_presets_file.read_text(encoding='ascii')
        decoded = base64.b64decode(content).decode('utf-8')
        data = json.loads(decoded)
        assert isinstance(data, list)
        assert data[0]['name'] == "测试预设"

    def test_add_returns_true(self, clean_presets_file):
        assert presets_module.add_preset("P", 10, 5, 2) is True


# ==================== Loader ====================
class TestLoader:
    @pytest.fixture(autouse=True)
    def ensure_mods_package(self):
        """
        确保 mods/ 目录存在且已被初始化为 Python 包。
        - 不创建 __init__.py，避免污染真实目录
        - 缺失时直接 fail，提示项目结构有问题
        """
        mods_dir = os.path.join(PROJECT_ROOT, 'mods')
        init_file = os.path.join(mods_dir, '__init__.py')

        if not os.path.isdir(mods_dir):
            pytest.skip("mods 目录不存在，跳过加载器测试")
        if not os.path.exists(init_file):
            pytest.fail(
                f"mods/__init__.py 缺失于 {mods_dir}。"
                "它是 Python 包的一部分，应提交到版本库。"
            )

        self.mods_dir = mods_dir
        self.temp_files = []
        yield
        for f in self.temp_files:
            if os.path.exists(f):
                os.remove(f)

    def _create_mod(self, filename, content):
        path = os.path.join(self.mods_dir, filename)
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        self.temp_files.append(path)

    def test_dependency_missing(self, mock_game):
        self._create_mod('test_mod_dep.py', """
SEASON_ID = "MOD_DEP"
SEASON_NAME = "依赖测试"
RELY_ON = ("S2", "需要 S2 的技能")
SKILL_CLASSES = []
""")
        skills, glossary, ach = SkillLoader.load_skills(['MOD_DEP'], mock_game)
        assert skills == []

    def test_reject_conflict(self, mock_game):
        self._create_mod('test_mod_reject.py', """
SEASON_ID = "MOD_REJ"
SEASON_NAME = "排斥测试"
REJECT = {"S1": "冲突"}
SKILL_CLASSES = []
""")
        skills, glossary, ach = SkillLoader.load_skills(['S1', 'MOD_REJ'], mock_game)
        assert skills == []

    def test_tolerate(self, mock_game):
        self._create_mod('test_mod_tolerate.py', """
SEASON_ID = "MOD_TOL"
SEASON_NAME = "容忍测试"
ONLY_TOLERATE = ("S1",)
SKILL_CLASSES = []
""")
        skills, glossary, ach = SkillLoader.load_skills(
            ['S1', 'S2', 'MOD_TOL'], mock_game
        )
        assert not any(s.name == '始皇帝' for s in skills)

    def test_load_official_s1(self, mock_game):
        skills, glossary, ach = SkillLoader.load_skills(['S1'], mock_game)
        assert len(skills) == 15
        assert isinstance(glossary, dict)
        assert isinstance(ach, list)

    def test_load_unknown_season(self, mock_game):
        skills, glossary, ach = SkillLoader.load_skills(['NOT_EXIST'], mock_game)
        assert skills == []


# ==================== Season 2 技能 ====================
class TestSeason2ShiHuangDi:
    def test_can_trigger_game_start(self, mock_game, owner):
        s = season2.ShiHuangDi(owner, mock_game)
        assert s.can_trigger(GameEvent.GAME_START, {})

    def test_can_trigger_turn_start_for_owner(self, mock_game, owner):
        s = season2.ShiHuangDi(owner, mock_game)
        assert s.can_trigger(GameEvent.TURN_START, {'player': owner})

    def test_cannot_trigger_turn_start_for_other(self, mock_game, owner, other_player):
        s = season2.ShiHuangDi(owner, mock_game)
        assert not s.can_trigger(GameEvent.TURN_START, {'player': other_player})

    def test_urgency_high_when_opponent_has_many(self, mock_game, owner):
        s = season2.ShiHuangDi(owner, mock_game)
        other_player = mock_game.players[1]
        other_player.hand = [Card('红', '数字', i) for i in range(10)]
        assert s.evaluate_urgency(mock_game) == 90

    def test_urgency_low_when_opponent_has_few(self, mock_game, owner):
        s = season2.ShiHuangDi(owner, mock_game)
        for p in mock_game.players[1:]:
            p.hand = [Card('红', '数字', 1)]
        assert s.evaluate_urgency(mock_game) == 70

    def test_consumed_returns_false(self, mock_game, owner):
        s = season2.ShiHuangDi(owner, mock_game)
        s.is_consumed = True
        assert not s.can_trigger(GameEvent.GAME_START, {})


class TestSeason2SuQin:
    def test_can_trigger_game_start(self, mock_game, owner):
        s = season2.SuQin(owner, mock_game)
        assert s.can_trigger(GameEvent.GAME_START, {})

    def test_can_trigger_being_added(self, mock_game, owner):
        s = season2.SuQin(owner, mock_game)
        ctx = {'target': owner, 'amount': 3}
        assert s.can_trigger(GameEvent.BEING_ADDED_CARDS, ctx)

    def test_cannot_trigger_being_added_for_other(self, mock_game, owner, other_player):
        s = season2.SuQin(owner, mock_game)
        ctx = {'target': other_player, 'amount': 3}
        assert not s.can_trigger(GameEvent.BEING_ADDED_CARDS, ctx)

    def test_urgency_high_with_many_cards(self, mock_game, owner):
        s = season2.SuQin(owner, mock_game)
        owner.hand = [Card('红', '数字', i) for i in range(10)]
        assert s.evaluate_urgency(mock_game) == 70

    def test_urgency_low_with_few_cards(self, mock_game, owner):
        s = season2.SuQin(owner, mock_game)
        owner.hand = [Card('红', '数字', 1)]
        assert s.evaluate_urgency(mock_game) == 30

    def test_combo_partners_set(self, mock_game, owner):
        s = season2.SuQin(owner, mock_game)
        assert s.combo_partners == ('苏秦', '张仪')
        assert s.combo_effect is season2.SuQinZhangYiCombo

    def test_activate_being_added(self, mock_game, owner):
        s = season2.SuQin(owner, mock_game)
        owner.hand = [Card('红', '数字', i) for i in range(5)]
        ctx = {'target': owner, 'amount': 3, 'cancel': False}
        assert s.activate(GameEvent.BEING_ADDED_CARDS, ctx) is True
        assert ctx['cancel'] is True
        assert s.is_consumed is True
        assert len(owner.hand) == 2


class TestSeason2ZhangYi:
    def test_can_trigger_game_start(self, mock_game, owner):
        s = season2.ZhangYi(owner, mock_game)
        assert s.can_trigger(GameEvent.GAME_START, {})

    def test_can_trigger_turn_start(self, mock_game, owner):
        s = season2.ZhangYi(owner, mock_game)
        assert s.can_trigger(GameEvent.TURN_START, {'player': owner})

    def test_urgency_zero_without_target(self, mock_game, owner):
        s = season2.ZhangYi(owner, mock_game)
        owner.hand = [Card('红', '数字', 9), Card('绿', '跳过')]
        assert s.evaluate_urgency(mock_game) == 0

    def test_urgency_high_when_next_has_few(self, mock_game, owner):
        s = season2.ZhangYi(owner, mock_game)
        owner.hand = [Card('红', '数字', 3)]
        mock_game.players[1].hand = [Card('红', '数字', 1)]
        assert s.evaluate_urgency(mock_game) == 90

    def test_urgency_medium_default(self, mock_game, owner):
        s = season2.ZhangYi(owner, mock_game)
        owner.hand = [Card('红', '数字', 3)]
        for p in mock_game.players[1:]:
            p.hand = [Card('红', '数字', i) for i in range(7)]
        assert s.evaluate_urgency(mock_game) == 50

    def test_combo_partners_set(self, mock_game, owner):
        s = season2.ZhangYi(owner, mock_game)
        assert s.combo_partners == ('苏秦', '张仪')


class TestSeason2ShuangShengHua:
    def test_initial_ally_none(self, mock_game, owner):
        s = season2.ShuangShengHua(owner, mock_game)
        assert s.ally is None

    def test_can_trigger_start_random_for_owner(self, mock_game, owner):
        s = season2.ShuangShengHua(owner, mock_game)
        assert s.can_trigger(GameEvent.START_RANDOM, {'player': owner})

    def test_can_trigger_turn_start_when_unallied(self, mock_game, owner):
        s = season2.ShuangShengHua(owner, mock_game)
        assert s.can_trigger(GameEvent.TURN_START, {'player': owner})

    def test_cannot_trigger_turn_start_when_allied(self, mock_game, owner):
        s = season2.ShuangShengHua(owner, mock_game)
        s.ally = mock_game.players[1]
        assert not s.can_trigger(GameEvent.TURN_START, {'player': owner})

    def test_can_trigger_cards_added_when_ally_targeted(self, mock_game, owner):
        s = season2.ShuangShengHua(owner, mock_game)
        ally = mock_game.players[1]
        s.ally = ally
        ctx = {'target': ally, 'amount': 3}
        assert s.can_trigger(GameEvent.CARDS_ADDED, ctx)

    def test_urgency_when_unallied(self, mock_game, owner):
        s = season2.ShuangShengHua(owner, mock_game)
        assert s.evaluate_urgency(mock_game) == 70

    def test_urgency_when_allied(self, mock_game, owner):
        s = season2.ShuangShengHua(owner, mock_game)
        s.ally = mock_game.players[1]
        assert s.evaluate_urgency(mock_game) == 0

    def test_ally_sync_on_cards_added(self, mock_game, owner):
        s = season2.ShuangShengHua(owner, mock_game)
        ally = mock_game.players[1]
        s.ally = ally
        ctx = {'target': ally, 'amount': 2}
        with patch.object(mock_game, 'apply_add_cards') as mock_add:
            s.activate(GameEvent.CARDS_ADDED, ctx)
        mock_add.assert_called_once_with(owner, 2)


class TestSeason2JinShen:
    def test_can_trigger_big_add(self, mock_game, owner):
        s = season2.JinShen(owner, mock_game)
        ctx = {'target': owner, 'amount': 10}
        assert s.can_trigger(GameEvent.BEING_ADDED_CARDS, ctx)

    def test_cannot_trigger_small_add(self, mock_game, owner):
        s = season2.JinShen(owner, mock_game)
        ctx = {'target': owner, 'amount': 3}
        assert not s.can_trigger(GameEvent.BEING_ADDED_CARDS, ctx)

    def test_can_trigger_powanfa(self, mock_game, owner):
        s = season2.JinShen(owner, mock_game)
        po_wan_fa = season1.PoWanFa(owner, mock_game)
        ctx = {'activated_skill': po_wan_fa}
        assert s.can_trigger(GameEvent.SKILL_ACTIVATED, ctx)

    def test_activate_big_add(self, mock_game, owner):
        s = season2.JinShen(owner, mock_game)
        ctx = {'target': owner, 'amount': 10, 'cancel': False}
        assert s.activate(GameEvent.BEING_ADDED_CARDS, ctx) is True
        assert ctx['cancel'] is True


class TestSeason2YingYan:
    def test_can_trigger_game_start(self, mock_game, owner):
        s = season2.YingYan(owner, mock_game)
        assert s.can_trigger(GameEvent.GAME_START, {})

    def test_can_trigger_turn_start(self, mock_game, owner):
        s = season2.YingYan(owner, mock_game)
        assert s.can_trigger(GameEvent.TURN_START, {'player': owner})

    def test_urgency_low(self, mock_game, owner):
        s = season2.YingYan(owner, mock_game)
        assert s.evaluate_urgency(mock_game) == 30


class TestSeason2GuYongZhe:
    def test_after_draw_increments(self, mock_game, owner):
        s = season2.GuYongZhe(owner, mock_game)
        s.can_trigger(GameEvent.AFTER_DRAW, {'player': owner})
        s.can_trigger(GameEvent.AFTER_DRAW, {'player': owner})
        assert s.draw_count == 2

    def test_urgency_at_7_draws(self, mock_game, owner):
        s = season2.GuYongZhe(owner, mock_game)
        s.draw_count = 7
        assert s.evaluate_urgency(mock_game) == 90

    def test_urgency_below_7_draws(self, mock_game, owner):
        s = season2.GuYongZhe(owner, mock_game)
        s.draw_count = 5
        assert s.evaluate_urgency(mock_game) == 0

    def test_activate_sends_7_to_all_others(self, mock_game, owner):
        s = season2.GuYongZhe(owner, mock_game)
        s.draw_count = 7
        with patch.object(mock_game, 'apply_add_cards') as mock_add:
            s.activate(GameEvent.TURN_START, {'player': owner})
        assert mock_add.call_count == len(mock_game.players) - 1


class TestSeason2WangYou:
    def test_can_trigger_player_died(self, mock_game, owner):
        s = season2.WangYou(owner, mock_game)
        assert s.can_trigger(GameEvent.PLAYER_DIED, {'player': owner})

    def test_cannot_trigger_other_player(self, mock_game, owner, other_player):
        s = season2.WangYou(owner, mock_game)
        assert not s.can_trigger(GameEvent.PLAYER_DIED, {'player': other_player})

    def test_activate_no_available_skills(self, mock_game, owner):
        s = season2.WangYou(owner, mock_game)
        for p in mock_game.players:
            for skill in p.skills:
                skill.is_consumed = False
        result = s.activate(GameEvent.PLAYER_DIED, {'player': owner})
        assert result is True
        assert s.is_consumed is True


class TestSeason2Combo:
    def test_combo_consumes_both(self, mock_game, owner):
        suqin = season2.SuQin(owner, mock_game)
        zhangyi = season2.ZhangYi(owner, mock_game)
        owner.skills = [suqin, zhangyi]
        combo = season2.SuQinZhangYiCombo()
        with patch('random.randint', return_value=6):
            combo.execute(owner, mock_game.skill_manager, mock_game)
        assert suqin.is_consumed
        assert zhangyi.is_consumed

    def test_combo_low_roll_sends_cards(self, mock_game, owner):
        suqin = season2.SuQin(owner, mock_game)
        zhangyi = season2.ZhangYi(owner, mock_game)
        owner.skills = [suqin, zhangyi]
        combo = season2.SuQinZhangYiCombo()
        with patch('random.randint', return_value=1), \
             patch.object(mock_game, 'apply_add_cards') as mock_add:
            combo.execute(owner, mock_game.skill_manager, mock_game)
        assert mock_add.call_count == len(mock_game.players)


# ==================== Season 3（占位） ====================
class TestSeason3:
    def test_metadata_exists(self):
        assert hasattr(season3, 'SEASON_ID')
        assert hasattr(season3, 'SEASON_NAME')
        assert hasattr(season3, 'SKILL_CLASSES')
        assert isinstance(season3.SKILL_CLASSES, list)

    def test_loader_does_not_crash(self, mock_game):
        result = SkillLoader.load_skills(['S3'], mock_game)
        assert isinstance(result, tuple)
        assert len(result) == 3


# ==================== Season 4 技能 ====================
class TestSeason4YanPin:
    def test_can_trigger(self, mock_game, owner):
        s = season4.YanPin(owner, mock_game)
        assert s.can_trigger(GameEvent.TURN_START, {'player': owner})

    def test_activate_no_hand(self, mock_game, owner):
        s = season4.YanPin(owner, mock_game)
        owner.hand = []
        assert s.activate(GameEvent.TURN_START, {'player': owner}) is False

    def test_activate_ai_branch(self, mock_game, owner):
        s = season4.YanPin(owner, mock_game)
        owner.is_human = False
        owner.hand = [Card('红', '数字', 3)]
        result = s.activate(GameEvent.TURN_START, {'player': owner})
        assert result is True
        assert s.is_consumed is True


class TestSeason4TanNang:
    def test_can_trigger(self, mock_game, owner):
        s = season4.TanNang(owner, mock_game)
        assert s.can_trigger(GameEvent.TURN_START, {'player': owner})

    def test_urgency_with_low_hand(self, mock_game, owner):
        s = season4.TanNang(owner, mock_game)
        mock_game.players[1].hand = [Card('红', '数字', 1)]
        assert s.evaluate_urgency(mock_game) == 75

    def test_urgency_default(self, mock_game, owner):
        s = season4.TanNang(owner, mock_game)
        for p in mock_game.players[1:]:
            p.hand = [Card('红', '数字', i) for i in range(7)]
        assert s.evaluate_urgency(mock_game) == 55

    def test_activate_ai_branch(self, mock_game, owner):
        s = season4.TanNang(owner, mock_game)
        owner.is_human = False
        target = mock_game.players[1]
        target.hand = [Card('红', '数字', 1)]
        with patch.object(s, '_choose_target', return_value=target):
            result = s.activate(GameEvent.TURN_START, {'player': owner})
        assert result is True
        assert len(target.hand) == 0


class TestSeason4XianLing:
    def test_can_trigger(self, mock_game, owner):
        s = season4.XianLing(owner, mock_game)
        assert s.can_trigger(GameEvent.TURN_START, {'player': owner})

    def test_activate_ai_branch(self, mock_game, owner):
        s = season4.XianLing(owner, mock_game)
        owner.is_human = False
        result = s.activate(GameEvent.TURN_START, {'player': owner})
        assert result is True
        assert s.is_consumed is True


class TestSeason4JiaHuo:
    def test_can_trigger_when_targeted(self, mock_game, owner):
        s = season4.JiaHuo(owner, mock_game)
        ctx = {'original_context': {'target': owner}}
        assert s.can_trigger(GameEvent.SKILL_ACTIVATED, ctx)

    def test_cannot_trigger_when_not_targeted(self, mock_game, owner, other_player):
        s = season4.JiaHuo(owner, mock_game)
        ctx = {'original_context': {'target': other_player}}
        assert not s.can_trigger(GameEvent.SKILL_ACTIVATED, ctx)

    def test_activate_redirects(self, mock_game, owner):
        s = season4.JiaHuo(owner, mock_game)
        other_player = mock_game.players[1]
        orig = {'target': owner}
        ctx = {'original_context': orig}
        with patch.object(s, '_choose_target', return_value=other_player):
            result = s.activate(GameEvent.SKILL_ACTIVATED, ctx)
        assert result is True
        assert orig['target'] is other_player
        assert s.is_consumed is True


class TestSeason4JiFa:
    def test_can_trigger(self, mock_game, owner):
        s = season4.JiFa(owner, mock_game)
        assert s.can_trigger(GameEvent.TURN_START, {'player': owner})

    def test_urgency_low(self, mock_game, owner):
        s = season4.JiFa(owner, mock_game)
        assert s.evaluate_urgency(mock_game) == 30


class TestSeason4YeLi:
    def test_can_trigger(self, mock_game, owner):
        s = season4.YeLi(owner, mock_game)
        assert s.can_trigger(GameEvent.TURN_START, {'player': owner})

    def test_activate_ai_branch(self, mock_game, owner):
        s = season4.YeLi(owner, mock_game)
        owner.is_human = False
        target = mock_game.players[1]
        target.hand = [Card('红', '数字', i) for i in range(5)]
        with patch.object(s, '_choose_target', return_value=target), \
             patch.object(mock_game, 'apply_add_cards') as mock_add, \
             patch('random.choice', return_value='红'):
            result = s.activate(GameEvent.TURN_START, {'player': owner})
        assert result is True
        assert mock_add.called


class TestSeason4DuoXinPo:
    def test_can_trigger(self, mock_game, owner):
        s = season4.DuoXinPo(owner, mock_game)
        ctx = {'target': owner, 'amount': 5}
        assert s.can_trigger(GameEvent.BEING_ADDED_CARDS, ctx)

    def test_cannot_trigger_for_other(self, mock_game, owner, other_player):
        s = season4.DuoXinPo(owner, mock_game)
        ctx = {'target': other_player, 'amount': 5}
        assert not s.can_trigger(GameEvent.BEING_ADDED_CARDS, ctx)

    def test_activate_ai_picks_victims(self, mock_game, owner):
        s = season4.DuoXinPo(owner, mock_game)
        owner.is_human = False
        ctx = {'target': owner, 'amount': 3, 'cancel': False}
        with patch.object(mock_game, 'apply_add_cards') as mock_add, \
             patch('random.sample', side_effect=lambda seq, k: list(seq)[:k]):
            result = s.activate(GameEvent.BEING_ADDED_CARDS, ctx)
        assert result is True
        assert mock_add.call_count >= 1


class TestSeason4HunQian:
    def test_can_trigger(self, mock_game, owner):
        s = season4.HunQian(owner, mock_game)
        ctx = {'target': owner, 'amount': 5}
        assert s.can_trigger(GameEvent.BEING_ADDED_CARDS, ctx)

    def test_cannot_trigger_for_other(self, mock_game, owner, other_player):
        s = season4.HunQian(owner, mock_game)
        ctx = {'target': other_player, 'amount': 5}
        assert not s.can_trigger(GameEvent.BEING_ADDED_CARDS, ctx)

    def test_activate_consumes_immediately(self, mock_game, owner):
        s = season4.HunQian(owner, mock_game)
        ctx = {'target': owner, 'amount': 3, 'cancel': False}
        with patch.object(mock_game, 'apply_add_cards'):
            result = s.activate(GameEvent.BEING_ADDED_CARDS, ctx)
        assert result is True
        assert s.is_consumed is True
        assert ctx['cancel'] is True


# ==================== 成就 ====================
@pytest.fixture
def mock_ach_game():
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


class TestAchievements:
    def test_no_draw_victory(self, mock_ach_game):
        events = [{'type': 'game_end', 'winner': '你'}]
        assert NoDrawVictoryAchievement().check(mock_ach_game, events) is True

    def test_no_draw_victory_fail(self, mock_ach_game):
        events = [
            {'type': 'draw_card', 'player': '你'},
            {'type': 'game_end', 'winner': '你'}
        ]
        assert NoDrawVictoryAchievement().check(mock_ach_game, events) is False

    def test_comeback_1v3(self, mock_ach_game):
        events = [
            {'type': 'player_eliminated', 'player': '电脑A', 'turn_number': 5},
            {'type': 'player_eliminated', 'player': '电脑B', 'turn_number': 10},
            {'type': 'player_eliminated', 'player': '电脑C', 'turn_number': 15},
            {'type': 'game_end', 'winner': '你'}
        ]
        assert Comeback1v3Achievement().check(mock_ach_game, events) is True

    def test_comeback_1v3_fail_human_eliminated(self, mock_ach_game):
        events = [
            {'type': 'player_eliminated', 'player': '你', 'turn_number': 1},
            {'type': 'game_end', 'winner': '电脑A'}
        ]
        assert Comeback1v3Achievement().check(mock_ach_game, events) is False

    def test_comeback_1v3_fail_not_all_eliminated(self, mock_ach_game):
        events = [
            {'type': 'player_eliminated', 'player': '电脑A', 'turn_number': 5},
            {'type': 'game_end', 'winner': '你'}
        ]
        assert Comeback1v3Achievement().check(mock_ach_game, events) is False

    def test_counter_master(self, mock_ach_game):
        events = [
            {'type': 'skill_use', 'skill_name': '破万法'},
            {'type': 'skill_use', 'skill_name': '储能'},
            {'type': 'skill_use', 'skill_name': '破万法'},
        ]
        assert CounterMasterAchievement().check(mock_ach_game, events) is True

    def test_counter_master_fail(self, mock_ach_game):
        events = [
            {'type': 'skill_use', 'skill_name': '破万法'},
            {'type': 'skill_use', 'skill_name': '储能'},
        ]
        assert CounterMasterAchievement().check(mock_ach_game, events) is False

    def test_instant_kill(self, mock_ach_game):
        events = [
            {'type': 'player_eliminated', 'player': '电脑A',
             'reason': 'hand_limit', 'turn_number': 1},
        ]
        assert InstantKillAchievement().check(mock_ach_game, events) is True

    def test_instant_kill_fail(self, mock_ach_game):
        events = [
            {'type': 'player_eliminated', 'player': '电脑A',
             'reason': 'hand_limit', 'turn_number': 3},
        ]
        assert InstantKillAchievement().check(mock_ach_game, events) is False

    def test_manager_registers_all(self, mock_ach_game):
        m = AchievementManager(mock_ach_game, get_core_achievements())
        assert len(m.achievements) >= 4

    def test_manager_evaluate(self, mock_ach_game):
        m = AchievementManager(mock_ach_game, get_core_achievements())
        achieved = m.evaluate([{'type': 'game_end', 'winner': '你'}])
        assert '被遗忘的战术' in achieved

    def test_manager_add(self, mock_ach_game):
        from uno.achievements import Achievement

        class Extra(Achievement):
            def __init__(self):
                super().__init__('extra', '额外成就', '测试')
            def check(self, game, events):
                return True

        m = AchievementManager(mock_ach_game, [])
        m.add_achievements([Extra])
        assert m.achievements[0].name == '额外成就'


# ==================== 回放 ====================
class TestReplay:
    def test_recorder_save_load(self):
        recorder = GameRecorder()
        recorder.players = ['你', '电脑A']
        recorder.seasons = ['S1']
        recorder.initial_top_card = '红5'
        recorder.record('turn_start', player='你', hand_size=7)
        recorder.record('play_card', player='你', card='红5')
        recorder.record('game_end', winner='你')
        path = recorder.save()
        assert os.path.exists(path)
        try:
            ui = MagicMock()
            replayer = GameReplayer(path, ui)
            assert replayer.data['players'] == ['你', '电脑A']
            events = []
            while True:
                ev = replayer.next_event()
                if ev is None:
                    break
                events.append(ev)
            assert len(events) == 3
        finally:
            os.remove(path)

    def test_replayer_missing_file(self):
        with pytest.raises((FileNotFoundError, ValueError)):
            GameReplayer('/nonexistent/path.json', MagicMock())

    def test_replayer_empty_file(self, tmp_path):
        empty = tmp_path / "empty.json"
        empty.write_text('', encoding='utf-8')
        with pytest.raises((FileNotFoundError, ValueError)):
            GameReplayer(str(empty), MagicMock())

# ==================== Archive ====================
class TestArchive:
    @pytest.fixture(autouse=True)
    def redirect_archive_file(self, tmp_path, monkeypatch):
        """把 ARCHIVE_FILE 指向临时文件，避免污染真实数据。"""
        import uno.archive as archive_module
        fake_file = tmp_path / "archive.txt"
        monkeypatch.setattr(archive_module, 'ARCHIVE_FILE', str(fake_file))
        self.archive_module = archive_module
        self.archive_file = fake_file

    def test_load_missing_file_returns_empty(self):
        assert self.archive_module.load_archive() == {}

    def test_load_empty_file_returns_empty(self):
        self.archive_file.write_text('', encoding='utf-8')
        assert self.archive_module.load_archive() == {}

    def test_load_invalid_base64_returns_empty(self):
        self.archive_file.write_text('!!!not-base64!!!', encoding='ascii')
        assert self.archive_module.load_archive() == {}

    def test_load_invalid_json_returns_empty(self):
        # 合法 Base64，但内容不是合法 JSON
        content = base64.b64encode(b'not-json').decode('ascii')
        self.archive_file.write_text(content, encoding='ascii')
        assert self.archive_module.load_archive() == {}

    def test_save_and_load_roundtrip(self):
        data = {"你": {"wins": 3, "losses": 1, "achievements": ["一穿三"]}}
        self.archive_module.save_archive(data)
        loaded = self.archive_module.load_archive()
        assert loaded == data

    def test_save_is_base64_json(self):
        data = {"你": {"wins": 1, "losses": 0, "achievements": []}}
        self.archive_module.save_archive(data)
        content = self.archive_file.read_text(encoding='ascii')
        decoded = base64.b64decode(content).decode('utf-8')
        parsed = json.loads(decoded)
        assert parsed == data

    def test_load_legacy_no_achievements_field(self):
        """兼容旧存档：缺少 achievements 字段时自动补空列表。"""
        legacy = {"老玩家": {"wins": 5, "losses": 3}}   # 没有 achievements
        encoded = base64.b64encode(
            json.dumps(legacy, ensure_ascii=False).encode('utf-8')
        ).decode('ascii')
        self.archive_file.write_text(encoded, encoding='ascii')
        loaded = self.archive_module.load_archive()
        assert loaded["老玩家"]["achievements"] == []

    def test_update_record_win(self):
        self.archive_module.update_record("A", True)
        data = self.archive_module.load_archive()
        assert data["A"]["wins"] == 1
        assert data["A"]["losses"] == 0

    def test_update_record_loss(self):
        self.archive_module.update_record("A", False)
        data = self.archive_module.load_archive()
        assert data["A"]["wins"] == 0
        assert data["A"]["losses"] == 1

    def test_update_record_increments(self):
        self.archive_module.update_record("A", True)
        self.archive_module.update_record("A", True)
        self.archive_module.update_record("A", False)
        data = self.archive_module.load_archive()
        assert data["A"]["wins"] == 2
        assert data["A"]["losses"] == 1

    def test_update_record_with_achievements(self):
        self.archive_module.update_record("A", True, ["一穿三", "反制大师"])
        data = self.archive_module.load_archive()
        assert set(data["A"]["achievements"]) == {"一穿三", "反制大师"}

    def test_update_record_merges_achievements(self):
        self.archive_module.update_record("A", True, ["一穿三"])
        self.archive_module.update_record("A", True, ["反制大师"])
        data = self.archive_module.load_archive()
        assert set(data["A"]["achievements"]) == {"一穿三", "反制大师"}

    def test_update_record_deduplicates_achievements(self):
        self.archive_module.update_record("A", True, ["一穿三"])
        self.archive_module.update_record("A", True, ["一穿三"])
        data = self.archive_module.load_archive()
        assert data["A"]["achievements"].count("一穿三") == 1

    def test_show_record_missing_player(self, capsys):
        self.archive_module.show_record("查无此人")
        out = capsys.readouterr().out
        assert "尚无战绩记录" in out

    def test_show_record_existing_player(self, capsys):
        self.archive_module.update_record("A", True)
        self.archive_module.update_record("A", False)
        capsys.readouterr()   # 清掉 update_record 的输出
        self.archive_module.show_record("A")
        out = capsys.readouterr().out
        assert "1胜" in out
        assert "1负" in out
        assert "50." in out

    def test_show_record_with_achievements(self, capsys):
        self.archive_module.update_record("A", True, ["一穿三"])
        capsys.readouterr()
        self.archive_module.show_record("A")
        out = capsys.readouterr().out
        assert "一穿三" in out

    def test_multiple_players(self):
        self.archive_module.update_record("A", True)
        self.archive_module.update_record("B", False)
        data = self.archive_module.load_archive()
        assert "A" in data
        assert "B" in data
        assert data["A"]["wins"] == 1
        assert data["B"]["losses"] == 1

# ==================== Season 2 技能 ====================
# ---------- ShiHuangDi ----------
class TestSeason2ShiHuangDi:
    def test_can_trigger_game_start(self, mock_game, owner):
        s = season2.ShiHuangDi(owner, mock_game)
        assert s.can_trigger(GameEvent.GAME_START, {})

    def test_can_trigger_turn_start_for_owner(self, mock_game, owner):
        s = season2.ShiHuangDi(owner, mock_game)
        assert s.can_trigger(GameEvent.TURN_START, {'player': owner})

    def test_cannot_trigger_turn_start_for_other(self, mock_game, owner, other_player):
        s = season2.ShiHuangDi(owner, mock_game)
        assert not s.can_trigger(GameEvent.TURN_START, {'player': other_player})

    def test_urgency_high_when_opponent_has_many(self, mock_game, owner):
        s = season2.ShiHuangDi(owner, mock_game)
        mock_game.players[1].hand = [Card('红', '数字', i) for i in range(10)]
        assert s.evaluate_urgency(mock_game) == 90

    def test_urgency_low_when_opponent_has_few(self, mock_game, owner):
        s = season2.ShiHuangDi(owner, mock_game)
        for p in mock_game.players[1:]:
            p.hand = [Card('红', '数字', 1)]
        assert s.evaluate_urgency(mock_game) == 70

    def test_consumed_returns_false(self, mock_game, owner):
        s = season2.ShiHuangDi(owner, mock_game)
        s.is_consumed = True
        assert not s.can_trigger(GameEvent.GAME_START, {})

    def test_activate_game_start_ai_picks_first_7(self, mock_game, owner):
        """AI 分支：随机选 7 张，不走 input。"""
        s = season2.ShiHuangDi(owner, mock_game)
        owner.is_human = False
        owner.hand = [Card('红', '数字', 1)]
        result = s.activate(GameEvent.GAME_START, {})
        assert result is False
        assert len(owner.hand) == 7
        assert s.passive_used is True

    def test_activate_game_start_human_uses_input(self, mock_game, human_player):
        """人类分支：mock input 每次选第 0 张。"""
        s = season2.ShiHuangDi(human_player, mock_game)
        human_player.is_human = True
        human_player.ui.input = MagicMock(return_value='0')
        result = s.activate(GameEvent.GAME_START, {})
        assert result is False
        assert len(human_player.hand) == 7

    def test_activate_turn_start_ai_chetonggui(self, mock_game, owner):
        """AI 分支：车同轨强制弃牌，保留数量最多的颜色。"""
        s = season2.ShiHuangDi(owner, mock_game)
        owner.is_human = False
        owner.hand = [Card('红', '数字', 1), Card('红', '数字', 2),
                      Card('红', '数字', 3)]
        mock_game.players[1].hand = [Card('红', '数字', 4)]
        mock_game.players[2].hand = [Card('蓝', '数字', 5)]
        mock_game.players[3].hand = [Card('蓝', '数字', 6)]
        result = s.activate(GameEvent.TURN_START, {'player': owner})
        assert result is True
        assert s.is_consumed is True
        # owner 和 players[1] 手里有红牌，应保留全部红牌
        for c in owner.hand:
            assert c.color == '红'
        for c in mock_game.players[1].hand:
            assert c.color == '红'
        # players[2]、players[3] 全是蓝牌，弃光后补回 1 张（颜色随机）
        assert len(mock_game.players[2].hand) == 1
        assert len(mock_game.players[3].hand) == 1

    def test_activate_turn_start_human_chooses_color(self, mock_game, human_player):
        s = season2.ShiHuangDi(human_player, mock_game)
        human_player.is_human = True
        human_player.ui.input = MagicMock(return_value='0')  # 选红
        for p in mock_game.players:
            p.hand = [Card('红', '数字', 1)]
        result = s.activate(GameEvent.TURN_START, {'player': human_player})
        assert result is True
        assert s.is_consumed is True

    def test_activate_turn_start_empty_hand_gets_one(self, mock_game, owner):
        """车同轨后手牌清零的玩家补一张。"""
        s = season2.ShiHuangDi(owner, mock_game)
        owner.is_human = False
        owner.hand = [Card('红', '数字', 1)]
        # 让其他玩家手里全是红色以外的牌
        mock_game.players[1].hand = [Card('蓝', '数字', 1)]
        result = s.activate(GameEvent.TURN_START, {'player': owner})
        assert result is True
        # players[1] 手牌被清空后应该补 1 张
        assert len(mock_game.players[1].hand) == 1

# ---------- SuQin ----------
class TestSeason2SuQin:
    def test_can_trigger_game_start(self, mock_game, owner):
        s = season2.SuQin(owner, mock_game)
        assert s.can_trigger(GameEvent.GAME_START, {})

    def test_can_trigger_being_added(self, mock_game, owner):
        s = season2.SuQin(owner, mock_game)
        assert s.can_trigger(GameEvent.BEING_ADDED_CARDS,
                             {'target': owner, 'amount': 3})

    def test_cannot_trigger_being_added_for_other(self, mock_game, owner, other_player):
        s = season2.SuQin(owner, mock_game)
        assert not s.can_trigger(GameEvent.BEING_ADDED_CARDS,
                                 {'target': other_player, 'amount': 3})

    def test_urgency_high_with_many_cards(self, mock_game, owner):
        s = season2.SuQin(owner, mock_game)
        owner.hand = [Card('红', '数字', i) for i in range(10)]
        assert s.evaluate_urgency(mock_game) == 70

    def test_urgency_low_with_few_cards(self, mock_game, owner):
        s = season2.SuQin(owner, mock_game)
        owner.hand = [Card('红', '数字', 1)]
        assert s.evaluate_urgency(mock_game) == 30

    def test_combo_partners_set(self, mock_game, owner):
        s = season2.SuQin(owner, mock_game)
        assert s.combo_partners == ('苏秦', '张仪')
        assert s.combo_effect is season2.SuQinZhangYiCombo

    def test_activate_game_start_redistributes_hands(self, mock_game, owner):
        s = season2.SuQin(owner, mock_game)
        owner.is_human = False
        for p in mock_game.players:
            p.hand = [Card('红', '数字', i) for i in range(7)]
        result = s.activate(GameEvent.GAME_START, {})
        assert result is False
        assert s.passive_used is True
        assert len(owner.hand) == 5
        for p in mock_game.players[1:]:
            assert len(p.hand) == 9

    def test_activate_being_added_removes_cards(self, mock_game, owner):
        s = season2.SuQin(owner, mock_game)
        owner.hand = [Card('红', '数字', i) for i in range(5)]
        ctx = {'target': owner, 'amount': 3, 'cancel': False}
        result = s.activate(GameEvent.BEING_ADDED_CARDS, ctx)
        assert result is True
        assert ctx['cancel'] is True
        assert s.is_consumed is True
        assert len(owner.hand) == 2

    def test_activate_being_added_more_than_hand(self, mock_game, owner):
        s = season2.SuQin(owner, mock_game)
        owner.hand = [Card('红', '数字', 1)]
        ctx = {'target': owner, 'amount': 10, 'cancel': False}
        result = s.activate(GameEvent.BEING_ADDED_CARDS, ctx)
        assert result is True
        assert len(owner.hand) == 0


# ---------- ZhangYi ----------
class TestSeason2ZhangYi:
    def test_can_trigger_game_start(self, mock_game, owner):
        s = season2.ZhangYi(owner, mock_game)
        assert s.can_trigger(GameEvent.GAME_START, {})

    def test_can_trigger_turn_start(self, mock_game, owner):
        s = season2.ZhangYi(owner, mock_game)
        assert s.can_trigger(GameEvent.TURN_START, {'player': owner})

    def test_urgency_zero_without_target(self, mock_game, owner):
        s = season2.ZhangYi(owner, mock_game)
        owner.hand = [Card('红', '数字', 9), Card('绿', '跳过')]
        assert s.evaluate_urgency(mock_game) == 0

    def test_urgency_high_when_next_has_few(self, mock_game, owner):
        s = season2.ZhangYi(owner, mock_game)
        owner.hand = [Card('红', '数字', 3)]
        mock_game.players[1].hand = [Card('红', '数字', 1)]
        assert s.evaluate_urgency(mock_game) == 90

    def test_urgency_medium_default(self, mock_game, owner):
        s = season2.ZhangYi(owner, mock_game)
        owner.hand = [Card('红', '数字', 3)]
        for p in mock_game.players[1:]:
            p.hand = [Card('红', '数字', i) for i in range(7)]
        assert s.evaluate_urgency(mock_game) == 50

    def test_combo_partners_set(self, mock_game, owner):
        s = season2.ZhangYi(owner, mock_game)
        assert s.combo_partners == ('苏秦', '张仪')

    def test_activate_game_start_redistributes(self, mock_game, owner):
        s = season2.ZhangYi(owner, mock_game)
        owner.is_human = False
        for p in mock_game.players:
            p.hand = [Card('红', '数字', i) for i in range(7)]
        result = s.activate(GameEvent.GAME_START, {})
        assert result is False
        assert s.passive_used is True
        assert len(owner.hand) == 5

    def test_activate_turn_start_ai_converts_card(self, mock_game, owner):
        s = season2.ZhangYi(owner, mock_game)
        owner.is_human = False
        owner.hand = [Card('红', '数字', 3), Card('蓝', '跳过')]
        with patch.object(mock_game, 'apply_add_cards') as mock_add:
            result = s.activate(GameEvent.TURN_START, {'player': owner})
        assert result is True
        assert s.is_consumed is True
        mock_add.assert_called_once()
        assert mock_add.call_args[0][0] is mock_game.players[1]

    def test_activate_turn_start_no_targets(self, mock_game, owner):
        s = season2.ZhangYi(owner, mock_game)
        owner.is_human = False
        owner.hand = [Card('红', '数字', 9), Card('蓝', '跳过')]
        result = s.activate(GameEvent.TURN_START, {'player': owner})
        assert result is False

    def test_activate_turn_start_human_picks_card(self, mock_game, human_player):
        s = season2.ZhangYi(human_player, mock_game)
        human_player.is_human = True
        human_player.hand = [Card('红', '数字', 3), Card('蓝', '跳过')]
        human_player.ui.input = MagicMock(return_value='0')
        with patch.object(mock_game, 'apply_add_cards') as mock_add:
            result = s.activate(GameEvent.TURN_START, {'player': human_player})
        assert result is True
        assert s.is_consumed is True
        mock_add.assert_called_once()


# ---------- ShuangShengHua ----------
class TestSeason2ShuangShengHua:
    def test_initial_ally_none(self, mock_game, owner):
        s = season2.ShuangShengHua(owner, mock_game)
        assert s.ally is None

    def test_can_trigger_start_random_for_owner(self, mock_game, owner):
        s = season2.ShuangShengHua(owner, mock_game)
        assert s.can_trigger(GameEvent.START_RANDOM, {'player': owner})

    def test_can_trigger_turn_start_when_unallied(self, mock_game, owner):
        s = season2.ShuangShengHua(owner, mock_game)
        assert s.can_trigger(GameEvent.TURN_START, {'player': owner})

    def test_cannot_trigger_turn_start_when_allied(self, mock_game, owner):
        s = season2.ShuangShengHua(owner, mock_game)
        s.ally = mock_game.players[1]
        assert not s.can_trigger(GameEvent.TURN_START, {'player': owner})

    def test_can_trigger_cards_added_when_ally_targeted(self, mock_game, owner):
        s = season2.ShuangShengHua(owner, mock_game)
        ally = mock_game.players[1]
        s.ally = ally
        assert s.can_trigger(GameEvent.CARDS_ADDED, {'target': ally, 'amount': 3})

    def test_urgency_when_unallied(self, mock_game, owner):
        s = season2.ShuangShengHua(owner, mock_game)
        assert s.evaluate_urgency(mock_game) == 70

    def test_urgency_when_allied(self, mock_game, owner):
        s = season2.ShuangShengHua(owner, mock_game)
        s.ally = mock_game.players[1]
        assert s.evaluate_urgency(mock_game) == 0

    def test_activate_start_random_ai_retry(self, mock_game, owner):
        s = season2.ShuangShengHua(owner, mock_game)
        owner.is_human = False
        ctx = {'player': owner, 'retry': False}
        with patch('random.random', return_value=0.1):
            s.activate(GameEvent.START_RANDOM, ctx)
        assert ctx['retry'] is True

    def test_activate_start_random_ai_no_retry(self, mock_game, owner):
        s = season2.ShuangShengHua(owner, mock_game)
        owner.is_human = False
        ctx = {'player': owner, 'retry': False}
        with patch('random.random', return_value=0.9):
            s.activate(GameEvent.START_RANDOM, ctx)
        assert ctx['retry'] is False

    def test_activate_turn_start_ai_chooses_ally(self, mock_game, owner):
        s = season2.ShuangShengHua(owner, mock_game)
        owner.is_human = False
        s.activate(GameEvent.TURN_START, {'player': owner})
        assert s.ally is not None
        assert s.ally is not owner

    def test_activate_turn_start_human_chooses_ally(self, mock_game, human_player):
        s = season2.ShuangShengHua(human_player, mock_game)
        human_player.is_human = True
        human_player.ui.input = MagicMock(return_value='0')
        s.activate(GameEvent.TURN_START, {'player': human_player})
        assert s.ally is not None

    def test_activate_turn_start_cannot_ally_guyongzhe(self, mock_game, owner):
        s = season2.ShuangShengHua(owner, mock_game)
        owner.is_human = False
        for p in mock_game.players[1:]:
            p.skills = [season2.GuYongZhe(p, mock_game)]
        s.activate(GameEvent.TURN_START, {'player': owner})
        assert s.ally is None

    def test_activate_cards_added_syncs(self, mock_game, owner):
        s = season2.ShuangShengHua(owner, mock_game)
        ally = mock_game.players[1]
        s.ally = ally
        ctx = {'target': ally, 'amount': 3}
        with patch.object(mock_game, 'apply_add_cards') as mock_add:
            s.activate(GameEvent.CARDS_ADDED, ctx)
        mock_add.assert_called_once_with(owner, 3)


# ---------- JinShen ----------
class TestSeason2JinShen:
    def test_can_trigger_big_add(self, mock_game, owner):
        s = season2.JinShen(owner, mock_game)
        assert s.can_trigger(GameEvent.BEING_ADDED_CARDS,
                             {'target': owner, 'amount': 10})

    def test_cannot_trigger_small_add(self, mock_game, owner):
        s = season2.JinShen(owner, mock_game)
        assert not s.can_trigger(GameEvent.BEING_ADDED_CARDS,
                                 {'target': owner, 'amount': 3})

    def test_can_trigger_powanfa(self, mock_game, owner):
        s = season2.JinShen(owner, mock_game)
        po = season1.PoWanFa(owner, mock_game)
        assert s.can_trigger(GameEvent.SKILL_ACTIVATED, {'activated_skill': po})

    def test_activate_being_added_cancels(self, mock_game, owner):
        s = season2.JinShen(owner, mock_game)
        ctx = {'target': owner, 'amount': 10, 'cancel': False}
        result = s.activate(GameEvent.BEING_ADDED_CARDS, ctx)
        assert result is True
        assert ctx['cancel'] is True
        assert s.is_consumed is False   # 金身不消耗

    def test_activate_blocks_powanfa(self, mock_game, owner):
        s = season2.JinShen(owner, mock_game)
        po = season1.PoWanFa(owner, mock_game)
        ctx = {'activated_skill': po, 'cancel': False}
        result = s.activate(GameEvent.SKILL_ACTIVATED, ctx)
        assert result is True
        assert po.is_consumed is True
        assert ctx['cancel'] is True
        assert s.is_consumed is True

    def test_activate_ignores_non_powanfa(self, mock_game, owner):
        s = season2.JinShen(owner, mock_game)
        chu = season1.ChuNeng(owner, mock_game)
        ctx = {'activated_skill': chu, 'cancel': False}
        result = s.activate(GameEvent.SKILL_ACTIVATED, ctx)
        assert result is False


# ---------- YingYan ----------
class TestSeason2YingYan:
    def test_can_trigger_game_start(self, mock_game, owner):
        s = season2.YingYan(owner, mock_game)
        assert s.can_trigger(GameEvent.GAME_START, {})

    def test_can_trigger_turn_start(self, mock_game, owner):
        s = season2.YingYan(owner, mock_game)
        assert s.can_trigger(GameEvent.TURN_START, {'player': owner})

    def test_urgency_low(self, mock_game, owner):
        s = season2.YingYan(owner, mock_game)
        assert s.evaluate_urgency(mock_game) == 30

    def test_activate_game_start_ai_looks(self, mock_game, owner):
        s = season2.YingYan(owner, mock_game)
        owner.is_human = False
        result = s.activate(GameEvent.GAME_START, {})
        assert result is False

    def test_activate_turn_start_shows_top5(self, mock_game, owner):
        s = season2.YingYan(owner, mock_game)
        owner.is_human = False
        before = len(mock_game.deck.cards)
        result = s.activate(GameEvent.TURN_START, {'player': owner})
        assert result is True
        assert s.is_consumed is True
        assert len(mock_game.deck.cards) == before


# ---------- GuYongZhe ----------
class TestSeason2GuYongZhe:
    def test_after_draw_increments(self, mock_game, owner):
        s = season2.GuYongZhe(owner, mock_game)
        s.can_trigger(GameEvent.AFTER_DRAW, {'player': owner})
        s.can_trigger(GameEvent.AFTER_DRAW, {'player': owner})
        assert s.draw_count == 2

    def test_after_draw_only_counts_owner(self, mock_game, owner):
        s = season2.GuYongZhe(owner, mock_game)
        s.can_trigger(GameEvent.AFTER_DRAW, {'player': mock_game.players[1]})
        assert s.draw_count == 0
        s.can_trigger(GameEvent.AFTER_DRAW, {'player': owner})
        assert s.draw_count == 1

    def test_urgency_at_7_draws(self, mock_game, owner):
        s = season2.GuYongZhe(owner, mock_game)
        s.draw_count = 7
        assert s.evaluate_urgency(mock_game) == 90

    def test_urgency_below_7_draws(self, mock_game, owner):
        s = season2.GuYongZhe(owner, mock_game)
        s.draw_count = 5
        assert s.evaluate_urgency(mock_game) == 0

    def test_activate_turn_start_sends_7(self, mock_game, owner):
        s = season2.GuYongZhe(owner, mock_game)
        s.draw_count = 7
        with patch.object(mock_game, 'apply_add_cards') as mock_add:
            result = s.activate(GameEvent.TURN_START, {'player': owner})
        assert result is True
        assert mock_add.call_count == len(mock_game.players) - 1
        assert s.draw_count == 0


# ---------- WangYou ----------
class TestSeason2WangYou:
    def test_can_trigger_player_died(self, mock_game, owner):
        s = season2.WangYou(owner, mock_game)
        assert s.can_trigger(GameEvent.PLAYER_DIED, {'player': owner})

    def test_cannot_trigger_other_player(self, mock_game, owner, other_player):
        s = season2.WangYou(owner, mock_game)
        assert not s.can_trigger(GameEvent.PLAYER_DIED, {'player': other_player})

    def test_activate_with_available_skill(self, mock_game, owner):
        s = season2.WangYou(owner, mock_game)
        other = mock_game.players[1]
        stolen = season1.PoWanFa(other, mock_game)
        stolen.is_consumed = True
        other.skills = [stolen]
        with patch.object(mock_game.skill_manager, 'execute_skill'):
            result = s.activate(GameEvent.PLAYER_DIED, {'player': owner})
        assert result is True
        assert s.is_consumed is True

    def test_activate_no_available_skills(self, mock_game, owner):
        s = season2.WangYou(owner, mock_game)
        for p in mock_game.players:
            p.skills = []
        result = s.activate(GameEvent.PLAYER_DIED, {'player': owner})
        assert result is True
        assert s.is_consumed is True


# ---------- SuQin + ZhangYi 组合技 ----------
class TestSeason2Combo:
    def test_combo_consumes_both(self, mock_game, owner):
        suqin = season2.SuQin(owner, mock_game)
        zhangyi = season2.ZhangYi(owner, mock_game)
        owner.skills = [suqin, zhangyi]
        combo = season2.SuQinZhangYiCombo()
        with patch('random.randint', return_value=6):
            combo.execute(owner, mock_game.skill_manager, mock_game)
        assert suqin.is_consumed
        assert zhangyi.is_consumed

    def test_combo_low_roll_sends_cards(self, mock_game, owner):
        suqin = season2.SuQin(owner, mock_game)
        zhangyi = season2.ZhangYi(owner, mock_game)
        owner.skills = [suqin, zhangyi]
        combo = season2.SuQinZhangYiCombo()
        with patch('random.randint', return_value=1), \
             patch.object(mock_game, 'apply_add_cards') as mock_add:
            combo.execute(owner, mock_game.skill_manager, mock_game)
        assert mock_add.call_count == len(mock_game.players)


# ==================== Season 3（占位） ====================
class TestSeason3:
    def test_metadata_exists(self):
        assert hasattr(season3, 'SEASON_ID')
        assert hasattr(season3, 'SEASON_NAME')
        assert hasattr(season3, 'SKILL_CLASSES')
        assert isinstance(season3.SKILL_CLASSES, list)

    def test_loader_does_not_crash(self, mock_game):
        result = SkillLoader.load_skills(['S3'], mock_game)
        assert isinstance(result, tuple)
        assert len(result) == 3


# ==================== Season 4 技能 ====================
# ---------- YanPin ----------
class TestSeason4YanPin:
    def test_can_trigger(self, mock_game, owner):
        s = season4.YanPin(owner, mock_game)
        assert s.can_trigger(GameEvent.TURN_START, {'player': owner})

    def test_activate_no_hand(self, mock_game, owner):
        s = season4.YanPin(owner, mock_game)
        owner.hand = []
        assert s.activate(GameEvent.TURN_START, {'player': owner}) is False

    def test_activate_ai_changes_random_card(self, mock_game, owner):
        """AI 分支：先选卡，再选新颜色，再选新数字。"""
        s = season4.YanPin(owner, mock_game)
        owner.is_human = False
        card = Card('红', '数字', 3)
        owner.hand = [card]
        # 第一次 choice 从手牌选卡 → 返回 card
        # 第二次 choice 选新颜色 → 返回 '蓝'
        with patch('random.choice', side_effect=[card, '蓝']), \
             patch('random.randint', return_value=7):
            result = s.activate(GameEvent.TURN_START, {'player': owner})
        assert result is True
        assert s.is_consumed is True
        assert card.color == '蓝'
        assert card.value == 7

    def test_activate_ai_changes_non_number(self, mock_game, owner):
        """非数字牌只改颜色，不改数字。"""
        s = season4.YanPin(owner, mock_game)
        owner.is_human = False
        card = Card('红', '跳过')
        owner.hand = [card]
        with patch('random.choice', side_effect=[card, '绿']):
            result = s.activate(GameEvent.TURN_START, {'player': owner})
        assert result is True
        assert card.color == '绿'
        assert card.type == '跳过'

    def test_activate_human_changes_color_and_value(self, mock_game, human_player):
        s = season4.YanPin(human_player, mock_game)
        human_player.is_human = True
        human_player.hand = [Card('红', '数字', 3)]
        human_player.ui.input = MagicMock(side_effect=['0', '蓝', '7'])
        result = s.activate(GameEvent.TURN_START, {'player': human_player})
        assert result is True
        assert human_player.hand[0].color == '蓝'
        assert human_player.hand[0].value == 7

    def test_activate_human_keeps_color_if_empty(self, mock_game, human_player):
        s = season4.YanPin(human_player, mock_game)
        human_player.is_human = True
        human_player.hand = [Card('红', '数字', 3)]
        human_player.ui.input = MagicMock(side_effect=['0', '', ''])
        result = s.activate(GameEvent.TURN_START, {'player': human_player})
        assert result is True
        assert human_player.hand[0].color == '红'


# ---------- TanNang ----------
class TestSeason4TanNang:
    def test_can_trigger(self, mock_game, owner):
        s = season4.TanNang(owner, mock_game)
        assert s.can_trigger(GameEvent.TURN_START, {'player': owner})

    def test_urgency_with_low_hand(self, mock_game, owner):
        s = season4.TanNang(owner, mock_game)
        mock_game.players[1].hand = [Card('红', '数字', 1)]
        assert s.evaluate_urgency(mock_game) == 75

    def test_urgency_default(self, mock_game, owner):
        s = season4.TanNang(owner, mock_game)
        for p in mock_game.players[1:]:
            p.hand = [Card('红', '数字', i) for i in range(7)]
        assert s.evaluate_urgency(mock_game) == 55

    def test_activate_ai_steals_random_card(self, mock_game, owner):
        s = season4.TanNang(owner, mock_game)
        owner.is_human = False
        target = mock_game.players[1]
        target.hand = [Card('红', '数字', 1), Card('蓝', '跳过')]
        before_owner = len(owner.hand)
        before_target = len(target.hand)
        with patch.object(s, '_choose_target', return_value=target):
            result = s.activate(GameEvent.TURN_START, {'player': owner})
        assert result is True
        assert s.is_consumed is True
        assert len(owner.hand) == before_owner + 1
        assert len(target.hand) == before_target - 1

    def test_activate_ai_target_empty_hand(self, mock_game, owner):
        s = season4.TanNang(owner, mock_game)
        owner.is_human = False
        target = mock_game.players[1]
        target.hand = []
        with patch.object(s, '_choose_target', return_value=target):
            result = s.activate(GameEvent.TURN_START, {'player': owner})
        assert result is False

    def test_activate_human_steals_named_card(self, mock_game, human_player):
        s = season4.TanNang(human_player, mock_game)
        human_player.is_human = True
        target = mock_game.players[1]
        target.hand = [Card('红', '数字', 5), Card('蓝', '跳过')]
        human_player.ui.input = MagicMock(return_value='红5')
        with patch.object(s, '_choose_target', return_value=target):
            result = s.activate(GameEvent.TURN_START, {'player': human_player})
        assert result is True
        assert any(c.color == '红' and c.value == 5 for c in human_player.hand)

    def test_activate_human_target_missing_card(self, mock_game, human_player):
        s = season4.TanNang(human_player, mock_game)
        human_player.is_human = True
        target = mock_game.players[1]
        target.hand = [Card('蓝', '跳过')]
        human_player.ui.input = MagicMock(return_value='红5')
        with patch.object(s, '_choose_target', return_value=target):
            result = s.activate(GameEvent.TURN_START, {'player': human_player})
        assert result is False

    def test_parse_card_wild(self, mock_game, owner):
        s = season4.TanNang(owner, mock_game)
        assert s._parse_card('万能').type == '万能'

    def test_parse_card_wild4(self, mock_game, owner):
        s = season4.TanNang(owner, mock_game)
        assert s._parse_card('万能+4').type == '万能+4'

    def test_parse_card_action(self, mock_game, owner):
        s = season4.TanNang(owner, mock_game)
        card = s._parse_card('蓝跳过')
        assert card is not None
        assert card.color == '蓝'
        assert card.type == '跳过'

    def test_parse_card_invalid(self, mock_game, owner):
        s = season4.TanNang(owner, mock_game)
        assert s._parse_card('???') is None


# ---------- XianLing ----------
class TestSeason4XianLing:
    def test_can_trigger(self, mock_game, owner):
        s = season4.XianLing(owner, mock_game)
        assert s.can_trigger(GameEvent.TURN_START, {'player': owner})

    def test_activate_ai_counts_cards(self, mock_game, owner):
        s = season4.XianLing(owner, mock_game)
        owner.is_human = False
        mock_game.players[1].hand = [Card('红', '数字', 3)]
        with patch('random.choice', return_value='红'), \
             patch('random.randint', return_value=3):
            result = s.activate(GameEvent.TURN_START, {'player': owner})
        assert result is True
        assert s.is_consumed is True

    def test_activate_human_valid_input(self, mock_game, human_player):
        s = season4.XianLing(human_player, mock_game)
        human_player.is_human = True
        mock_game.players[1].hand = [Card('红', '数字', 3)]
        human_player.ui.input = MagicMock(return_value='红3')
        result = s.activate(GameEvent.TURN_START, {'player': human_player})
        assert result is True

    def test_activate_human_action_card(self, mock_game, human_player):
        s = season4.XianLing(human_player, mock_game)
        human_player.is_human = True
        human_player.ui.input = MagicMock(return_value='蓝跳过')
        result = s.activate(GameEvent.TURN_START, {'player': human_player})
        assert result is True

    def test_activate_human_invalid_input(self, mock_game, human_player):
        s = season4.XianLing(human_player, mock_game)
        human_player.is_human = True
        human_player.ui.input = MagicMock(return_value='???')
        result = s.activate(GameEvent.TURN_START, {'player': human_player})
        assert result is False


# ---------- JiaHuo ----------
class TestSeason4JiaHuo:
    def test_can_trigger_when_targeted(self, mock_game, owner):
        s = season4.JiaHuo(owner, mock_game)
        assert s.can_trigger(GameEvent.SKILL_ACTIVATED,
                             {'original_context': {'target': owner}})

    def test_cannot_trigger_when_not_targeted(self, mock_game, owner, other_player):
        s = season4.JiaHuo(owner, mock_game)
        assert not s.can_trigger(GameEvent.SKILL_ACTIVATED,
                                 {'original_context': {'target': other_player}})

    def test_activate_redirects(self, mock_game, owner):
        s = season4.JiaHuo(owner, mock_game)
        other = mock_game.players[1]
        orig = {'target': owner}
        ctx = {'original_context': orig}
        with patch.object(s, '_choose_target', return_value=other):
            result = s.activate(GameEvent.SKILL_ACTIVATED, ctx)
        assert result is True
        assert orig['target'] is other
        assert s.is_consumed is True

    def test_activate_no_target_returns_false(self, mock_game, owner):
        s = season4.JiaHuo(owner, mock_game)
        orig = {'target': owner}
        ctx = {'original_context': orig}
        with patch.object(s, '_choose_target', return_value=None):
            result = s.activate(GameEvent.SKILL_ACTIVATED, ctx)
        assert result is False


# ---------- JiFa ----------
class TestSeason4JiFa:
    @staticmethod
    def _stock_skill_pool(mock_game, count=30):
        """给 skill_pool 灌入足够的技能，让 JiFa 有牌可分。"""
        from uno.season1 import (
            PoWanFa, QiaoWu, ShengShengBuXi, ChuNeng, QiangYun,
            LiXi, HuaXing, HuoShui, BuMie, WuJianDao,
            DuXin, DianRen, ZhaoZai, JingLei, NongYan
        )
        classes = [PoWanFa, QiaoWu, ShengShengBuXi, ChuNeng, QiangYun,
                   LiXi, HuaXing, HuoShui, BuMie, WuJianDao,
                   DuXin, DianRen, ZhaoZai, JingLei, NongYan]
        while len(mock_game.skill_pool) < count:
            for cls in classes:
                if len(mock_game.skill_pool) >= count:
                    break
                mock_game.skill_pool.append(cls(owner=None, game=mock_game))

    def test_can_trigger(self, mock_game, owner):
        s = season4.JiFa(owner, mock_game)
        assert s.can_trigger(GameEvent.TURN_START, {'player': owner})

    def test_urgency_low(self, mock_game, owner):
        s = season4.JiFa(owner, mock_game)
        assert s.evaluate_urgency(mock_game) == 30

    def test_activate_ai_redistributes(self, mock_game, owner):
        self._stock_skill_pool(mock_game)
        s = season4.JiFa(owner, mock_game)
        owner.is_human = False
        result = s.activate(GameEvent.TURN_START, {'player': owner})
        assert result is True
        assert s.is_consumed is True
        for p in mock_game.players:
            assert len(p.skills) >= 1

    def test_activate_insufficient_pool_returns_false(self, mock_game, owner):
        s = season4.JiFa(owner, mock_game)
        owner.is_human = False
        mock_game.skill_pool.clear()
        result = s.activate(GameEvent.TURN_START, {'player': owner})
        assert result is False

    def test_activate_human_picks_3(self, mock_game, human_player):
        self._stock_skill_pool(mock_game)
        s = season4.JiFa(human_player, mock_game)
        human_player.is_human = True
        human_player.ui.input = MagicMock(side_effect=['0', '1', '2'])
        result = s.activate(GameEvent.TURN_START, {'player': human_player})
        assert result is True
        assert s.is_consumed is True

    def test_activate_human_rejects_duplicate(self, mock_game, human_player):
        self._stock_skill_pool(mock_game)
        s = season4.JiFa(human_player, mock_game)
        human_player.is_human = True
        human_player.ui.input = MagicMock(side_effect=['0', '0', '1', '2'])
        result = s.activate(GameEvent.TURN_START, {'player': human_player})
        assert result is True


# ---------- YeLi ----------
class TestSeason4YeLi:
    def test_can_trigger(self, mock_game, owner):
        s = season4.YeLi(owner, mock_game)
        assert s.can_trigger(GameEvent.TURN_START, {'player': owner})

    def test_activate_ai_guess_correct(self, mock_game, owner):
        s = season4.YeLi(owner, mock_game)
        owner.is_human = False
        target = mock_game.players[1]
        target.hand = [Card('红', '数字', 1), Card('红', '数字', 2),
                       Card('蓝', '数字', 3)]
        with patch.object(s, '_choose_target', return_value=target), \
             patch('random.choice', return_value='红'), \
             patch.object(mock_game, 'apply_add_cards') as mock_add:
            result = s.activate(GameEvent.TURN_START, {'player': owner})
        assert result is True
        assert mock_add.call_args[0][0] is target
        assert mock_add.call_args[0][1] == 8

    def test_activate_ai_guess_wrong(self, mock_game, owner):
        s = season4.YeLi(owner, mock_game)
        owner.is_human = False
        target = mock_game.players[1]
        target.hand = [Card('红', '数字', 1), Card('红', '数字', 2)]
        with patch.object(s, '_choose_target', return_value=target), \
             patch('random.choice', return_value='蓝'), \
             patch.object(mock_game, 'apply_add_cards') as mock_add:
            result = s.activate(GameEvent.TURN_START, {'player': owner})
        assert result is True
        assert mock_add.call_args[0][0] is owner
        assert mock_add.call_args[0][1] == 5

    def test_activate_human_guesses(self, mock_game, human_player):
        s = season4.YeLi(human_player, mock_game)
        human_player.is_human = True
        target = mock_game.players[1]
        target.hand = [Card('红', '数字', 1)]
        human_player.ui.input = MagicMock(return_value='0')
        with patch.object(s, '_choose_target', return_value=target), \
             patch.object(mock_game, 'apply_add_cards') as mock_add:
            result = s.activate(GameEvent.TURN_START, {'player': human_player})
        assert result is True
        assert mock_add.call_args[0][1] == 8


# ---------- DuoXinPo ----------
class TestSeason4DuoXinPo:
    def test_can_trigger(self, mock_game, owner):
        s = season4.DuoXinPo(owner, mock_game)
        assert s.can_trigger(GameEvent.BEING_ADDED_CARDS,
                             {'target': owner, 'amount': 5})

    def test_cannot_trigger_for_other(self, mock_game, owner, other_player):
        s = season4.DuoXinPo(owner, mock_game)
        assert not s.can_trigger(GameEvent.BEING_ADDED_CARDS,
                                 {'target': other_player, 'amount': 5})

    def test_activate_ai_picks_two_victims(self, mock_game, owner):
        s = season4.DuoXinPo(owner, mock_game)
        owner.is_human = False
        ctx = {'target': owner, 'amount': 3, 'cancel': False}
        with patch.object(mock_game, 'apply_add_cards') as mock_add, \
             patch('random.sample', side_effect=lambda seq, k: list(seq)[:k]):
            result = s.activate(GameEvent.BEING_ADDED_CARDS, ctx)
        assert result is True
        assert s.is_consumed is True
        assert mock_add.call_count >= 1

    def test_activate_human_picks_victims(self, mock_game, human_player):
        s = season4.DuoXinPo(human_player, mock_game)
        human_player.is_human = True
        ctx = {'target': human_player, 'amount': 3, 'cancel': False}
        human_player.ui.input = MagicMock(return_value='0,1')
        with patch.object(mock_game, 'apply_add_cards') as mock_add:
            result = s.activate(GameEvent.BEING_ADDED_CARDS, ctx)
        assert result is True
        assert mock_add.call_count == 2

    def test_activate_human_cancel(self, mock_game, human_player):
        s = season4.DuoXinPo(human_player, mock_game)
        human_player.is_human = True
        ctx = {'target': human_player, 'amount': 3, 'cancel': False}
        human_player.ui.input = MagicMock(return_value='')
        result = s.activate(GameEvent.BEING_ADDED_CARDS, ctx)
        assert result is False

    def test_activate_no_other_players(self, mock_game, owner):
        s = season4.DuoXinPo(owner, mock_game)
        for p in mock_game.players[1:]:
            p.eliminated = True
        ctx = {'target': owner, 'amount': 3, 'cancel': False}
        result = s.activate(GameEvent.BEING_ADDED_CARDS, ctx)
        assert result is False


# ---------- HunQian ----------
class TestSeason4HunQian:
    def test_can_trigger(self, mock_game, owner):
        s = season4.HunQian(owner, mock_game)
        assert s.can_trigger(GameEvent.BEING_ADDED_CARDS,
                             {'target': owner, 'amount': 5})

    def test_cannot_trigger_for_other(self, mock_game, owner, other_player):
        s = season4.HunQian(owner, mock_game)
        assert not s.can_trigger(GameEvent.BEING_ADDED_CARDS,
                                 {'target': other_player, 'amount': 5})

    def test_activate_consumes_before_transfer(self, mock_game, owner):
        s = season4.HunQian(owner, mock_game)
        ctx = {'target': owner, 'amount': 3, 'cancel': False}
        with patch.object(mock_game, 'apply_add_cards') as mock_add:
            result = s.activate(GameEvent.BEING_ADDED_CARDS, ctx)
        assert result is True
        assert s.is_consumed is True
        assert ctx['cancel'] is True
        mock_add.assert_called_once()

    def test_activate_transfers_to_random_player(self, mock_game, owner):
        s = season4.HunQian(owner, mock_game)
        ctx = {'target': owner, 'amount': 3, 'cancel': False}
        with patch('random.choice', return_value=mock_game.players[1]), \
             patch.object(mock_game, 'apply_add_cards') as mock_add:
            s.activate(GameEvent.BEING_ADDED_CARDS, ctx)
        assert mock_add.call_args[0][0] is mock_game.players[1]
        assert mock_add.call_args[0][1] == 3

# ==================== Season 1 技能 ====================
# ---------- PoWanFa（破万法）----------
class TestSeason1PoWanFa:
    def test_can_trigger_skill_activated(self, mock_game, owner):
        s = season1.PoWanFa(owner, mock_game)
        other_skill = season1.ChuNeng(mock_game.players[1], mock_game)
        ctx = {'activated_skill': other_skill}
        assert s.can_trigger(GameEvent.SKILL_ACTIVATED, ctx)

    def test_cannot_trigger_empty_context(self, mock_game, owner):
        s = season1.PoWanFa(owner, mock_game)
        assert not s.can_trigger(GameEvent.SKILL_ACTIVATED, {})

    def test_cannot_trigger_when_consumed(self, mock_game, owner):
        s = season1.PoWanFa(owner, mock_game)
        s.is_consumed = True
        other_skill = season1.ChuNeng(mock_game.players[1], mock_game)
        ctx = {'activated_skill': other_skill}
        assert not s.can_trigger(GameEvent.SKILL_ACTIVATED, ctx)

    def test_activate_breaks_other_skill(self, mock_game, owner):
        s = season1.PoWanFa(owner, mock_game)
        other = mock_game.players[1]
        target = season1.ChuNeng(other, mock_game)
        ctx = {'activated_skill': target, 'cancel': False}
        result = s.activate(GameEvent.SKILL_ACTIVATED, ctx)
        assert result is True
        assert target.is_consumed is True
        assert ctx['cancel'] is True
        assert s.is_consumed is True

    def test_activate_ignores_own_skill(self, mock_game, owner):
        s = season1.PoWanFa(owner, mock_game)
        target = season1.ChuNeng(owner, mock_game)
        ctx = {'activated_skill': target, 'cancel': False}
        result = s.activate(GameEvent.SKILL_ACTIVATED, ctx)
        assert result is False


# ---------- QiaoWu（巧物）----------
class TestSeason1QiaoWu:
    def test_can_trigger_turn_start(self, mock_game, owner):
        s = season1.QiaoWu(owner, mock_game)
        assert s.can_trigger(GameEvent.TURN_START, {})

    def test_activate_no_available_skills(self, mock_game, owner):
        s = season1.QiaoWu(owner, mock_game)
        mock_game.skill_pool.clear()
        result = s.activate(GameEvent.TURN_START, {})
        assert result is False

    def test_activate_ai_copies_random_skill(self, mock_game, owner):
        s = season1.QiaoWu(owner, mock_game)
        owner.is_human = False
        # 确保技能池里有可复制的技能
        target = season1.ZhaoZai(mock_game.players[1], mock_game)
        mock_game.skill_pool = [target]
        with patch.object(target, 'activate') as mock_act:
            result = s.activate(GameEvent.TURN_START, {})
        assert result is True
        assert s.is_consumed is True

    def test_activate_human_picks_from_list(self, mock_game, human_player):
        s = season1.QiaoWu(human_player, mock_game)
        human_player.is_human = True
        target = season1.ZhaoZai(mock_game.players[1], mock_game)
        mock_game.skill_pool = [target]
        human_player.ui.input = MagicMock(return_value='0')
        with patch.object(target.__class__, 'activate'):
            result = s.activate(GameEvent.TURN_START, {})
        assert result is True
        assert s.is_consumed is True


# ---------- ShengShengBuXi（生生不息）----------
class TestSeason1ShengShengBuXi:
    def test_can_trigger_player_died_self(self, mock_game, owner):
        s = season1.ShengShengBuXi(owner, mock_game)
        assert s.can_trigger(GameEvent.PLAYER_DIED, {'player': owner})

    def test_cannot_trigger_other_player(self, mock_game, owner, other_player):
        s = season1.ShengShengBuXi(owner, mock_game)
        assert not s.can_trigger(GameEvent.PLAYER_DIED, {'player': other_player})

    def test_activate_revives_with_5_cards(self, mock_game, owner):
        s = season1.ShengShengBuXi(owner, mock_game)
        owner.eliminated = True
        owner.hand = []
        result = s.activate(GameEvent.PLAYER_DIED, {'player': owner})
        assert result is True
        assert owner.eliminated is False
        assert owner.hand_limit == 25
        assert len(owner.hand) == 5
        assert s.is_consumed is True


# ---------- ChuNeng（储能）----------
class TestSeason1ChuNeng:
    def test_can_trigger_skill_activated(self, mock_game, owner):
        s = season1.ChuNeng(owner, mock_game)
        other_skill = season1.ZhaoZai(mock_game.players[1], mock_game)
        assert s.can_trigger(GameEvent.SKILL_ACTIVATED, {'activated_skill': other_skill})

    def test_activate_steals_skill(self, mock_game, owner):
        s = season1.ChuNeng(owner, mock_game)
        other = mock_game.players[1]
        target = season1.ZhaoZai(other, mock_game)
        other.skills = [target]
        ctx = {'activated_skill': target, 'cancel': False}
        result = s.activate(GameEvent.SKILL_ACTIVATED, ctx)
        assert result is True
        assert target.owner is owner
        assert target in owner.skills
        assert target not in other.skills
        assert target.is_consumed is False
        assert ctx['cancel'] is True
        assert s.is_consumed is True

    def test_activate_ignores_own_skill(self, mock_game, owner):
        s = season1.ChuNeng(owner, mock_game)
        target = season1.ZhaoZai(owner, mock_game)
        ctx = {'activated_skill': target, 'cancel': False}
        result = s.activate(GameEvent.SKILL_ACTIVATED, ctx)
        assert result is False


# ---------- QiangYun（强运）----------
class TestSeason1QiangYun:
    def test_can_trigger_game_start(self, mock_game, owner):
        s = season1.QiangYun(owner, mock_game)
        assert s.can_trigger(GameEvent.GAME_START, {})

    def test_activate_gets_1_or_2_skills(self, mock_game, owner):
        s = season1.QiangYun(owner, mock_game)
        owner.skills = []
        # 技能池准备至少 2 个可分配的技能
        pool = [season1.ZhaoZai(None, mock_game) for _ in range(5)]
        for i, sk in enumerate(pool):
            sk.owner = None
        mock_game.skill_pool = pool
        with patch('random.randint', return_value=2):
            result = s.activate(GameEvent.GAME_START, {})
        assert result is True
        assert s.is_consumed is True
        # 至少获得 1 张（如果池子足够就是 2 张）
        assert len(owner.skills) >= 1


# ---------- LiXi（离析）----------
class TestSeason1LiXi:
    def test_can_trigger_being_added(self, mock_game, owner):
        s = season1.LiXi(owner, mock_game)
        assert s.can_trigger(GameEvent.BEING_ADDED_CARDS,
                             {'target': owner, 'amount': 5})

    def test_cannot_trigger_for_other(self, mock_game, owner, other_player):
        s = season1.LiXi(owner, mock_game)
        assert not s.can_trigger(GameEvent.BEING_ADDED_CARDS,
                                 {'target': other_player, 'amount': 5})

    def test_activate_cancels_add(self, mock_game, owner):
        s = season1.LiXi(owner, mock_game)
        ctx = {'target': owner, 'amount': 5, 'cancel': False}
        result = s.activate(GameEvent.BEING_ADDED_CARDS, ctx)
        assert result is True
        assert ctx['cancel'] is True
        assert s.is_consumed is True

    def test_urgency_high_with_many_cards(self, mock_game, owner):
        s = season1.LiXi(owner, mock_game)
        owner.hand = [Card('红', '数字', i) for i in range(10)]
        assert s.evaluate_urgency(mock_game) == 80

    def test_urgency_default(self, mock_game, owner):
        s = season1.LiXi(owner, mock_game)
        owner.hand = [Card('红', '数字', 1)]
        assert s.evaluate_urgency(mock_game) == 50


# ---------- HuaXing（化形）----------
class TestSeason1HuaXing:
    def test_can_trigger_turn_start(self, mock_game, owner):
        s = season1.HuaXing(owner, mock_game)
        assert s.can_trigger(GameEvent.TURN_START, {'player': owner})

    def test_urgency_high_when_few_cards(self, mock_game, owner):
        s = season1.HuaXing(owner, mock_game)
        owner.hand = [Card('红', '数字', 1)]
        assert s.evaluate_urgency(mock_game) == 70

    def test_urgency_low_when_many_cards(self, mock_game, owner):
        s = season1.HuaXing(owner, mock_game)
        owner.hand = [Card('红', '数字', i) for i in range(13)]
        assert s.evaluate_urgency(mock_game) == 20

    def test_urgency_medium(self, mock_game, owner):
        s = season1.HuaXing(owner, mock_game)
        owner.hand = [Card('红', '数字', i) for i in range(6)]
        assert s.evaluate_urgency(mock_game) == 45

    def test_activate_no_other_players(self, mock_game, owner):
        s = season1.HuaXing(owner, mock_game)
        for p in mock_game.players[1:]:
            p.eliminated = True
        result = s.activate(GameEvent.TURN_START, {'player': owner})
        assert result is False

    def test_activate_swaps_hands_ai(self, mock_game, owner):
        s = season1.HuaXing(owner, mock_game)
        owner.is_human = False
        target = mock_game.players[1]
        owner.hand = [Card('红', '数字', 1)]
        target.hand = [Card('蓝', '数字', 2)]
        # 第一次 random.choice（choose_target 内部）→ 返回 target
        # 第二次 random.choice（mode 选择）→ 返回 True 走"手牌"
        with patch('random.choice', side_effect=[target, True]):
            result = s.activate(GameEvent.TURN_START, {'player': owner})
        assert result is True
        assert s.is_consumed is True
        # 交换后，owner 拿到对方的牌
        assert len(owner.hand) == 1
        assert owner.hand[0].color == '蓝'
        assert target.hand[0].color == '红'

    def test_activate_swaps_skills_ai(self, mock_game, owner):
        """AI 分支交换技能。"""
        s = season1.HuaXing(owner, mock_game)
        owner.is_human = False
        target = mock_game.players[1]
        owner_skill = season1.ZhaoZai(owner, mock_game)
        target_skill = season1.JingLei(target, mock_game)
        owner.skills = [owner_skill]
        target.skills = [target_skill]
        # 第一次 random.choice 选目标，第二次 random.choice 返回 False 走"技能"
        with patch('random.choice', side_effect=[target, False]):
            result = s.activate(GameEvent.TURN_START, {'player': owner})
        assert result is True
        assert s.is_consumed is True
        # 技能交换后，owner 拥有 target 的旧技能
        assert target_skill in owner.skills
        assert owner_skill in target.skills
        assert target_skill.owner is owner
        assert owner_skill.owner is target

    def test_activate_human_swaps_hands(self, mock_game, human_player):
        s = season1.HuaXing(human_player, mock_game)
        human_player.is_human = True
        target = mock_game.players[1]
        human_player.hand = [Card('红', '数字', 1)]
        target.hand = [Card('蓝', '数字', 2)]
        # 直接 patch choose_target，避开 random.choice 冲突
        # 人类只走一次 input："1" 表示交换手牌
        human_player.ui.input = MagicMock(return_value='1')
        with patch.object(s, 'choose_target', return_value=target):
            result = s.activate(GameEvent.TURN_START, {'player': human_player})
        assert result is True
        assert s.is_consumed is True
        assert human_player.hand[0].color == '蓝'
        assert target.hand[0].color == '红'

    def test_activate_human_swaps_skills(self, mock_game, human_player):
        s = season1.HuaXing(human_player, mock_game)
        human_player.is_human = True
        target = mock_game.players[1]
        owner_skill = season1.ZhaoZai(human_player, mock_game)
        target_skill = season1.JingLei(target, mock_game)
        human_player.skills = [owner_skill]
        target.skills = [target_skill]
        # 人类输入 "2" 表示交换技能
        human_player.ui.input = MagicMock(return_value='2')
        with patch.object(s, 'choose_target', return_value=target):
            result = s.activate(GameEvent.TURN_START, {'player': human_player})
        assert result is True
        assert s.is_consumed is True
        assert target_skill in human_player.skills
        assert owner_skill in target.skills

    def test_choose_target_ai(self, mock_game, owner):
        s = season1.HuaXing(owner, mock_game)
        owner.is_human = False
        target = s.choose_target()
        assert target is not None
        assert target is not owner
        assert not target.eliminated

    def test_choose_target_human(self, mock_game, human_player):
        s = season1.HuaXing(human_player, mock_game)
        human_player.is_human = True
        human_player.ui.input = MagicMock(return_value='0')
        target = s.choose_target()
        assert target is not None
        assert target is not human_player

    def test_choose_target_no_candidates(self, mock_game, owner):
        s = season1.HuaXing(owner, mock_game)
        for p in mock_game.players[1:]:
            p.eliminated = True
        assert s.choose_target() is None


# ---------- HuoShui（祸水）----------
class TestSeason1HuoShui:
    def test_can_trigger_being_added(self, mock_game, owner):
        s = season1.HuoShui(owner, mock_game)
        assert s.can_trigger(GameEvent.BEING_ADDED_CARDS,
                             {'target': owner, 'amount': 5})

    def test_urgency_high_with_many(self, mock_game, owner):
        s = season1.HuoShui(owner, mock_game)
        owner.hand = [Card('红', '数字', i) for i in range(10)]
        assert s.evaluate_urgency(mock_game) == 80

    def test_urgency_default(self, mock_game, owner):
        s = season1.HuoShui(owner, mock_game)
        owner.hand = [Card('红', '数字', 1)]
        assert s.evaluate_urgency(mock_game) == 50

    def test_activate_transfers_to_other(self, mock_game, owner):
        s = season1.HuoShui(owner, mock_game)
        ctx = {'target': owner, 'amount': 5, 'cancel': False}
        with patch.object(s, 'choose_target', return_value=mock_game.players[1]):
            result = s.activate(GameEvent.BEING_ADDED_CARDS, ctx)
        assert result is True
        assert ctx['target'] is mock_game.players[1]
        assert s.is_consumed is True

    def test_activate_no_target_returns_false(self, mock_game, owner):
        s = season1.HuoShui(owner, mock_game)
        ctx = {'target': owner, 'amount': 5, 'cancel': False}
        with patch.object(s, 'choose_target', return_value=None):
            result = s.activate(GameEvent.BEING_ADDED_CARDS, ctx)
        assert result is False


# ---------- BuMie（不灭）----------
class TestSeason1BuMie:
    def test_can_trigger_player_died_self(self, mock_game, owner):
        s = season1.BuMie(owner, mock_game)
        assert s.can_trigger(GameEvent.PLAYER_DIED, {'player': owner})

    def test_cannot_trigger_other(self, mock_game, owner, other_player):
        s = season1.BuMie(owner, mock_game)
        assert not s.can_trigger(GameEvent.PLAYER_DIED, {'player': other_player})

    def test_activate_revives_trims_hand(self, mock_game, owner):
        s = season1.BuMie(owner, mock_game)
        owner.eliminated = True
        owner.hand = [Card('红', '数字', i) for i in range(15)]
        # 给一个额外技能，方便测试"丢弃 1 张技能"
        extra = season1.ZhaoZai(owner, mock_game)
        owner.skills = [s, extra]
        result = s.activate(GameEvent.PLAYER_DIED, {'player': owner})
        assert result is True
        assert owner.eliminated is False
        assert len(owner.hand) == 10
        assert s.is_consumed is True
        # 额外技能被丢弃
        assert extra not in owner.skills


# ---------- WuJianDao（无间道）----------
class TestSeason1WuJianDao:
    def test_can_trigger_turn_start_unbound(self, mock_game, owner):
        s = season1.WuJianDao(owner, mock_game)
        assert s.can_trigger(GameEvent.TURN_START, {'player': owner})

    def test_cannot_trigger_turn_start_bound(self, mock_game, owner):
        s = season1.WuJianDao(owner, mock_game)
        s.bound_target = mock_game.players[1]
        assert not s.can_trigger(GameEvent.TURN_START, {'player': owner})

    def test_can_trigger_cards_added_on_target(self, mock_game, owner):
        s = season1.WuJianDao(owner, mock_game)
        target = mock_game.players[1]
        s.bound_target = target
        assert s.can_trigger(GameEvent.CARDS_ADDED, {'target': target, 'amount': 3})

    def test_activate_turn_start_binds(self, mock_game, owner):
        s = season1.WuJianDao(owner, mock_game)
        target = mock_game.players[1]
        with patch.object(s, 'choose_target', return_value=target):
            result = s.activate(GameEvent.TURN_START, {'player': owner})
        assert result is True
        assert s.bound_target is target
        assert s.times_left == 3

    def test_activate_cards_added_removes_cards(self, mock_game, owner):
        s = season1.WuJianDao(owner, mock_game)
        target = mock_game.players[1]
        s.bound_target = target
        s.times_left = 3
        owner.hand = [Card('红', '数字', i) for i in range(10)]
        result = s.activate(GameEvent.CARDS_ADDED, {'target': target, 'amount': 3})
        assert result is False
        assert len(owner.hand) == 7
        assert s.times_left == 2

    def test_activate_cards_added_expires(self, mock_game, owner):
        s = season1.WuJianDao(owner, mock_game)
        target = mock_game.players[1]
        s.bound_target = target
        s.times_left = 1
        owner.hand = [Card('红', '数字', 1)]
        s.activate(GameEvent.CARDS_ADDED, {'target': target, 'amount': 3})
        assert s.bound_target is None
        assert s.is_consumed is True


# ---------- DuXin（读心）----------
class TestSeason1DuXin:
    def test_can_trigger_turn_start(self, mock_game, owner):
        s = season1.DuXin(owner, mock_game)
        assert s.can_trigger(GameEvent.TURN_START, {'player': owner})

    def test_activate_no_target(self, mock_game, owner):
        s = season1.DuXin(owner, mock_game)
        with patch.object(s, 'choose_target', return_value=None):
            result = s.activate(GameEvent.TURN_START, {'player': owner})
        assert result is False

    def test_activate_ai_views_hand(self, mock_game, owner):
        s = season1.DuXin(owner, mock_game)
        owner.is_human = False
        target = mock_game.players[1]
        target.hand = [Card('红', '数字', 1), Card('蓝', '数字', 2)]
        target.skills = []
        with patch.object(s, 'choose_target', return_value=target), \
             patch('random.choice', return_value='手牌'):
            result = s.activate(GameEvent.TURN_START, {'player': owner})
        assert result is True
        assert s.is_consumed is True

    def test_activate_ai_views_skills(self, mock_game, owner):
        s = season1.DuXin(owner, mock_game)
        owner.is_human = False
        target = mock_game.players[1]
        target.hand = []
        target.skills = [season1.ZhaoZai(target, mock_game)]
        with patch.object(s, 'choose_target', return_value=target), \
             patch('random.choice', return_value='技能'):
            result = s.activate(GameEvent.TURN_START, {'player': owner})
        assert result is True

    def test_activate_human_views_hand(self, mock_game, human_player):
        s = season1.DuXin(human_player, mock_game)
        human_player.is_human = True
        target = mock_game.players[1]
        target.hand = [Card('红', '数字', 1)]
        human_player.ui.input = MagicMock(return_value='1')  # 看手牌
        with patch.object(s, 'choose_target', return_value=target):
            result = s.activate(GameEvent.TURN_START, {'player': human_player})
        assert result is True


# ---------- DianRen（癫人）----------
class TestSeason1DianRen:
    def test_can_trigger_player_died_self(self, mock_game, owner):
        s = season1.DianRen(owner, mock_game)
        assert s.can_trigger(GameEvent.PLAYER_DIED, {'player': owner})

    def test_activate_inherits_dead_skills(self, mock_game, owner):
        s = season1.DianRen(owner, mock_game)
        dead_p = mock_game.players[1]
        dead_p.eliminated = True
        inherited = season1.ZhaoZai(dead_p, mock_game)
        dead_p.skills = [inherited]
        result = s.activate(GameEvent.PLAYER_DIED, {'player': owner})
        assert result is True
        assert inherited in owner.skills
        assert inherited.owner is owner
        assert s.is_consumed is True

    def test_activate_no_dead_skills(self, mock_game, owner):
        s = season1.DianRen(owner, mock_game)
        for p in mock_game.players:
            p.skills = []
            p.eliminated = False
        result = s.activate(GameEvent.PLAYER_DIED, {'player': owner})
        assert result is True
        assert s.is_consumed is True


# ---------- ZhaoZai（招灾）----------
class TestSeason1ZhaoZai:
    def test_can_trigger_turn_start(self, mock_game, owner):
        s = season1.ZhaoZai(owner, mock_game)
        assert s.can_trigger(GameEvent.TURN_START, {'player': owner})

    def test_urgency_high_with_weak_opponent(self, mock_game, owner):
        s = season1.ZhaoZai(owner, mock_game)
        mock_game.players[1].hand = [Card('红', '数字', 1)]
        assert s.evaluate_urgency(mock_game) == 90

    def test_urgency_default(self, mock_game, owner):
        s = season1.ZhaoZai(owner, mock_game)
        for p in mock_game.players[1:]:
            p.hand = [Card('红', '数字', i) for i in range(7)]
        assert s.evaluate_urgency(mock_game) == 40

    def test_activate_adds_5_to_random(self, mock_game, owner):
        s = season1.ZhaoZai(owner, mock_game)
        # 清空技能，避免触发 START_RANDOM 时的额外逻辑
        for p in mock_game.players:
            p.skills = []
        # 让随机选择固定返回 players[1]
        with patch('random.choice', return_value=mock_game.players[1]), \
             patch.object(mock_game, 'apply_add_cards') as mock_add:
            result = s.activate(GameEvent.TURN_START, {'player': owner})
        assert result is True
        assert s.is_consumed is True
        mock_add.assert_called_once_with(mock_game.players[1], 5)


# ---------- JingLei（惊雷）----------
class TestSeason1JingLei:
    def test_can_trigger_turn_start(self, mock_game, owner):
        s = season1.JingLei(owner, mock_game)
        assert s.can_trigger(GameEvent.TURN_START, {'player': owner})

    def test_urgency_high_risk_many_cards(self, mock_game, owner):
        s = season1.JingLei(owner, mock_game)
        owner.hand = [Card('红', '数字', i) for i in range(13)]
        assert s.evaluate_urgency(mock_game) == 10

    def test_urgency_low_when_few_cards(self, mock_game, owner):
        s = season1.JingLei(owner, mock_game)
        owner.hand = [Card('红', '数字', 1)]
        assert s.evaluate_urgency(mock_game) == 40

    def test_urgency_zero_default(self, mock_game, owner):
        s = season1.JingLei(owner, mock_game)
        owner.hand = [Card('红', '数字', i) for i in range(7)]
        assert s.evaluate_urgency(mock_game) == 0

    def test_activate_all_pass_no_penalty(self, mock_game, owner):
        """所有玩家点数 ≥5，不触发加牌。"""
        s = season1.JingLei(owner, mock_game)
        for p in mock_game.players:
            p.skills = []
        with patch('random.randint', return_value=6), \
             patch.object(mock_game, 'apply_add_cards') as mock_add:
            result = s.activate(GameEvent.TURN_START, {'player': owner})
        assert result is True
        assert s.is_consumed is True
        # 无人受罚
        mock_add.assert_not_called()

    def test_activate_all_fail_add_5(self, mock_game, owner):
        """所有玩家点数 <5，全部加 5。"""
        s = season1.JingLei(owner, mock_game)
        for p in mock_game.players:
            p.skills = []
        with patch('random.randint', return_value=1), \
             patch.object(mock_game, 'apply_add_cards') as mock_add:
            result = s.activate(GameEvent.TURN_START, {'player': owner})
        assert result is True
        # 每个玩家各加 5
        assert mock_add.call_count == len(mock_game.players)
        for call in mock_add.call_args_list:
            assert call[0][1] == 5


# ---------- NongYan（浓烟）----------
class TestSeason1NongYan:
    def test_can_trigger_game_start(self, mock_game, owner):
        s = season1.NongYan(owner, mock_game)
        assert s.can_trigger(GameEvent.GAME_START, {})

    def test_activate_hides_one_skill_from_each(self, mock_game, owner):
        s = season1.NongYan(owner, mock_game)
        # 给每个对手 2 个技能
        for p in mock_game.players[1:]:
            p.skills = [
                season1.ZhaoZai(p, mock_game),
                season1.JingLei(p, mock_game),
            ]
        result = s.activate(GameEvent.GAME_START, {})
        assert result is True
        assert s.is_consumed is True
        # 每个对手应有 1 个被删除
        for p in mock_game.players[1:]:
            deleted = [sk for sk in p.skills if sk.is_deleted]
            assert len(deleted) == 1

    def test_activate_skips_targets_with_no_skills(self, mock_game, owner):
        s = season1.NongYan(owner, mock_game)
        for p in mock_game.players[1:]:
            p.skills = []
        result = s.activate(GameEvent.GAME_START, {})
        assert result is True
        assert s.is_consumed is True

# ==================== Replay 补充测试 ====================
class TestReplayInteractiveChoose:
    @pytest.fixture(autouse=True)
    def temp_records_dir(self, tmp_path, monkeypatch):
        """把 RECORDS_DIR 指向临时目录，避免污染真实录像。"""
        import uno.replay as replay_module
        fake_dir = tmp_path / "records"
        fake_dir.mkdir()
        monkeypatch.setattr(replay_module, 'RECORDS_DIR', str(fake_dir))
        self.replay_module = replay_module
        self.records_dir = fake_dir

    def _make_record(self, name, players=None, timestamp=None, events=None):
        import json
        data = {
            "version": "v1.3.2",
            "timestamp": timestamp or name,
            "players": players or ['你', '电脑A'],
            "seasons": ['S1'],
            "initial_top_card": '红5',
            "events": events or []
        }
        path = self.records_dir / name
        path.write_text(json.dumps(data, ensure_ascii=False), encoding='utf-8')
        return path

    def test_list_records_empty(self):
        assert self.replay_module.list_records() == []

    def test_list_records_returns_sorted_latest_first(self):
        self._make_record('replay_20260101_120000.json')
        self._make_record('replay_20260102_120000.json')
        records = self.replay_module.list_records()
        assert len(records) == 2
        assert '20260102' in records[0]

    def test_interactive_choose_no_records_raises(self):
        ui = MagicMock()
        with pytest.raises(FileNotFoundError):
            self.replay_module.GameReplayer.interactive_choose(ui)

    def test_interactive_choose_empty_input_uses_latest(self):
        self._make_record('replay_20260101_120000.json', players=['A'])
        self._make_record('replay_20260102_120000.json', players=['B'])
        ui = MagicMock()
        ui.input = MagicMock(return_value='')
        replayer = self.replay_module.GameReplayer.interactive_choose(ui)
        assert replayer.data['players'] == ['B']

    def test_interactive_choose_specific_index(self):
        self._make_record('replay_20260101_120000.json', players=['A'])
        self._make_record('replay_20260102_120000.json', players=['B'])
        ui = MagicMock()
        ui.input = MagicMock(return_value='1')   # 第二个（旧的）
        replayer = self.replay_module.GameReplayer.interactive_choose(ui)
        assert replayer.data['players'] == ['A']

    def test_interactive_choose_invalid_index_falls_back_latest(self):
        self._make_record('replay_20260101_120000.json', players=['A'])
        ui = MagicMock()
        ui.input = MagicMock(return_value='999')
        replayer = self.replay_module.GameReplayer.interactive_choose(ui)
        assert replayer.data['players'] == ['A']

    def test_interactive_choose_non_numeric_falls_back_latest(self):
        self._make_record('replay_20260101_120000.json', players=['A'])
        ui = MagicMock()
        ui.input = MagicMock(return_value='abc')
        replayer = self.replay_module.GameReplayer.interactive_choose(ui)
        assert replayer.data['players'] == ['A']

    def test_interactive_choose_handles_corrupt_file(self):
        """有坏文件时应被过滤，用户仍能选到好文件。"""
        self._make_record('replay_20260101_120000.json', players=['A'])
        # 坏文件时间戳更"新"，排序时排在前面
        (self.records_dir / 'replay_20260102_120000.json').write_text(
            'not-json', encoding='utf-8'
        )
        ui = MagicMock()
        ui.input = MagicMock(return_value='')   # 回车选"最新"
        replayer = self.replay_module.GameReplayer.interactive_choose(ui)
        # 坏文件被过滤，实际拿到的是好文件
        assert replayer.data['players'] == ['A']

    def test_interactive_choose_all_corrupt_raises(self):
        """全部损坏时应抛出 FileNotFoundError。"""
        (self.records_dir / 'replay_20260101_120000.json').write_text(
            'not-json', encoding='utf-8'
        )
        (self.records_dir / 'replay_20260102_120000.json').write_text(
            '', encoding='utf-8'
        )
        ui = MagicMock()
        with pytest.raises(FileNotFoundError):
            self.replay_module.GameReplayer.interactive_choose(ui)

    def test_interactive_choose_filters_display(self):
        """列表中只显示可读文件，坏文件不出现。"""
        self._make_record('replay_20260101_120000.json', players=['A'])
        (self.records_dir / 'replay_20260102_120000.json').write_text(
            'not-json', encoding='utf-8'
        )
        ui = MagicMock()
        ui.input = MagicMock(return_value='')
        self.replay_module.GameReplayer.interactive_choose(ui)
        # 收集所有 ui.show 的输出
        output = '\n'.join(str(call) for call in ui.show.call_args_list)
        # 应该只有 1 个可选项（索引 0）
        assert '  0:' in output
        assert '  1:' not in output


class TestReplayDisplay:
    """测试 GameReplayer._display 各个事件分支。"""
    def _make_replayer(self, tmp_path, events):
        import json
        path = tmp_path / "rec.json"
        data = {
            "version": "v1.3.2",
            "players": ['你', '电脑A'],
            "seasons": ['S1'],
            "initial_top_card": '红5',
            "events": events
        }
        path.write_text(json.dumps(data, ensure_ascii=False), encoding='utf-8')
        ui = MagicMock()
        return GameReplayer(str(path), ui), ui

    def test_display_game_start(self, tmp_path):
        r, ui = self._make_replayer(tmp_path, [
            {'type': 'game_start', 'top_card': '红5'}
        ])
        r.next_event()
        assert ui.show.called

    def test_display_turn_start(self, tmp_path):
        r, ui = self._make_replayer(tmp_path, [
            {'type': 'turn_start', 'player': '你', 'hand_size': 7}
        ])
        r.next_event()
        assert ui.show.called

    def test_display_turn_start_without_hand_size(self, tmp_path):
        r, ui = self._make_replayer(tmp_path, [
            {'type': 'turn_start', 'player': '你'}
        ])
        r.next_event()
        assert ui.show.called

    def test_display_draw_card(self, tmp_path):
        r, ui = self._make_replayer(tmp_path, [
            {'type': 'draw_card', 'player': '你', 'card': '红5'}
        ])
        r.next_event()
        assert ui.show.called

    def test_display_play_card(self, tmp_path):
        r, ui = self._make_replayer(tmp_path, [
            {'type': 'play_card', 'player': '你', 'card': '红5'}
        ])
        r.next_event()
        assert ui.show.called

    def test_display_uno_call(self, tmp_path):
        r, ui = self._make_replayer(tmp_path, [
            {'type': 'uno_call', 'player': '你'}
        ])
        r.next_event()
        assert ui.show.called

    def test_display_skill_use(self, tmp_path):
        r, ui = self._make_replayer(tmp_path, [
            {'type': 'skill_use', 'player': '你', 'skill_name': '破万法'}
        ])
        r.next_event()
        assert ui.show.called

    def test_display_add_cards(self, tmp_path):
        r, ui = self._make_replayer(tmp_path, [
            {'type': 'add_cards', 'target': '电脑A', 'amount': 3}
        ])
        r.next_event()
        assert ui.show.called

    def test_display_player_eliminated(self, tmp_path):
        r, ui = self._make_replayer(tmp_path, [
            {'type': 'player_eliminated', 'player': '电脑A'}
        ])
        r.next_event()
        assert ui.show.called

    def test_display_game_end(self, tmp_path):
        r, ui = self._make_replayer(tmp_path, [
            {'type': 'game_end', 'winner': '你'}
        ])
        r.next_event()
        assert ui.show.called

    def test_display_unknown_event(self, tmp_path):
        r, ui = self._make_replayer(tmp_path, [{'type': 'unknown_xyz'}])
        r.next_event()
        # 应打印"未知事件"
        assert any('未知事件' in str(call) for call in ui.show.call_args_list)

    def test_replay_all_stops_at_end(self, tmp_path):
        r, ui = self._make_replayer(tmp_path, [
            {'type': 'game_end', 'winner': '你'}
        ])
        with patch('builtins.input', return_value=''):
            r.replay_all()
        assert any('回放结束' in str(call) for call in ui.show.call_args_list)

    def test_replay_all_multiple_events(self, tmp_path):
        r, ui = self._make_replayer(tmp_path, [
            {'type': 'turn_start', 'player': '你', 'hand_size': 7},
            {'type': 'play_card', 'player': '你', 'card': '红5'},
            {'type': 'game_end', 'winner': '你'},
        ])
        with patch('builtins.input', return_value=''):
            r.replay_all()
        # 至少调用了 3 次（3 个事件）+ 1 次"回放结束"
        assert ui.show.call_count >= 4

    def test_next_event_returns_none_at_end(self, tmp_path):
        r, _ = self._make_replayer(tmp_path, [])
        assert r.next_event() is None

    def test_next_event_returns_event_and_advances(self, tmp_path):
        r, _ = self._make_replayer(tmp_path, [
            {'type': 'game_end', 'winner': '你'}
        ])
        ev1 = r.next_event()
        assert ev1 is not None
        ev2 = r.next_event()
        assert ev2 is None


class TestReplayRecorderSave:
    """补 GameRecorder.save 到自定义目录的分支。"""

    def test_recorder_save_creates_directory(self, tmp_path, monkeypatch):
        import uno.replay as replay_module
        nested = tmp_path / "a" / "b" / "records"
        monkeypatch.setattr(replay_module, 'RECORDS_DIR', str(nested))
        recorder = GameRecorder()
        recorder.players = ['你']
        recorder.seasons = ['S1']
        recorder.initial_top_card = '红5'
        path = recorder.save()
        assert os.path.exists(path)
        # 文件所在目录被创建
        assert os.path.isdir(str(nested))
        # 清理
        os.remove(path)
