"""导出所有技能到 JSON，供网页技能图鉴使用。

数据源：
- src/uno/season1.py ~ season4.py（官方赛季）
- mods/*.py（本地已安装的 Mod，不存在则跳过）

用法：
    PYTHONPATH=src python tools/export_skills.py

输出：
    web/skills/skills.json
"""
import importlib
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
MODS = ROOT / "mods"
OUT = ROOT / "web" / "skills" / "skills.json"

SEASONS = ["season1", "season2", "season3", "season4"]


def _skill_type_name(skill_type):
    """SkillType 枚举 → 中文字符串。"""
    mapping = {
        "ACTIVE": "主动",
        "PASSIVE": "被动",
        "DEATH": "亡语",
        "HYBRID": "混合",
    }
    name = getattr(skill_type, "name", str(skill_type))
    return mapping.get(name, name)


def _extract_season(module_name, display_id, display_name):
    """从单个 season 模块提取技能列表。"""
    try:
        module = importlib.import_module(f"uno.{module_name}")
    except ImportError as e:
        print(f"[错误] 无法导入官方赛季 {module_name}: {e}", file=sys.stderr)
        print("       这通常意味着环境依赖缺失（如 rich）。", file=sys.stderr)
        raise

    season_id = getattr(module, "SEASON_ID", display_id)
    season_name = getattr(module, "SEASON_NAME", display_name)
    classes = getattr(module, "SKILL_CLASSES", [])

    result = []
    for cls in classes:
        try:
            inst = cls(None, None)
        except Exception as e:
            print(f"[跳过] {season_id}/{cls.__name__}: {e}", file=sys.stderr)
            continue
        result.append({
            "name": inst.name,
            "type": _skill_type_name(inst.type),
            "description": inst.description or "",
            "help": inst.help_text or "",
            "season_id": season_id,
            "season_name": season_name,
            "class_name": cls.__name__,
        })
    return result


def _extract_local_mods():
    """扫描 mods/*.py，提取 mod 的 SEASON_ID / SKILL_CLASSES。"""
    if not MODS.is_dir():
        return []

    result = []
    for py_file in sorted(MODS.glob("*.py")):
        if py_file.name == "__init__.py" or py_file.name.startswith("_"):
            continue
        mod_name = py_file.stem
        try:
            module = importlib.import_module(f"mods.{mod_name}")
        except ImportError as e:
            print(f"[警告] mod {mod_name} 导入失败（不影响官方赛季）: {e}",
                  file=sys.stderr)
            continue

        season_id = getattr(module, "SEASON_ID", mod_name.upper())
        season_name = getattr(module, "SEASON_NAME", mod_name)
        classes = getattr(module, "SKILL_CLASSES", [])

        for cls in classes:
            try:
                inst = cls(None, None)
            except Exception as e:
                print(f"[跳过] {season_id}/{cls.__name__}: {e}", file=sys.stderr)
                continue
            result.append({
                "name": inst.name,
                "type": _skill_type_name(inst.type),
                "description": inst.description or "",
                "help": inst.help_text or "",
                "season_id": season_id,
                "season_name": season_name,
                "class_name": cls.__name__,
                "is_mod": True,
            })
    return result


def main():
    sys.path.insert(0, str(SRC))
    sys.path.insert(0, str(ROOT))  # 让 mods.* 可导入

    all_skills = []
    for i, season_mod in enumerate(SEASONS, 1):
        # fallback：从文件名推断 S1/S2/S3/S4
        display_id = f"S{i}"
        display_name = display_id
        skills = _extract_season(season_mod, display_id, display_name)
        all_skills.extend(skills)
        print(f"  {display_id}: {len(skills)} 个技能")

    mod_skills = _extract_local_mods()
    all_skills.extend(mod_skills)
    if mod_skills:
        print(f"  Mods: {len(mod_skills)} 个技能")

    if len(all_skills) == 0:
        print("[错误] 导出 0 个技能，环境依赖可能缺失", file=sys.stderr)
        sys.exit(1)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "version": "1.0.0",
        "total": len(all_skills),
        "skills": all_skills,
    }
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    print(f"\n[OK] 已导出 {len(all_skills)} 个技能到 {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
