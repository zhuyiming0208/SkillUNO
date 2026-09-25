import os
import json
import base64

ARCHIVE_FILE = os.path.join(os.path.dirname(__file__), 'archive.txt')

def load_archive():
    if not os.path.exists(ARCHIVE_FILE):
        return {}
    try:
        with open(ARCHIVE_FILE, 'r', encoding='utf-8') as f:
            encoded = f.read()
            if not encoded:
                return {}
            decoded = base64.b64decode(encoded).decode('utf-8')
            data = json.loads(decoded)
            # 兼容旧存档：确保每个玩家都有 achievements 列表
            for name in data:
                if 'achievements' not in data[name]:
                    data[name]['achievements'] = []
            return data
    except Exception as e:
        print(f"[存档] 读取失败，使用空存档。错误：{e}")
        return {}

def save_archive(data):
    try:
        json_str = json.dumps(data, ensure_ascii=False, indent=2)
        encoded = base64.b64encode(json_str.encode('utf-8')).decode('ascii')
        with open(ARCHIVE_FILE, 'w', encoding='ascii') as f:
            f.write(encoded)
    except Exception as e:
        print(f"[存档] 保存失败。错误：{e}")

def update_record(name: str, won: bool, achievements: list = None):
    data = load_archive()
    if name not in data:
        data[name] = {'wins': 0, 'losses': 0, 'achievements': []}
    if won:
        data[name]['wins'] += 1
    else:
        data[name]['losses'] += 1
    if achievements:
        existing = set(data[name].get('achievements', []))
        for ach in achievements:
            existing.add(ach)
        data[name]['achievements'] = list(existing)
    save_archive(data)
    print(f"[存档] {name} 的战绩已更新。")

def show_record(name: str):
    data = load_archive()
    if name in data:
        wins = data[name]['wins']
        losses = data[name]['losses']
        total = wins + losses
        rate = f"{wins/total*100:.7f}%" if total > 0 else "N/A"
        print(f"{name} 战绩：{wins}胜 {losses}负，胜率 {rate}")
        ach = data[name].get('achievements', [])
        if ach:
            print(f"  成就：{', '.join(ach)}")
    else:
        print(f"{name} 尚无战绩记录。")