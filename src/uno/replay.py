import json
import os
import glob
from datetime import datetime
from typing import List

RECORDS_DIR = os.path.join(os.path.dirname(__file__), 'records')

class GameRecorder:
    def __init__(self):
        self.events: List[dict] = []
        self.players = []
        self.seasons = []
        self.initial_top_card = None

    def record(self, event_type: str, **kwargs):
        self.events.append({"type": event_type, **kwargs})

    def save(self):
        """自动保存到 records 文件夹，文件名带时间戳"""
        os.makedirs(RECORDS_DIR, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"replay_{timestamp}.json"
        filepath = os.path.join(RECORDS_DIR, filename)
        data = {
            "version": "v0.7.0",
            "timestamp": timestamp,
            "players": self.players,
            "seasons": self.seasons,
            "initial_top_card": self.initial_top_card,
            "events": self.events
        }
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return filepath


def list_records() -> List[str]:
    """返回所有录像文件的完整路径列表（按时间倒序）"""
    if not os.path.exists(RECORDS_DIR):
        return []
    files = glob.glob(os.path.join(RECORDS_DIR, "replay_*.json"))
    files.sort(reverse=True)  # 最新的在前
    return files


class GameReplayer:
    def __init__(self, filepath: str, ui):
        self.ui = ui
        self.filepath = filepath
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"录像文件 {filepath} 不存在。")
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            if not content:
                raise ValueError("录像文件为空。")
            self.data = json.loads(content)
        self.event_index = 0

    @classmethod
    def interactive_choose(cls, ui):
        """让用户从列表中选择一个录像，返回 GameReplayer 实例"""
        records = list_records()
        if not records:
            raise FileNotFoundError("没有找到任何录像文件。")
        ui.show("可用的录像文件：")
        for i, path in enumerate(records):
            # 提取文件名和时间信息
            fname = os.path.basename(path)
            # 尝试读取玩家信息
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                players = ', '.join(data.get('players', []))
                ts = data.get('timestamp', fname)
            except:
                players = '未知'
                ts = fname
            ui.show(f"  {i}: {ts}  玩家: {players}")
        choice = ui.input("请输入序号（直接回车选择最新）: ").strip()
        if choice == '':
            path = records[0]
        else:
            try:
                idx = int(choice)
                path = records[idx]
            except (ValueError, IndexError):
                ui.show("无效选择，使用最新录像。")
                path = records[0]
        return cls(path, ui)

    def next_event(self):
        if self.event_index < len(self.data["events"]):
            ev = self.data["events"][self.event_index]
            self.event_index += 1
            self._display(ev)
            return ev
        return None

    def _display(self, ev: dict):
        t = ev["type"]
        if t == "game_start":
            self.ui.show(f"起始牌: {ev.get('top_card', '?')}")
        elif t == "turn_start":
            self.ui.show(f"\n===== {ev['player']} 的回合 =====")
            if 'hand_size' in ev:
                self.ui.show(f"手牌数: {ev['hand_size']}")
        elif t == "draw_card":
            self.ui.show(f"{ev['player']} 抽了一张牌: {ev.get('card', '?')}")
        elif t == "play_card":
            self.ui.show(f"{ev['player']} 打出: {ev['card']}")
        elif t == "uno_call":
            self.ui.show(f"🔔 {ev['player']} 喊了 UNO！")
        elif t == "skill_use":
            self.ui.show(f"{ev['player']} 使用技能: {ev['skill_name']}")
        elif t == "add_cards":
            self.ui.show(f"{ev['target']} 抽了 {ev['amount']} 张牌")
        elif t == "player_eliminated":
            self.ui.show(f"[淘汰] {ev['player']} 被淘汰")
        elif t == "game_end":
            self.ui.show(f"游戏结束，胜者: {ev.get('winner', '?')}")
        else:
            self.ui.show(f"未知事件: {t}")

    def replay_all(self):
        while True:
            ev = self.next_event()
            if ev is None:
                self.ui.show("回放结束。")
                break
            input("按回车继续...")