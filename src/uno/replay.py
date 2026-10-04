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
            try:
                self.data = json.loads(content)
            except json.JSONDecodeError as e:
                raise ValueError(f"录像文件内容不是有效的 JSON：{e}")
        self.event_index = 0

    @classmethod
    def interactive_choose(cls, ui):
        """让用户从列表中选择一个录像，返回 GameReplayer 实例。
        打不开的录像会被自动过滤，不会出现在列表中。
        """
        all_records = list_records()
        if not all_records:
            raise FileNotFoundError("没有找到任何录像文件。")

        # 预读每个录像，过滤掉损坏的文件
        valid_records = []  # [(path, data), ...]
        for path in all_records:
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                if not content:
                    continue
                data = json.loads(content)
                valid_records.append((path, data))
            except (json.JSONDecodeError, OSError, ValueError):
                continue

        if not valid_records:
            raise FileNotFoundError("录像文件均不可读。")

        ui.show("可用的录像文件：")
        for i, (path, data) in enumerate(valid_records):
            fname = os.path.basename(path)
            players = ', '.join(data.get('players', [])) or '未知'
            ts = data.get('timestamp', fname)
            ui.show(f"  {i}: {ts}  玩家: {players}")

        choice = ui.input("请输入序号（直接回车选择最新）: ").strip()
        if choice == '':
            path = valid_records[0][0]
        else:
            try:
                idx = int(choice)
                path = valid_records[idx][0]
            except (ValueError, IndexError):
                ui.show("无效选择，使用最新录像。")
                path = valid_records[0][0]
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

