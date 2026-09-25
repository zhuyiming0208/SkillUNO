import os
import json
import base64
from typing import List, Dict, Optional

PRESET_FILE = os.path.join(os.path.dirname(__file__), 'presets.json')

# print(PRESET_FILE)

def load_presets() -> List[Dict]:
    """读取所有房间预设，返回列表"""
    if not os.path.exists(PRESET_FILE):
        return []
    try:
        with open(PRESET_FILE, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            if not content:
                return []
            # 支持 Base64 加密的 JSON 或普通 JSON
            try:
                decoded = base64.b64decode(content).decode('utf-8')
                data = json.loads(decoded)
            except Exception:
                data = json.loads(content)
            return data if isinstance(data, list) else []
    except Exception as e:
        print(f"[预设] 读取失败：{e}")
        return []

def save_presets(presets: List[Dict]):
    """保存预设列表到文件（Base64 编码）"""
    try:
        json_str = json.dumps(presets, ensure_ascii=False, indent=2)
        encoded = base64.b64encode(json_str.encode('utf-8')).decode('ascii')
        with open(PRESET_FILE, 'w', encoding='ascii') as f:
            f.write(encoded)
    except Exception as e:
        print(f"[预设] 保存失败：{e}")

def add_preset(name: str, hand_limit: int, initial_hand_size: int, initial_skill_count: int) -> bool:
    """添加或更新一个预设，返回是否成功"""
    presets = load_presets()
    # 移除同名预设
    presets = [p for p in presets if p.get('name') != name]
    presets.append({
        'name': name,
        'hand_limit': hand_limit,
        'initial_hand_size': initial_hand_size,
        'initial_skill_count': initial_skill_count
    })
    save_presets(presets)
    return True

def get_preset(name: str) -> Optional[Dict]:
    """根据名称获取预设"""
    for p in load_presets():
        if p.get('name') == name:
            return p
    return None