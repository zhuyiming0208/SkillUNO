"""商店上下文：封装所有路径。"""
from dataclasses import dataclass

from uno.mod_index import ModIndex


@dataclass
class StoreContext:
    mod_index: ModIndex
    history_path: str
    enabled_path: str
    collections_path: str
