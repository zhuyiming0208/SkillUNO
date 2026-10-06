## 模组元数据 JSON 格式

从 v1.3.4 起，SkillUNO CLI 模组商店通过 JSON 元数据发现、展示和索引你的模组。
你需要在模组仓库根目录放一个 `skilluno_mod.json` 文件，并在 GitHub 仓库加上
`skilluno-mod` topic，就能被自动收录。

### 单模组 JSON（`skilluno_mod.json`）

| 字段 | 必填 | 类型 | 说明 |
|------|:---:|------|------|
| `ID` | ✅ | str | 全局唯一标识，推荐大写字母与数字，如 `MY_MOD` |
| `name` | ✅ | str | 显示名称，如 `"我的疯狂赛季"` |
| `description` | ✅ | str | 一句话简介，展示在列表中 |
| `author` | ✅ | str | 作者昵称 |
| `author_github` | ❌ | str | GitHub 用户名，用于展示头像与主页 |
| `repo` | ✅ | str | 仓库地址，如 `https://github.com/you/your-mod` |
| `license` | ❌ | str | 许可证，如 `MIT`、`GPL-3.0` |
| `version` | ✅ | str | 模组自身版本号，遵循 [SemVer](https://semver.org/lang/zh-CN/) |
| `micover` | ✅ | str | 最低兼容的 SkillUNO 版本 |
| `lacover` | ✅ | str \| null | 最高兼容版本；`null` 表示不限 |
| `skills` | ✅ | int | 本模组包含的技能数量 |
| `achievements` | ❌ | int | 本模组包含的成就数量 |
| `needs` | ❌ | list[str] | 需要的接口列表，如 `["core.Skill"]` |
| `rely_on` | ❌ | dict | 依赖声明，格式见下 |
| `reject` | ❌ | dict | 排斥声明，格式见下 |
| `only_tolerate` | ❌ | list[str] | 白名单，仅允许与这些赛季共存 |
| `tags` | ❌ | list[str] | 标签，用于分类检索 |
| `created_at` | ❌ | str | 创建日期，`YYYY-MM-DD` |
| `updated_at` | ❌ | str | 更新日期，`YYYY-MM-DD` |

### 空值写法

| 类型 | 空值 |
|------|------|
| 字典 | `{}` |
| 列表 | `[]` |
| 无值 | `null` |

> ⚠️ 不要用空字符串 `""` 代替 `null`，会导致解析歧义。

### 索引文件 `mods/mod_idx.json`

CLI 商店读取的本地索引，由 GitHub Action 自动维护：

```json
{
  "handpicked": ["example.json"],
  "other": ["another_mod.json"],
  "version": "1.0.0",
  "update_time": "2026-10-06"
}

· handpicked：官方精选的模组元数据文件名列表
· other：其余收录的模组元数据文件名列表
· version：索引格式版本
· update_time：最近一次更新时间

自动发现机制

如果你希望模组被官方索引自动收录：

1. 在模组仓库根目录放 skilluno_mod.json（字段见上表）
2. 给仓库添加 GitHub topic：skilluno-mod
3. 提交到官方索引 PR，或等待 GitHub Action 定期抓取

安全声明

⚠️ 第三方模组由社区作者提供，SkillUNO 官方不对其内容负责。
下载和安装前，请确认来源可信、代码可审计。若发现恶意行为，请提交 Issue。

---

# SkillUNO 玩家自制赛季指南

欢迎制作你自己的 SkillUNO 赛季！只要遵循以下规范，你的赛季就能被游戏自动加载，并与官方赛季、其他 Mod 共存。

---

## 一、文件放置

在 `mods/` 文件夹下创建一个 `.py` 文件，比如 `my_crazy_season.py`。

- 文件名随意，但不要用中文和特殊符号。
- 如果 `mods/` 目录下没有 `__init__.py`，请手动创建一个空文件。
- 加载器会自动扫描该目录下的所有 `.py` 文件。

---

## 二、必须定义的三个变量

| 变量名 | 类型 | 说明 |
|--------|------|------|
| `SEASON_ID` | str | 赛季唯一标识，推荐大写字母和数字，如 `MOD_MY`。**不能与官方赛季重复**（`S1`/`S2`/`S4`）。 |
| `SEASON_NAME` | str | 赛季显示名称，如 `"我的疯狂赛季"`。 |
| `SKILL_CLASSES` | list | 包含所有技能类的列表，每个类必须继承自 `uno.core.Skill`。 |

示例：

```python
SEASON_ID = "MOD_LUCK"
SEASON_NAME = "幸运与诅咒"
SKILL_CLASSES = [LuckyDraw, CurseBack]
```

玩家在选择赛季组合时输入 MOD_LUCK，或在启动参数中写 1,MOD_LUCK 即可加载。

---

三、技能类怎么写

技能类需要继承 uno.core.Skill，并实现 can_trigger 和 activate 两个方法。

3.1 构造函数

```python
from uno.core import Skill, SkillType, GameEvent

class MySkill(Skill):
    def __init__(self, owner, game):
        super().__init__(
            name='我的技能',           # 显示名称
            skill_type=SkillType.ACTIVE,  # ACTIVE / PASSIVE / DEATH
            description='这是描述',       # 列表里显示的一行简介
            help_text='这是详细帮助',     # help 命令显示的文本
            owner=owner,                  # 拥有者
            game=game                     # 游戏对象
        )
```

参数 说明
ACTIVE 主动技，玩家在回合中输入 s 手动选择发动
PASSIVE 被动技，满足条件自动触发
DEATH 亡语技，玩家被淘汰时触发

3.2 必须重写的方法

can_trigger(self, event, context) -> bool

判断技能能否在当前事件触发。必须在最开始检查 is_consumed 和 is_deleted：

```python
def can_trigger(self, event, context):
    if self.is_consumed or self.is_deleted:
        return False
    return event == GameEvent.TURN_START
```

activate(self, event, context) -> bool

执行技能效果。用完一次性技能记得设置 self.is_consumed = True：

```python
def activate(self, event, context):
    self.owner_print(f"{self.owner.name} 发动了 {self.name}！")
    self.is_consumed = True
    return True
```

self.owner_print(text) 只会在拥有者是人类玩家时输出，用于保护隐私（AI 的内部决策不会展示给人类）。所有面向全体玩家的通知请改用 self.game.broadcast(text)。

---

四、可用的工具

4.1 游戏对象 self.game

方法/属性 说明
self.game.players 所有玩家列表
self.game.deck.draw(n) 抽 n 张牌
self.game.apply_add_cards(target, n) 给目标加牌（自动触发事件链）
self.game.peek_next_player() 获取下一位存活玩家（不改变回合）
self.game.current_player() 获取当前回合玩家
self.game.broadcast(text) 向所有可见 UI 的玩家广播
self.game.record_event(type, **kwargs) 手动记录事件（用于成就与回放）

4.2 技能管理器 self.game.skill_manager

方法 说明
trigger(event, context) 手动触发一个事件
execute_skill(skill, event, context) 执行技能并走完整反制流程
ask_human_intercept(player, event, context) 询问人类玩家是否拦截

4.3 上下文 context

事件的附加数据，常见键：

键 类型 可写 说明
player Player 否 当前玩家
target Player ✅ 加牌目标（可转移）
amount int ✅ 加牌数量
cancel bool ✅ 设为 True 取消效果
add_multiplier float ✅ 加牌倍数
retry bool ✅ 重掷随机结果

4.4 事件列表 GameEvent

事件 触发时机
GAME_START 游戏开始时
TURN_START 玩家回合开始时
BEFORE_PLAY / AFTER_PLAY 出牌前后
BEING_ADDED_CARDS 即将被加牌（可取消）
CARDS_ADDED 加牌完成
PLAYER_DIED 玩家被淘汰（用于亡语）
SKILL_ACTIVATED 技能被激活（用于反制）
START_RANDOM / END_RANDOM 随机事件开始 / 结束

---

五、让你的技能被 AI 正确使用（重要）

这是很多 Mod 作者最容易忽略的一点。

SkillUNO 的 AI 会评估每个可用技能的 紧迫度（urgency），只有分数 大于 20 才会考虑使用。如果你的技能没有正确设置紧迫度，AI 永远都不会主动使用它。

5.1 默认行为

如果你什么都不设置，Skill 基类默认给 urgency_weight = 50，AI 会把它视为普通主动技来评估。对于大多数“使用总比不用好”的技能，这已经足够。

5.2 静态紧迫度：urgency_weight

在 super().__init__(...) 中传入：

```python
super().__init__(
    '我的技能', SkillType.ACTIVE, '描述', '帮助',
    owner, game,
    urgency_weight=70
)
```

分档参考表：

分数 场景
0 绝不该用（例如会把好牌给对手的技能）
10 极低（有风险，只在运气好时才赚）
30 低（信息类、收益不确定）
50 常规（默认值，适用于大多数技能）
70 较高（防御、保命、针对对手低手牌）
90 极高（翻盘技、必须立即发动）

5.3 动态紧迫度：evaluate_urgency(self, game)

如果技能的价值取决于场上局势，请重写此方法。它返回 0–100 的整数。

示例 1：对手手牌越少，越值得用

```python
class ThreatSkill(Skill):
    def evaluate_urgency(self, game):
        for p in game.players:
            if p != self.owner and not p.eliminated and p.hand_size() <= 2:
                return 90   # 有对手快赢，必用
        return 40
```

示例 2：手牌越多越危险，不想用

```python
class RiskySkill(Skill):
    def evaluate_urgency(self, game):
        if self.owner.hand_size() >= 12:
            return 10   # 手牌已经很危险，别再乱来
        return 50
```

示例 3：有可触发的先决条件才用

```python
class ConditionalSkill(Skill):
    def evaluate_urgency(self, game):
        targets = [c for c in self.owner.hand if c.type == '数字' and c.value <= 4]
        if not targets:
            return 0    # 没有合适的牌，绝不用
        return 50
```

5.4 哪些技能不需要设紧迫度

· 亡语技（DEATH）：由 PLAYER_DIED 事件自动触发，不参与 AI 评估。
· 被动技（PASSIVE）：由事件自动触发，不参与 AI 评估。
· 拦截技（如 离析、祸水）：由 BEING_ADDED_CARDS 触发，不进入 AI 的主动技能列表。但如果 AI 也可能主动使用它们（例如为了提前进入防御状态），可以设置。

5.5 一个完整示例

```python
from uno.core import Skill, SkillType, GameEvent
import random

class WheelOfFortune(Skill):
    def __init__(self, owner, game):
        super().__init__(
            '命运之轮', SkillType.ACTIVE,
            '随机选择一个玩家，使其加 1~3 张牌',
            '在自己回合使用，转盘随机指向一名存活玩家，该玩家加 1~3 张牌。',
            owner, game,
            urgency_weight=40          # 静态默认值
        )

    def can_trigger(self, event, context):
        if self.is_consumed or self.is_deleted:
            return False
        return event == GameEvent.TURN_START

    def evaluate_urgency(self, game):
        # 存在手牌极少的对手时，收益大增
        for p in game.players:
            if p != self.owner and not p.eliminated and p.hand_size() <= 2:
                return 85
        # 自己手牌过多时，随机目标可能砸到自己，谨慎
        if self.owner.hand_size() >= 12:
            return 15
        return 40

    def activate(self, event, context):
        active = [p for p in self.game.players if not p.eliminated]
        if not active:
            return False
        target = random.choice(active)
        amount = random.randint(1, 3)
        self.game.broadcast(f"命运之轮指向 {target.name}，加 {amount} 张牌！")
        self.game.apply_add_cards(target, amount)
        self.is_consumed = True
        return True
```

这样 AI 在合适的时机就会主动使用你的技能，而不是永远捏在手里。

---

六、可选：依赖 / 排斥 / 容忍

如果你的 Mod 需要和其他赛季合作，或与某些赛季冲突，可以声明以下常量。三者是互相独立的规则，但请避免自相矛盾（例如既排斥 S1，又允许与 S1 共存）。

6.1 依赖：RELY_ON

```python
RELY_ON = ("S2", "本 Mod 使用了苏秦和张仪的组合技")
```

· 类型：tuple[str, str]
· 语义：必须同时启用 S2，否则你的 Mod 会被跳过。
· 如果玩家未启用依赖项，控制台会提示：
  ```
  警告：赛季/Mod XXX 依赖 S2，但该赛季未启用，已跳过。说明：本 Mod 使用了苏秦和张仪的组合技
  ```

6.2 排斥：REJECT

```python
REJECT = {"S1": "技能机制冲突"}
```

· 类型：dict[str, str]
· 语义：不能同时启用 S1。如果玩家同时启用了两者，双方都会被加载失败，并提示原因。
· 支持一对多排斥：
  ```python
  REJECT = {"S1": "冲突原因 A", "S2": "冲突原因 B"}
  ```
· 支持多对多排斥（其他 Mod 也声明排斥你时，双方都会被剔除）。

6.3 容忍：ONLY_TOLERATE

```python
ONLY_TOLERATE = ("S1", "S4")
```

· 类型：tuple[str, ...]
· 语义：只允许与 S1、S4 共存。若玩家还启用了 S2，则 S2 会被剔除（你的 Mod 本身仍加载）。
· 这是一种“白名单”机制，用于强制清理不兼容的赛季。

6.4 三者如何组合

正确示例：依赖 S2，排斥 S1，只允许与 S2、S4 共存

```python
RELY_ON = ("S2", "使用 S2 的技能")
REJECT = {"S1": "机制冲突"}
ONLY_TOLERATE = ("S2", "S4")
```

这个声明是自洽的：依赖 S2（必须启用），排斥 S1（不能启用），白名单只含 S2、S4（与依赖一致）。

错误示例：逻辑自相矛盾

```python
# ❌ 既排斥 S1，又允许与 S1 共存
REJECT = {"S1": "冲突"}
ONLY_TOLERATE = ("S1", "S4")

# ❌ 依赖 S2，但白名单里没有 S2
RELY_ON = ("S2", "使用 S2")
ONLY_TOLERATE = ("S1", "S4")
```

加载器不会主动检测这类语义矛盾，但会导致玩家困惑（提示“排斥 S1”却又不剔除 S1），所以请自行保证一致性。

6.5 加载顺序

加载器按以下顺序验证：

1. 依赖检查：缺失 RELY_ON 声明 → 跳过。
2. 排斥检查：与 REJECT 目标同时启用 → 双方剔除。
3. 容忍检查：白名单外的赛季 → 剔除白名单外的那个。

任何一步失败都会打印原因并更新可用赛季列表。

---

七、可选：添加自定义成就

在 Mod 文件中定义成就类，并放入 ACHIEVEMENTS 列表：

```python
from uno.achievements import Achievement

class MyAchievement(Achievement):
    def __init__(self):
        super().__init__(
            'my_ach',           # 唯一 ID
            '自定义成就',         # 显示名称
            '描述文字'            # 展示给玩家的描述
        )

    def check(self, game, events):
        # game: UNOGame 实例
        # events: 事件日志列表
        # 返回 True 表示达成
        human = game.players[0]   # 人类玩家永远是第一个
        return any(
            e['type'] == 'play_card' and e['player'] == human.name
            for e in events
        )

ACHIEVEMENTS = [MyAchievement]
```

注意：

· 不要硬编码玩家名（例如 '你'）。人类玩家名字是用户在启动时输入的，可能是任意字符串。
· 正确做法是使用 game.players[0].name 获取人类玩家名。
· 如果你想让成就对任何玩家生效（包括 AI），可以遍历 game.players：
  ```python
  def check(self, game, events):
      for p in game.players:
          if any(e['type'] == 'play_card' and e['player'] == p.name for e in events):
              return True
      return False
  ```
· 隐藏成就传入 hidden=True：
  ```python
  super().__init__('secret_ach', '???', '隐藏成就', hidden=True)
  ```
· 加载器会自动收集并注册到成就管理器。玩家达成后，成就名称会写入存档。

---

八、加载你的赛季

启动游戏，在选择赛季组合时输入你的 SEASON_ID：

· MY_SEASON — 只加载你的赛季
· 1,MY_SEASON — 同时启用 S1 和你的赛季
· 1,2,MY_SEASON — 三方共存

如果加载失败，控制台会提示原因（依赖缺失 / 排斥冲突 / 容忍规则 / 文件错误）。

---

九、测试与调试

1. 调试模式：启动时选择 1，会打印所有事件触发、技能调用、反制查询流程。
2. 开发技能覆写：在 main.py 中可以通过 dev_skills 参数强制让某位玩家开局拥有你的技能，快速验证效果：
   ```python
   from uno.season1 import PoWanFa
   from my_mod import MySkill
   
   game = UNOGame(
       "你", ['S1', 'MY_MOD'],
       dev_skills={"你": [PoWanFa, MySkill]}
   )
   ```
3. 回放验证：开启录像后，游戏结束会生成 JSON 记录，可以用来检查你的技能是否按预期触发。
4. 单元测试：如果有兴趣，可以在 tests/ 下编写 unittest，使用 SkillLoader.load_skills 直接测试加载与技能行为。

---

十、常见问题

Q：我的技能没有被加载？

· 检查 SKILL_CLASSES 是否包含所有技能类
· 检查 SEASON_ID 是否与官方或其他 Mod 重复
· 检查依赖关系（RELY_ON）
· 查看控制台是否有 ImportError

Q：技能不触发？

· 确认 can_trigger 返回 True
· 确认技能未消耗（is_consumed / is_deleted）
· 检查监听的事件是否匹配

Q：AI 从来不用我的技能？

· 检查 urgency_weight 是否 ≥ 20
· 如果依赖局势，重写 evaluate_urgency(self, game)，参见第五章

Q：技能直接报错？

· 检查 activate 返回值是否合理
· 检查是否在访问 self.owner.hand 时手牌为空
· 开启调试模式，查看出错的事件链

Q：如何取消加牌？
在 BEING_ADDED_CARDS 中将 context['cancel'] = True。

Q：如何修改加牌数量？
在 BEING_ADDED_CARDS 中修改 context['amount'] 或 context['add_multiplier']。

Q：加载器报错“排斥冲突”是什么情况？
说明你的 Mod 和其他赛季/Mod 都声明了互相排斥，或单方排斥。双方都会被剔除。这是设计行为，避免不兼容的赛季同时运行。

Q：我的 ONLY_TOLERATE 把某个赛季踢掉了，是 bug 吗？
不是。ONLY_TOLERATE 是白名单机制：不在白名单里的赛季会被自动剔除。如果你不想剔除任何赛季，就不要声明这个常量。

---

十一、完整示例：一个可玩的赛季

```python
# mods/my_season.py
from uno.core import Skill, SkillType, GameEvent
import random

SEASON_ID = "MOD_FORTUNE"
SEASON_NAME = "命运之轮"
RELY_ON = ("S1", "复用 S1 的手牌判定逻辑")
ONLY_TOLERATE = ("S1", "S4")


class WheelOfFortune(Skill):
    def __init__(self, owner, game):
        super().__init__(
            '命运之轮', SkillType.ACTIVE,
            '随机选择一个玩家，使其加 1~3 张牌',
            '在自己回合使用，转盘随机指向一名存活玩家，该玩家加 1~3 张牌。',
            owner, game, urgency_weight=40
        )

    def can_trigger(self, event, context):
        if self.is_consumed or self.is_deleted:
            return False
        return event == GameEvent.TURN_START

    def evaluate_urgency(self, game):
        for p in game.players:
            if p != self.owner and not p.eliminated and p.hand_size() <= 2:
                return 85
        if self.owner.hand_size() >= 12:
            return 15
        return 40

    def activate(self, event, context):
        active = [p for p in self.game.players if not p.eliminated]
        if not active:
            return False
        target = random.choice(active)
        amount = random.randint(1, 3)
        self.game.broadcast(f"命运之轮指向 {target.name}，加 {amount} 张牌！")
        self.game.apply_add_cards(target, amount)
        self.is_consumed = True
        return True


class FortuneBlessing(Skill):
    """每回合开始时，有 30% 概率给自己抽一张牌。"""
    def __init__(self, owner, game):
        super().__init__(
            '幸运祝福', SkillType.PASSIVE,
            '每回合开始时，有 30% 概率抽一张牌',
            '被动技能，无需主动发动。',
            owner, game
        )

    def can_trigger(self, event, context):
        if self.is_consumed or self.is_deleted:
            return False
        return event == GameEvent.TURN_START and context.get('player') == self.owner

    def activate(self, event, context):
        if random.random() < 0.3:
            drawn = self.game.deck.draw(1)
            self.owner.hand.append(drawn)
            self.owner_print(f"幸运祝福触发，{self.owner.name} 抽了一张牌。")
        return False  # 被动技不消耗


SKILL_CLASSES = [WheelOfFortune, FortuneBlessing]
ACHIEVEMENTS = []
```

把这个文件保存到 mods/my_season.py，启动游戏输入 1,MOD_FORTUNE 就能体验。

---

现在，发挥你的想象力，为 SkillUNO 增添新乐趣吧！
