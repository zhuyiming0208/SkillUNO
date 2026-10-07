"""测试 paths.find_mods_dir。"""
import os
import sys

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)
SRC_DIR = os.path.join(PROJECT_ROOT, "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from uno.paths import find_mods_dir


def test_finds_mods():
    p = find_mods_dir()
    assert p.is_dir()
    assert p.name == "mods"


def test_from_subdir():
    # 无论从哪儿调用，都应能找到
    assert find_mods_dir().name == "mods"
