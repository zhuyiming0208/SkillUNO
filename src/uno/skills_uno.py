import importlib
import os
from typing import List, Type, Dict, Any

class SkillLoader:
    SEASON_MODULES = {
        "S1": "uno.season1",
        "S2": "uno.season2",
        "S3": "uno.season3",
        "S4": "uno.season4",
    }

    @classmethod
    def load_skills(cls, enabled_seasons: List[str], game, mods_dir=None, enabled_path=None):
        # 路径解析（阶段六：enabled.json 支持）
        from uno.paths import find_mods_dir
        from uno.enabled import load_disabled
        if mods_dir is None:
            mods_dir = str(find_mods_dir())
        if enabled_path is None:
            enabled_path = os.path.join(mods_dir, "enabled.json")
        _disabled = load_disabled(enabled_path)

        all_classes = []
        skill_glossary = {}
        mod_achievements = []

        candidates = []

        # 官方赛季
        for season_id in enabled_seasons:
            module_name = cls.SEASON_MODULES.get(season_id)
            if not module_name:
                continue
            try:
                module = importlib.import_module(module_name)
                info = cls._extract_module_info(module, module_name, season_id)
                candidates.append(info)
            except ImportError as e:
                print(f"错误：无法导入赛季模块 {module_name} - {e}")

        # Mods
        # mods_dir 已由参数决定（见上方路径解析）
        if os.path.exists(mods_dir):
            for filename in sorted(os.listdir(mods_dir)):
                if filename.endswith('.py') and not filename.startswith('_'):
                    mod_name = filename[:-3]
                    full_module_name = f"mods.{mod_name}"
                    try:
                        module = importlib.import_module(full_module_name)
                        mod_id = getattr(module, 'SEASON_ID', None)
                        if mod_id in enabled_seasons and mod_id not in _disabled:
                            info = cls._extract_module_info(module, full_module_name, mod_id)
                            candidates.append(info)
                    except ImportError as e:
                        print(f"警告：无法导入 Mod {mod_name} - {e}")

        # 依赖检查
        valid_candidates = []
        for cand in candidates:
            rely = cand.get('rely_on')
            if rely and isinstance(rely, tuple) and len(rely) >= 1:
                dep_id = rely[0]
                if dep_id not in enabled_seasons:
                    explanation = rely[1] if len(rely) > 1 else "未提供说明"
                    print(f"警告：赛季/Mod {cand['season_name']} ({cand['season_id']}) 依赖 {dep_id}，但该赛季未启用，已跳过。说明：{explanation}")
                    continue
            valid_candidates.append(cand)

        # 排斥检查
        id_to_candidate = {c['season_id']: c for c in valid_candidates}
        failed_ids = set()
        reject_pairs = []
        for cand in valid_candidates:
            reject_dict = cand.get('reject')
            if not reject_dict or not isinstance(reject_dict, dict):
                continue
            for target_id, reason in reject_dict.items():
                if target_id in id_to_candidate:
                    reject_pairs.append((cand['season_id'], target_id, reason))
        for source_id, target_id, reason in reject_pairs:
            failed_ids.add(source_id)
            failed_ids.add(target_id)
            source_name = id_to_candidate[source_id]['season_name']
            target_name = id_to_candidate[target_id]['season_name']
            print(f"排斥冲突：{source_name} ({source_id}) 排斥 {target_name} ({target_id})，原因：{reason}。")
        if failed_ids:
            print("因此，以下赛季/Mod 无法加载：", ', '.join(failed_ids))

        # 容忍检查
        current_valid = [c for c in valid_candidates if c['season_id'] not in failed_ids]
        tolerate_failed_ids = set()
        for cand in current_valid:
            tolerate = cand.get('only_tolerate')
            if not tolerate or not isinstance(tolerate, (tuple, list)):
                continue
            tolerate_set = set(tolerate)
            for other in current_valid:
                if other['season_id'] == cand['season_id']:
                    continue
                if other['season_id'] not in tolerate_set:
                    tolerate_failed_ids.add(other['season_id'])
                    print(f"容忍冲突：{cand['season_name']} ({cand['season_id']}) 只允许与 {tolerate_set} 共同导入，因此 {other['season_name']} ({other['season_id']}) 导入失败。")
        failed_ids.update(tolerate_failed_ids)
        if tolerate_failed_ids:
            print("因容忍规则，以下赛季/Mod 无法加载：", ', '.join(tolerate_failed_ids))

        final_candidates = [c for c in valid_candidates if c['season_id'] not in failed_ids]

        for cand in final_candidates:
            for skill_cls in cand['skill_classes']:
                all_classes.append(skill_cls)
                temp = skill_cls(None, None)
                skill_glossary[temp.name] = temp.description
            # 收集成就
            achievements = cand.get('achievements', [])
            mod_achievements.extend(achievements)
            print(f"已加载赛季/Mod {cand['season_name']} ({cand['season_id']})，共 {len(cand['skill_classes'])} 个技能")

        return [cls(owner=None, game=game) for cls in all_classes], skill_glossary, mod_achievements

    @classmethod
    def _extract_module_info(cls, module, module_name, season_id):
        return {
            'module_name': module_name,
            'season_id': season_id,
            'season_name': getattr(module, 'SEASON_NAME', season_id),
            'skill_classes': getattr(module, 'SKILL_CLASSES', []),
            'rely_on': getattr(module, 'RELY_ON', None),
            'reject': getattr(module, 'REJECT', None),
            'only_tolerate': getattr(module, 'ONLY_TOLERATE', None),
            'achievements': getattr(module, 'ACHIEVEMENTS', []),
        }