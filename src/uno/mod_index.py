"""模组索引与元数据加载。

供 CLI 模组商店使用，读取 `mods/mod_idx.json` 与各模组元数据 JSON。
不涉及实际游戏加载逻辑（那是 `skills_uno.py` 的职责）。
"""
import os
import json
import copy
from typing import List, Dict, Optional

# 按要求导入，方便未来在元数据校验阶段引用技能基类
from uno.core import Skill, SkillType  # noqa: F401


# 单个模组元数据的必填字段
REQUIRED_FIELDS = [
    "ID",
    "name",
    "description",
    "author",
    "repo",
    "version",
    "micover",
    "lacover",
    "skills",
]

# 官方内建模组（硬编码）
OFFICIAL_MODS = [
    {"id": "S1", "name": "经典赛季", "skills": 16, "builtin": True},
    {"id": "S2", "name": "被动觉醒", "skills": 8, "builtin": True},
    {"id": "S4", "name": "补丁赛季", "skills": 8, "builtin": True},
]

# 索引文件缺省值
_EMPTY_INDEX = {
    "handpicked": [],
    "other": [],
    "version": "0.0.0",
    "update_time": "",
}


class ModIndex:
    """模组索引读取与查询。"""

    def __init__(self, mods_dir: str = "mods"):
        self.mods_dir = mods_dir

    # ---------- 内部 ----------
    def _path(self, filename: str) -> str:
        return os.path.join(self.mods_dir, filename)

    # ---------- 读取索引 ----------
    def load_index(self) -> Dict:
        """读取 `mod_idx.json`，失败时返回带缺省结构的空索引。"""
        path = self._path("mod_idx.json")
        try:
            # utf-8-sig 兼容带与不带 BOM 的文件
            with open(path, "r", encoding="utf-8-sig") as f:
                data = json.load(f)
        except FileNotFoundError:
            print(f"警告：找不到索引文件 {path}")
            return dict(_EMPTY_INDEX)
        except json.JSONDecodeError as e:
            print(f"警告：索引文件 {path} 格式错误：{e}")
            return dict(_EMPTY_INDEX)

        if not isinstance(data, dict):
            print(f"警告：索引文件 {path} 顶层不是对象，已忽略")
            return dict(_EMPTY_INDEX)

        # 补全缺省键
        for key, default in _EMPTY_INDEX.items():
            data.setdefault(key, default if not isinstance(default, list) else [])
        return data

    # ---------- 读取单个模组 ----------
    def load_mod(self, filename: str) -> Optional[Dict]:
        """读取单个模组元数据，校验必填字段。失败返回 None。"""
        path = self._path(filename)
        try:
            with open(path, "r", encoding="utf-8-sig") as f:
                data = json.load(f)
        except FileNotFoundError:
            print(f"警告：找不到模组文件 {path}")
            return None
        except json.JSONDecodeError as e:
            print(f"警告：模组文件 {filename} 格式错误：{e}")
            return None

        if not isinstance(data, dict):
            print(f"警告：模组文件 {filename} 顶层不是对象，已跳过")
            return None

        missing = [k for k in REQUIRED_FIELDS if k not in data]
        if missing:
            print(f"警告：模组 {filename} 缺少必填字段：{missing}，已跳过")
            return None

        return data

    # ---------- 列表 ----------
    def get_handpicked(self) -> List[Dict]:
        """获取精选模组列表。"""
        index = self.load_index()
        result = []
        for filename in index.get("handpicked", []):
            mod = self.load_mod(filename)
            if mod is not None:
                result.append(mod)
        return result

    def get_all(self) -> List[Dict]:
        """获取全部模组列表（handpicked + other）。"""
        index = self.load_index()
        filenames = list(index.get("handpicked", [])) + list(index.get("other", []))
        result = []
        for filename in filenames:
            mod = self.load_mod(filename)
            if mod is not None:
                result.append(mod)
        return result

    # ---------- 搜索 ----------
    def search(self, keyword: str) -> List[Dict]:
        """在 ID / 名称 / 作者中模糊匹配关键词。"""
        keyword = (keyword or "").strip().lower()
        if not keyword:
            return []
        result = []
        for mod in self.get_all():
            haystacks = [
                str(mod.get("ID", "")).lower(),
                str(mod.get("name", "")).lower(),
                str(mod.get("author", "")).lower(),
            ]
            if any(keyword in h for h in haystacks):
                result.append(mod)
        return result

    # ---------- 官方模组 ----------
    def get_official(self) -> List[Dict]:
        """获取官方内建模组列表（深拷贝，防止外部污染常量）。"""
        return copy.deepcopy(OFFICIAL_MODS)
