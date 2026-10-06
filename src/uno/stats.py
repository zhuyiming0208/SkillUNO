"""
统计面板：从存档与回放中聚合数据，用 rich 展示。

数据来源：
- archive.txt：玩家胜率、成就
- records/*.json：技能使用次数、牌型频率、回合数
"""
import os
import json
import glob
from collections import Counter
from typing import Dict, List, Optional, Any

from .archive import load_archive


def _records_dir() -> str:
    """延迟导入，避免循环依赖。"""
    from .replay import RECORDS_DIR
    return RECORDS_DIR


def _try_rich():
    """尝试导入 rich，失败返回 None。"""
    try:
        from rich.console import Console
        from rich.table import Table
        from rich.panel import Panel
        return {
            'Console': Console,
            'Table': Table,
            'Panel': Panel,
        }
    except ImportError:
        return None


class StatsCollector:
    """从 archive.txt 和 records/ 收集统计数据。"""

    def __init__(self, records_dir: Optional[str] = None):
        self.records_dir = records_dir if records_dir is not None else _records_dir()

    # ---------- 玩家 ----------
    def collect_player_stats(self) -> List[Dict[str, Any]]:
        """玩家胜率排行。"""
        archive = load_archive()
        players = []
        for name, data in archive.items():
            wins = data.get('wins', 0)
            losses = data.get('losses', 0)
            total = wins + losses
            rate = (wins / total * 100) if total > 0 else 0.0
            ach = data.get('achievements', [])
            players.append({
                'name': name,
                'wins': wins,
                'losses': losses,
                'total': total,
                'rate': rate,
                'achievements': ach,
            })
        # 按胜率降序，胜率相同按总场次降序
        players.sort(key=lambda p: (-p['rate'], -p['total']))
        return players

    # ---------- 回放聚合 ----------
    def _iter_replays(self):
        """迭代所有可读的回放文件。"""
        if not os.path.isdir(self.records_dir):
            return
        pattern = os.path.join(self.records_dir, 'replay_*.json')
        for path in sorted(glob.glob(pattern)):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                if not content:
                    continue
                yield json.loads(content)
            except (json.JSONDecodeError, OSError):
                continue

    def collect_skill_stats(self) -> Counter:
        """技能使用次数。"""
        counter = Counter()
        for replay in self._iter_replays():
            for ev in replay.get('events', []):
                if ev.get('type') == 'skill_use':
                    counter[ev.get('skill_name', '?')] += 1
        return counter

    def collect_card_stats(self) -> Counter:
        """牌型出现次数（打出 + 被加牌）。"""
        counter = Counter()
        for replay in self._iter_replays():
            for ev in replay.get('events', []):
                if ev.get('type') == 'play_card':
                    counter[ev.get('card', '?')] += 1
                elif ev.get('type') == 'add_cards':
                    for card_info in ev.get('cards', []):
                        # cards_info 结构: [color, value|None, type|None]
                        if len(card_info) != 3:
                            continue
                        color, value, func = card_info
                        if func:
                            counter[f"{color}{func}"] += 1
                        elif value is not None:
                            counter[f"{color}{value}"] += 1
                        else:
                            counter[f"{color}?"] += 1
        return counter

    def collect_game_stats(self) -> Dict[str, Any]:
        """对局统计：总局数、总回合数、平均回合数、最长/最短、胜者分布。"""
        total_games = 0
        turn_counts = []
        winners = Counter()
        for replay in self._iter_replays():
            total_games += 1
            turns = 0
            for ev in replay.get('events', []):
                if ev.get('type') == 'turn_start':
                    turns += 1
                elif ev.get('type') == 'game_end':
                    winners[ev.get('winner', '?')] += 1
            turn_counts.append(turns)
        return {
            'total_games': total_games,
            'total_turns': sum(turn_counts),
            'avg_turns': (sum(turn_counts) / len(turn_counts)) if turn_counts else 0.0,
            'max_turns': max(turn_counts) if turn_counts else 0,
            'min_turns': min(turn_counts) if turn_counts else 0,
            'winners': winners,
        }


class StatsPanel:
    """用 rich 展示统计数据；无 rich 时降级为普通文本。"""

    def __init__(self, ui=None, records_dir: Optional[str] = None):
        self.ui = ui
        self.collector = StatsCollector(records_dir=records_dir)
        self.rich = _try_rich()

    # ---------- 公开接口 ----------
    def show_all(self):
        """依次显示所有面板。"""
        self.show_player_ranking()
        self.show_skill_usage()
        self.show_card_stats()
        self.show_game_stats()

    def show_player_ranking(self):
        players = self.collector.collect_player_stats()
        if not players:
            self._say("暂无玩家数据。")
            return

        if self.rich:
            console = self.rich['Console']()
            table = self.rich['Table'](
                title="🏆 玩家排行榜",
                show_header=True,
                header_style="bold magenta"
            )
            table.add_column("玩家", style="cyan", no_wrap=True)
            table.add_column("胜", justify="right", style="green")
            table.add_column("负", justify="right", style="red")
            table.add_column("总", justify="right")
            table.add_column("胜率", justify="right", style="yellow")
            table.add_column("成就", style="dim")

            for p in players:
                ach_str = ', '.join(p['achievements']) if p['achievements'] else '—'
                table.add_row(
                    p['name'], str(p['wins']), str(p['losses']),
                    str(p['total']), f"{p['rate']:.1f}%", ach_str
                )
            console.print(table)
        else:
            rows = [
                [p['name'], p['wins'], p['losses'], p['total'],
                 f"{p['rate']:.1f}%", ', '.join(p['achievements']) or '—']
                for p in players
            ]
            self._fallback_show("玩家排行榜", rows,
                                ["玩家", "胜", "负", "总", "胜率", "成就"])

    def show_skill_usage(self):
        counter = self.collector.collect_skill_stats()
        if not counter:
            self._say("暂无技能使用数据（需要先录制对局）。")
            return
        items = counter.most_common()

        if self.rich:
            console = self.rich['Console']()
            table = self.rich['Table'](
                title="🎯 技能使用统计",
                show_header=True,
                header_style="bold magenta"
            )
            table.add_column("排名", justify="right", style="dim")
            table.add_column("技能", style="cyan")
            table.add_column("次数", justify="right", style="green")
            for rank, (name, count) in enumerate(items, 1):
                table.add_row(str(rank), name, str(count))
            console.print(table)
        else:
            rows = [[i, name, count] for i, (name, count) in enumerate(items, 1)]
            self._fallback_show("技能使用统计", rows, ["排名", "技能", "次数"])

    def show_card_stats(self, top_n: int = 20):
        counter = self.collector.collect_card_stats()
        if not counter:
            self._say("暂无牌型数据（需要先录制对局）。")
            return
        items = counter.most_common(top_n)

        if self.rich:
            console = self.rich['Console']()
            table = self.rich['Table'](
                title=f"🃏 牌型出现次数 Top {top_n}",
                show_header=True,
                header_style="bold magenta"
            )
            table.add_column("排名", justify="right", style="dim")
            table.add_column("牌", style="cyan")
            table.add_column("次数", justify="right", style="green")
            for rank, (name, count) in enumerate(items, 1):
                table.add_row(str(rank), name, str(count))
            console.print(table)
        else:
            rows = [[i, name, count] for i, (name, count) in enumerate(items, 1)]
            self._fallback_show(f"牌型出现次数 Top {top_n}", rows,
                                ["排名", "牌", "次数"])

    def show_game_stats(self):
        stats = self.collector.collect_game_stats()
        if stats['total_games'] == 0:
            self._say("暂无对局数据（需要先录制对局）。")
            return

        winner_str = ', '.join(
            f"{name}×{cnt}" for name, cnt in stats['winners'].most_common()
        ) or '—'

        if self.rich:
            console = self.rich['Console']()
            body = (
                f"[cyan]总局数[/cyan]: {stats['total_games']}\n"
                f"[cyan]总回合数[/cyan]: {stats['total_turns']}\n"
                f"[cyan]平均回合数[/cyan]: {stats['avg_turns']:.1f}\n"
                f"[cyan]最长对局[/cyan]: {stats['max_turns']} 回合\n"
                f"[cyan]最短对局[/cyan]: {stats['min_turns']} 回合\n"
                f"[cyan]胜者分布[/cyan]: {winner_str}"
            )
            panel = self.rich['Panel'](
                body, title="📊 对局统计", border_style="magenta"
            )
            console.print(panel)
        else:
            print("\n=== 对局统计 ===")
            print(f"总局数: {stats['total_games']}")
            print(f"总回合数: {stats['total_turns']}")
            print(f"平均回合数: {stats['avg_turns']:.1f}")
            print(f"最长对局: {stats['max_turns']} 回合")
            print(f"最短对局: {stats['min_turns']} 回合")
            print(f"胜者分布: {winner_str}")

    # ---------- 内部 ----------
    def _say(self, text: str):
        if self.ui is not None:
            self.ui.show(text)
        else:
            print(text)

    def _fallback_show(self, title: str, rows: List[List[Any]],
                       headers: List[str]):
        """无 rich 时的降级显示。"""
        print(f"\n=== {title} ===")
        col_widths = [len(h) for h in headers]
        for row in rows:
            for i, cell in enumerate(row):
                col_widths[i] = max(col_widths[i], len(str(cell)))
        print('  '.join(h.ljust(col_widths[i]) for i, h in enumerate(headers)))
        print('-' * (sum(col_widths) + 2 * (len(headers) - 1)))
        for row in rows:
            print('  '.join(str(c).ljust(col_widths[i]) for i, c in enumerate(row)))
