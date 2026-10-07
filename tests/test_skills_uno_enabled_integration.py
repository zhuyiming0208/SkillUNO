"""skills_uno 与 enabled 集成测试。"""
import os
import sys
import json
from unittest.mock import MagicMock

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)
SRC_DIR = os.path.join(PROJECT_ROOT, "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from uno.skills_uno import SkillLoader


def _mock_game():
    g = MagicMock()
    g.debug = False
    return g


def test_load_old_signature_still_works():
    """旧签名 load_skills([...], mock_game) 仍工作。"""
    game = _mock_game()
    result = SkillLoader.load_skills(['S1'], game)
    assert isinstance(result, tuple)
    assert len(result) == 3


def test_load_with_none_enabled_path_uses_default():
    game = _mock_game()
    result = SkillLoader.load_skills(['S1'], game, enabled_path=None)
    assert isinstance(result, tuple)


def test_load_with_explicit_enabled_path(tmp_path):
    p = tmp_path / "enabled.json"
    p.write_text(json.dumps({"version": "1.0.0", "disabled": []}), encoding="utf-8")
    game = _mock_game()
    result = SkillLoader.load_skills(['S1'], game, enabled_path=str(p))
    assert isinstance(result, tuple)


def test_unogame_default_enabled_path():
    from uno.core import UNOGame
    g = UNOGame(debug=False, use_rich_ui=False)
    assert g is not None
