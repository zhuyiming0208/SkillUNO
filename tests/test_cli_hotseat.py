"""CLI 热座模式入口测试。"""
import os
import sys
from unittest.mock import patch

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)
SRC_DIR = os.path.join(PROJECT_ROOT, "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from uno.main import _ask_hotseat_count, _collect_hotseat_players


# ============ _ask_hotseat_count ============

def test_count_valid_direct():
    with patch("builtins.input", side_effect=["3"]):
        assert _ask_hotseat_count() == 3


def test_count_rejects_non_number_then_accepts():
    with patch("builtins.input", side_effect=["abc", "2"]):
        assert _ask_hotseat_count() == 2


def test_count_rejects_out_of_range_then_accepts():
    with patch("builtins.input", side_effect=["1", "5", "4"]):
        assert _ask_hotseat_count() == 4


# ============ _collect_hotseat_players ============

def test_players_at_resolves_to_initial():
    """@ 解析为初始名字。"""
    with patch("builtins.input", side_effect=["@", "Bob"]):
        players = _collect_hotseat_players("Alice", 2)
    assert players == ["Alice", "Bob"]


def test_players_at_after_first_use_becomes_plain_name():
    """第一次 @ 用完后，后续 @ 会重名报错重问。"""
    with patch("builtins.input", side_effect=["@", "@", "Bob"]):
        players = _collect_hotseat_players("Alice", 2)
    assert players == ["Alice", "Bob"]


def test_players_empty_name_rejected():
    """空名被拒后重问。"""
    with patch("builtins.input", side_effect=["", "Bob", "Carol"]):
        players = _collect_hotseat_players("Alice", 2)
    assert players == ["Bob", "Carol"]


def test_players_duplicate_name_rejected():
    """重复名字报错重问。"""
    with patch("builtins.input", side_effect=["Bob", "Bob", "Carol"]):
        players = _collect_hotseat_players("Alice", 2)
    assert players == ["Bob", "Carol"]


def test_players_three_players():
    with patch("builtins.input", side_effect=["@", "Bob", "Carol"]):
        players = _collect_hotseat_players("Alice", 3)
    assert players == ["Alice", "Bob", "Carol"]


# ============ main() 集成测试 ============

def test_hotseat_main_passes_players_kwarg():
    """热座模式下 UNOGame 收到 players 参数，不带 ai_strategy。"""
    from uno.main import main
    # 输入：名字 / 模式=2 / 人数=2 / 玩家1=@ / 玩家2=Bob
    #       / 赛季默认 / debug=0 / rich=n / 录制=n（+2 兜底）
    inputs = ["Alice", "2", "2", "@", "Bob", "", "0", "n", "n", "n", "n"]
    with patch("builtins.input", side_effect=inputs), \
         patch("uno.main.UNOGame") as mock_game, \
         patch("uno.main.show_record") as mock_show:
        main()
    mock_show.assert_not_called()
    kw = mock_game.call_args.kwargs
    assert kw.get("players") == ["Alice", "Bob"]
    assert "ai_strategy" not in kw


def test_single_main_uses_ai_strategy():
    """单人模式下 UNOGame 收到 ai_strategy，不带 players。"""
    from uno.main import main
    # 输入：名字 / 模式=1 / 赛季默认 / AI难度=2 / debug=0 / rich=n / 录制=n
    inputs = ["Alice", "1", "", "2", "0", "n", "n", "n", "n"]
    with patch("builtins.input", side_effect=inputs), \
         patch("uno.main.UNOGame") as mock_game, \
         patch("uno.main.show_record") as mock_show, \
         patch("uno.main._make_ai") as mock_make_ai:
        mock_make_ai.return_value = "FAKE_AI"
        main()
    mock_show.assert_called_once_with("Alice")
    kw = mock_game.call_args.kwargs
    assert kw.get("ai_strategy") == "FAKE_AI"
    assert "players" not in kw
