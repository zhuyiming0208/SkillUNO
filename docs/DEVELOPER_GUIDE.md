# SkillUNO 开发者文档

**版本：v1.3.2**  
**最后更新：2026-09-12**

本文档面向希望为 SkillUNO 编写 Mod、自定义 UI 或扩展游戏核心的开发者。如果你是玩家，请先阅读 `FAQ.md`。  
如需查看历史修复记录，请参阅 `VersionBriefHistory.md`。

---

## 一、项目概述

SkillUNO 是一个基于 Python 的 UNO 卡牌游戏框架，核心设计理念是 **事件驱动 + Mod 化**。所有技能、赛季、甚至 UI 都可以通过简单的 Python 类进行扩展，无需修改核心引擎。

当前稳定版本：**v1.3.2**

---

## 二、目录结构

```

src/
├── tests/
│   ├── init.py
│   └── test_all.py             # 完整单元测试套件
├── uno/
│   ├── records/                # 对局回放目录
│   │   └── replay_*.json
│   ├── core.py                 # 游戏引擎（核心）
│   ├── skills_uno.py           # 技能加载器（依赖/排斥/容忍）
│   ├── ui.py                   # UI 抽象层（ConsoleUI / NullUI / RichUI）
│   ├── combo_base.py           # 组合技基类
│   ├── achievements.py         # 成就系统（含隐藏成就）
│   ├── archive.py              # 战绩存档
│   ├── presets.py              # 房间规则预设
│   ├── replay.py               # 录制与回放
│   ├── season1.py              # 经典赛季 S1
│   ├── season2.py              # 被动觉醒赛季 S2
│   ├── season3.py              # 同盟赛季 S3（预留）
│   ├── season4.py              # 补丁赛季 S4
│   ├── archive.txt             # Base64 加密的存档
│   └── init.py
├── mods/                       # 玩家自制 Mod 目录
│   ├── HOW_TO_MAKE_A_MOD.md
│   └── init.py
├── main.py                     # 入口
├── FAQ.md
├── DEVELOPER_GUIDE.md          # 本文档
├── VersionBriefHistory.md      # 版本修复历史
└── how_to_go_from_a_beginner_to_an_expert.md

```

---

## 三、核心概念

### 3.1 事件系统

游戏在关键节点触发事件，技能通过监听这些事件生效。

| 事件 | 触发时机 | 上下文关键键 |
|------|----------|--------------|
| `GAME_START` | 游戏开始时 | — |
| `TURN_START` | 玩家回合开始时 | `player` |
| `BEFORE_PLAY` | 出牌前 | `player`, `card` |
| `AFTER_PLAY` | 出牌后 | `player`, `card` |
| `BEING_ADDED_CARDS` | 即将被加牌 | `target`, `amount`, `cancel`, `add_multiplier` |
| `CARDS_ADDED` | 加牌完成后 | `target`, `amount`, `cards_info` |
| `PLAYER_DIED` | 玩家被淘汰时 | `player` |
| `PLAYER_ELIMINATED` | 玩家被淘汰后 | `player` |
| `SKILL_ACTIVATED` | 技能被激活时 | `activated_skill`, `skill_name`, `skill_activation_name` |
| `START_RANDOM` | 随机事件开始 | `source_skill`, `player`, `dice`, `retry` |
| `END_RANDOM` | 随机事件结束 | `source_skill`, `result` |

### 3.2 技能类

所有技能必须继承 `uno.core.Skill`。

```python
from uno.core import Skill, SkillType, GameEvent

class MySkill(Skill):
    def __init__(self, owner, game):
        super().__init__(
            name='技能名',
            skill_type=SkillType.ACTIVE,   # ACTIVE / PASSIVE / DEATH
            description='简短描述',
            help_text='详细说明',
            owner=owner,
            game=game,
            urgency_weight=50              # 可选，AI 使用该技能的紧迫度基准值
        )

    def can_trigger(self, event, context):
        if self.is_consumed or self.is_deleted:
            return False
        return event == GameEvent.TURN_START

    def activate(self, event, context):
        self.owner_print(f"{self.owner.name} 发动了 {self.name}！")
        self.is_consumed = True
        return True
```

技能类型：

类型 说明
ACTIVE 主动技能，玩家手动发动
PASSIVE 被动技能，满足条件自动触发
DEATH 亡语技能，玩家被淘汰时触发

3.3 AI 紧迫度系统

这是 SkillUNO 的 AI 决策核心机制。所有主动技能（ACTIVE）都会在 AI 回合开始时被评估，只有紧迫度 > 20 的技能才会被 AI 主动使用。

3.3.1 基本机制

AI 使用 max() 从可用主动技中选择紧迫度最高的一个：

```python
best_skill = max(usable, key=lambda s: s.evaluate_urgency(self.game))
if best_skill.evaluate_urgency(self.game) > 20:
    # 发动技能
```

3.3.2 静态紧迫度：urgency_weight

在构造函数中传入。默认值 50。适用于价值不随局势变化的技能。

```python
super().__init__(..., urgency_weight=70)
```

分档参考表：

分数 语义 典型场景
0 绝不该用 会把好牌给对手、纯亏本技能
10 极低 高风险赌博（如惊雷给自己加牌的代价）
30 低 信息类、收益不确定
50 常规（默认） 使用总比不用好
70 较高 防御、保命、针对对手低手牌
90 极高 翻盘技、必杀技

3.3.3 动态紧迫度：evaluate_urgency(self, game)

当技能价值取决于场上局势时，重写此方法。返回 0–100 的整数。

示例 A：对手越接近胜利越紧急

```python
def evaluate_urgency(self, game):
    for p in game.players:
        if p != self.owner and not p.eliminated and p.hand_size() <= 2:
            return 90
    return 40
```

示例 B：自己手牌越多越不想冒险

```python
def evaluate_urgency(self, game):
    if self.owner.hand_size() >= 12:
        return 10
    if self.owner.hand_size() <= 3:
        return 40
    return 0
```

示例 C：有先决条件才能用

```python
def evaluate_urgency(self, game):
    targets = [c for c in self.owner.hand if c.type == '数字' and c.value <= 4]
    if not targets:
        return 0
    # 下家手牌少时优先用
    next_p = game.peek_next_player()
    if next_p and next_p.hand_size() <= 2:
        return 90
    return 50
```

示例 D：结盟技只在未结盟时使用

```python
def evaluate_urgency(self, game):
    return 70 if self.ally is None else 0
```

3.3.4 阈值 20 的含义

· 小于等于 20：AI 视为“不值得主动发动”，会跳过。
· 大于 20：AI 视为“可以发动”，会在没有更好选择时使用。
· 大于 70：AI 视为“优先发动”，通常会在回合开始时立刻使用。

3.3.5 哪些技能不参与评估

· PASSIVE：由事件自动触发，不进入主动技能列表。
· DEATH：亡语，由 PLAYER_DIED 触发。
· 拦截型 ACTIVE（如 离析、祸水）：虽然类型是 ACTIVE，但它们的 can_trigger 只响应 BEING_ADDED_CARDS，不响应 TURN_START，因此不会被 AI 评估。

3.3.6 官方赛季的紧迫度参考

技能 紧迫度策略
招灾 对手 ≤2 张时 90，否则 40
惊雷 手牌≥12 时 10，≤3 时 40，否则 0
离析 / 祸水 手牌≥10 时 80，否则 50
化形 手牌≥12 时 20，≤4 时 70，否则 45
破万法 / 储能 固定 55
巧物 固定 50
读心 固定 40
始皇帝 对手最高手牌≥10 时 90，否则 70
苏秦 手牌≥8 时 70，否则 30
张仪 无可转化牌 0；下家≤2 张 90；否则 50
双生花 未结盟 70，已结盟 0
金身 固定 60
鹰眼 固定 30
孤勇者 抽牌≥7 时 90，否则 0
探囊 有对手 ≤2 张时 75，否则 55
显灵 固定 35
嫁祸 固定 60
激发 固定 30
业力 固定 40
夺心魄 固定 70
魂迁 固定 65
赝品 固定 40

Mod 作者可以参考这些数值设计自己的技能。

3.4 组合技

多个技能可以定义组合效果。

```python
from uno.combo_base import ComboBase

class MyCombo(ComboBase):
    def execute(self, player, skill_manager, game):
        # 组合技效果
        for s in player.skills:
            if s.name in ('技能A', '技能B'):
                s.is_consumed = True
```

在技能类中声明：

```python
self.combo_partners = ('技能A', '技能B')
self.combo_effect = MyCombo
```

注意：组合技不经过 AI 紧迫度评估，需要玩家手动触发（在 s 菜单中显示为独立选项）。

3.5 上下文

事件触发时携带 context 字典，技能可读写：

键 类型 可写 说明
player Player 否 当前玩家
target Player ✅ 加牌目标（可转移）
amount int ✅ 加牌数量
cancel bool ✅ 设为 True 取消效果
add_multiplier float ✅ 加牌倍数
activated_skill Skill 否 被激活的技能
cards_info list 否 抽到的牌信息
retry bool ✅ 重掷骰子/转盘

---

四、UI 系统（v1.1.2 起完全解耦）

SkillUNO 的 UI 层已与游戏逻辑完全解耦。核心提供三种 UI 实现，全部位于 uno/ui.py：

4.1 内置 UI 类

类名 用途 行为
ConsoleUI 普通命令行 UI 使用 print / input
NullUI AI 专用静默 UI 所有方法为空操作
RichUI 彩色 UI（需 rich） 富文本、卡牌着色

统一接口：

```python
class ConsoleUI:
    def show(self, text=""): ...             # 显示一行文本
    def input(self, prompt=""): ...          # 获取输入
    def print_inline(self, text="", end=''): # 行内输出
    def clear_screen(self): ...              # 清屏
    def pause(self, message=""): ...         # 暂停等待输入
```

RichUI 额外提供 show_card、show_hand、show_skill、show_turn_header、show_uno_reminder 等彩色渲染方法。

4.2 UI 参数（ERROR-019 修复重点）

UNOGame.__init__ 提供了两个可选的 UI 参数，用于完全自定义人类玩家与 AI 的 UI：

```python
def __init__(
    self,
    human_name: str = "你",
    enabled_seasons: List[str] = None,
    debug: bool = False,
    dev_skills: Dict[str, List[type]] = None,
    use_rich_ui: bool = False,
    recorder: 'GameRecorder' = None,
    players: List[str] = None,
    human_ui: ConsoleUI = None,     # ✅ 人类玩家 UI
    ai_ui: ConsoleUI = None,         # ✅ AI 玩家 UI
    hand_limit: int = 15,
    initial_hand_size: int = 7,
    initial_skill_count: int = 3,
):
```

参数说明：

参数 类型 默认 说明
human_ui ConsoleUI None 人类玩家使用的 UI。如果传入，则 use_rich_ui 被忽略。可以传入任何继承自 ConsoleUI 的实现。
ai_ui ConsoleUI None AI 玩家使用的 UI。如果为 None，自动使用 NullUI()（静默），确保 AI 不会向人类玩家泄露信息。

优先级规则：

1. 如果 human_ui 不是 None，使用它作为人类玩家 UI。
2. 否则，如果 use_rich_ui=True，尝试加载 RichUI；失败则回退到 ConsoleUI。
3. 否则，使用 ConsoleUI。
4. AI 玩家使用 ai_ui；如果为 None，则自动使用 NullUI()。

使用示例：

```python
# 场景 1：使用默认彩色 UI
game = UNOGame("你", ['S1'], use_rich_ui=True)

# 场景 2：使用自定义 UI（例如 Web UI）
from my_web_ui import WebUI
game = UNOGame("你", ['S1'], human_ui=WebUI())

# 场景 3：让 AI 也显示输出（调试用）
from uno.ui import ConsoleUI, RichUI
game = UNOGame("你", ['S1'], human_ui=RichUI(), ai_ui=ConsoleUI())

# 场景 4：热座模式
game = UNOGame(
    enabled_seasons=['S1'],
    players=['Alice', 'Bob'],
    human_ui=ConsoleUI()
    # 所有玩家共享同一个 human_ui
)
```

为什么需要 ai_ui？
AI 玩家不需要与人类交互，但在某些调试场景下，你可能希望看到 AI 的内部决策过程。传入 ConsoleUI() 即可让 AI 的 ui.show 输出到控制台。默认 NullUI() 则完全静默。

4.3 自定义 UI

任何 UI 实现只需继承 ConsoleUI 并覆盖所需方法：

```python
from uno.ui import ConsoleUI

class MyUI(ConsoleUI):
    def show(self, text=""):
        # 发送到自定义通道
        pass

    def input(self, prompt=""):
        # 从自定义通道接收
        return ""

    def print_inline(self, text="", end=''):
        pass

    def clear_screen(self):
        pass

    def pause(self, message=""):
        return ""
```

游戏中的所有输出都通过 player.ui.show(...)、self.ui.show(...) 或 game.broadcast(...) 进行，不会直接调用 print。这保证了自定义 UI 能够完全接管显示。

---

五、创建 Mod

5.1 基本步骤

1. 在 mods/ 下创建 my_season.py。
2. 定义必需变量：

```python
SEASON_ID = "MY_SEASON"
SEASON_NAME = "我的赛季"
SKILL_CLASSES = [MySkill1, MySkill2]
```

3. 可选地声明依赖关系：

```python
RELY_ON = ("S1", "依赖 S1 的技能")
REJECT = {"S2": "与 S2 不兼容"}
ONLY_TOLERATE = ("S1", "S4")
```

4. 编写技能类（见 3.2 与 3.3）。

详细说明见 mods/HOW_TO_MAKE_A_MOD.md。

5.2 依赖 / 排斥 / 容忍

加载器按顺序验证：

1. RELY_ON：如果 A 依赖 B，但 B 未启用 → A 加载失败。
2. REJECT：如果 A 排斥 B，且两者同时启用 → 双方都加载失败。
3. ONLY_TOLERATE：如果 A 仅容忍 B、C，而加载列表中有 D → D 加载失败。

注意：三者是独立的规则，但请避免自相矛盾（例如既 REJECT 排斥 S1，又 ONLY_TOLERATE 允许 S1 共存）。加载器不会主动检测这类矛盾。

5.3 添加成就

在 Mod 文件中定义成就类：

```python
from uno.achievements import Achievement

class MyAchievement(Achievement):
    def __init__(self):
        super().__init__('my_ach', '自定义成就', '描述')
    def check(self, game, events):
        human = game.players[0]  # 不要硬编码 '你'
        return any(
            e['type'] == 'play_card' and e['player'] == human.name
            for e in events
        )

ACHIEVEMENTS = [MyAchievement]
```

加载器自动收集并注册到 AchievementManager。

---

六、可用的游戏 API

在技能内部，可以通过 self.game 访问：

```python
# 玩家列表
active_players = [p for p in self.game.players if not p.eliminated]

# 当前玩家
current = self.game.current_player()

# 下一位玩家
next_p = self.game.peek_next_player()

# 给目标加牌（自动触发事件链）
self.game.apply_add_cards(target, amount)

# 广播一条消息给所有可见 UI 的玩家
self.game.broadcast("消息")

# 触发事件
self.game.skill_manager.trigger(GameEvent.SOME_EVENT, context)

# 记录事件（同时写入 event_log 与 recorder）
self.game.record_event('custom_event', player='X', detail='Y')
```

game.broadcast(message)

broadcast 会向所有 可见 UI（即非 NullUI）的玩家发送消息，自动去重。适用于需要全体玩家看到的信息，例如淘汰公告、加牌通知。

---

七、房间规则

UNOGame.__init__ 支持自定义房间规则：

```python
game = UNOGame(
    "你", ['S1'],
    hand_limit=10,          # 手牌上限（默认 15）
    initial_hand_size=5,    # 起始手牌数（默认 7，范围 5~10）
    initial_skill_count=1,  # 初始技能数（默认 3，范围 1~3）
)
```

预设保存在 uno/presets.json（Base64 编码），通过 uno/presets.py 管理：

```python
from uno.presets import load_presets, add_preset, get_preset

add_preset("快速局", hand_limit=8, initial_hand_size=5, initial_skill_count=2)
presets = load_presets()
```

---

八、调试与测试

8.1 调试模式

启动游戏时选择 1 开启。输出会显示事件触发、技能调用、反制查询等详细流程。调试输出通过 self.game.ui 输出，遵循 UI 抽象。

8.2 开发技能覆盖

```python
from uno.season1 import PoWanFa, QiaoWu, ChuNeng

game = UNOGame(
    human_name="你",
    enabled_seasons=['S1'],
    debug=True,
    dev_skills={"你": [PoWanFa, QiaoWu, ChuNeng]}
)
```

8.3 对局录制与回放

```python
from uno.replay import GameRecorder

recorder = GameRecorder()
game = UNOGame("你", ['S1'], recorder=recorder)
game.run()
# 结束后自动保存到 uno/records/replay_YYYYMMDD_HHMMSS.json
```

回放：

```python
from uno.replay import GameReplayer
from uno.ui import ConsoleUI

replayer = GameReplayer.interactive_choose(ConsoleUI())
replayer.replay_all()
```

8.4 单元测试

```bash
python -m unittest tests.test_all
```

当前共 30 个测试，覆盖卡牌、牌堆、技能、加载器（依赖/排斥/容忍）、成就、回放、房间规则、热座模式。

---

九、事件上下文参考（速查表）

事件 player target amount cancel add_multiplier retry 其他
GAME_START — — — — — — —
TURN_START ✅ — — — — — —
BEFORE_PLAY ✅ — — — — — card
AFTER_PLAY ✅ — — — — — card
BEING_ADDED_CARDS — ✅ ✅ ✅ ✅ — —
CARDS_ADDED — ✅ ✅ — — — cards_info
PLAYER_DIED ✅ — — — — — —
PLAYER_ELIMINATED ✅ — — — — — —
SKILL_ACTIVATED — — — ✅ — — activated_skill, skill_name
START_RANDOM ✅ — — — — ✅ dice, source_skill
END_RANDOM ✅ — — — — — result

---

十、常见问题

Q：我的技能没有被加载？

· 检查 SKILL_CLASSES 是否正确注册
· 检查 SEASON_ID 是否重复
· 检查依赖关系是否满足（RELY_ON）
· 查看控制台是否有 ImportError

Q：技能不触发？

· 确认 can_trigger 返回 True
· 确认技能未消耗（is_consumed / is_deleted）
· 检查监听的事件是否匹配

Q：AI 不用我的技能？

· 检查 urgency_weight 是否 ≥ 20
· 如果依赖局势，重写 evaluate_urgency(self, game)，参见 3.3 节

Q：如何取消加牌？
在 BEING_ADDED_CARDS 中设置 context['cancel'] = True。

Q：如何修改加牌数量？
修改 context['amount'] 或 context['add_multiplier']。

Q：如何自定义 UI？
继承 uno.ui.ConsoleUI，实现 show / input / print_inline / clear_screen / pause，然后通过 human_ui 参数传入。

Q：AI 的输出会不会泄露给人类玩家？
不会。默认 ai_ui=NullUI()，AI 的 ui.show 会被静默。仅当显式传入可见 UI 时才会输出。

Q：如何手动编辑存档？
archive.txt 为 Base64 编码的 JSON。使用 Python 生成：

```python
import json, base64
data = {"你的名字": {"wins": 10, "losses": 2, "achievements": []}}
print(base64.b64encode(json.dumps(data, ensure_ascii=False).encode('utf-8')).decode('ascii'))
```

Q：加载器报错“排斥冲突”是什么情况？
说明两个赛季/Mod 声明了互相排斥。双方都会被剔除。参见 5.2 节。

Q：ONLY_TOLERATE 把某个赛季踢掉了，是 bug 吗？
不是。它是白名单机制：不在白名单里的赛季会被自动剔除。如果你不想剔除任何赛季，就不要声明这个常量。

---

十一、v1.3.2 修复摘要（面向开发者）

v1.3.2 修复了 ERROR-021 与 ERROR-022：

编号 修复
ERROR-021 run() 淘汰分支不再硬编码 winner='?'，动态推断实际赢家
ERROR-022 热座模式下为每位人类玩家分别记录胜负到存档

完整的修复记录（包括 ERROR-001 ~ ERROR-020）请参阅 VersionBriefHistory.md。

---

十二、后续版本计划

参见 VersionBriefHistory.md 的末尾「后续版本计划」一节，包含：

· TODO-001：成就按玩家分别评估（热座模式）→ v1.4.0
· TODO-002：AI 战术增强 → v1.4.0+
· TODO-003：统计面板 → v1.5.0
· TODO-004：随机赛季 → 待定
· TODO-005：固定种子及每日任务 → 待定
· TODO-006：联机模式 → 待定

---

十三、许可证

SkillUNO 为个人项目，代码仅供学习和参考。

如有疑问或建议，请提交 Issue 或联系维护者。