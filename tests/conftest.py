"""pytest 全局配置：固定随机种子，保证测试稳定。"""
import random
import pytest


@pytest.fixture(autouse=True)
def _fixed_random_seed():
    """每个测试前重置随机种子，让覆盖率稳定。"""
    random.seed(42)
    yield
