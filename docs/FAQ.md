# SkillUNO 常见问题 FAQ

本文档收录了玩家和 Mod 作者在使用 SkillUNO 过程中最常遇到的问题。如果你在游戏中遇到困难，请先查阅本文档。

---

## 一、安装与运行

### Q1: 我需要安装什么依赖？

SkillUNO 使用纯 Python 编写，仅需 Python 3.8 或更高版本。

彩色界面（可选）需要额外安装 `rich`：
```bash
pip install rich
```

如果未安装 rich，游戏会自动降级为普通黑白界面，不影响核心功能。

Q2: 如何启动游戏？

在项目根目录（含 main.py 的目录）下执行：

```bash
python main.py
```

Q3: 为什么我导入 ui 报错 ModuleNotFoundError？

main.py 中必须使用相对包导入：

```python
from uno.ui import ConsoleUI
```

而不是 from ui import ConsoleUI。请确保所有 uno 内部的导入都使用包路径。

---

二、赛季与技能

Q4: 有哪些官方赛季？

ID 名称 技能数量
S1 经典赛季 15
S2 被动觉醒赛季 8
S3 同盟赛季（未实装） 0
S4 补丁赛季 8

启动游戏时输入组合，例如 1 表示只用 S1，124 表示同时启用 S1、S2、S4。

Q5: 什么是“组合技”？

某些技能可以联合发动，例如苏秦和张仪可以一起发动“合纵连横·骰子审判”。当你同时拥有组合中的两个技能时，输入 s 会看到额外选项。

Q6: 技能牌用掉就没了？

是的。技能牌使用后变为“已用”，不会再回来（除非某些技能如 忘忧、激发 重新分配）。所以请珍惜每一次发动。

Q7: 手牌上限是多少？

默认 15 张，达到 16 张立即淘汰。可以在开局前通过“房间规则”调整。

---

三、游戏模式

Q8: 单人模式和热座模式有什么区别？

· 单人模式：你 vs 3 个 AI。
· 热座模式：2~4 名真人玩家在同一台设备轮流操作。回合开始前会提示“请将屏幕转交给下一位玩家”，并自动清屏，保护手牌隐私。

Q9: 如何回放之前的对局？

选择主菜单的 2. 回放录像，会列出 uno/records/ 目录下的所有录像文件。选择任意一场，逐帧播放。若输入路径为空，默认加载 uno/record.json。

Q10: 录制功能怎么开启？

在新游戏流程中，会询问“是否录制本局游戏？” 选 y。游戏结束后录像会自动保存到 uno/records/replay_YYYYMMDD_HHMMSS.json。

---

四、Mod 制作

Q11: 如何创建一个自制赛季？

1. 在 mods/ 目录下创建 .py 文件。
2. 定义必须的常量：
   ```python
   SEASON_ID = "MOD_MY"
   SEASON_NAME = "我的赛季"
   SKILL_CLASSES = [MySkill]
   ```
3. 技能类必须继承 uno.core.Skill 并实现 can_trigger / activate。

详细说明见 mods/HOW_TO_MAKE_A_MOD.md。

Q12: 什么是 RELY_ON？

声明依赖。如果你的 Mod 使用了 S2 的技能，可以写：

```python
RELY_ON = ("S2", "依赖苏秦技能")
```

如果玩家未启用 S2，你的 Mod 会被跳过并提示原因。

Q13: 什么是 REJECT？

声明排斥。如果你的 Mod 与某赛季冲突：

```python
REJECT = {"S1": "机制冲突"}
```

同时启用时，双方都会被阻止加载。

Q14: 什么是 ONLY_TOLERATE？

白名单。如果你的 Mod 只允许与某些赛季共存：

```python
ONLY_TOLERATE = ("S1", "S2")
```

其他赛季会被自动排除。

Q15: Mod 如何添加成就？

在 Mod 文件中定义成就类并放入 ACHIEVEMENTS 列表：

```python
from uno.achievements import Achievement

class MyAchievement(Achievement):
    def __init__(self):
        super().__init__('my_ach', '自定义成就', '描述')
    def check(self, game, events):
        # 分析 events 日志
        return True

ACHIEVEMENTS = [MyAchievement]
```

加载器会自动收集并注册。

---

五、存档与成就

Q16: 我的战绩存在哪里？

存档文件为 uno/archive.txt，采用 Base64 编码的 JSON，防止直接修改。

Q17: 如何手动修改战绩？

用 Python 生成 Base64 字符串：

```python
import json, base64
data = {"你的名字": {"wins": 10, "losses": 2, "achievements": []}}
print(base64.b64encode(json.dumps(data, ensure_ascii=False).encode('utf-8')).decode('ascii'))
```

把输出写入 archive.txt 即可。

Q18: 有哪些成就？

目前包含：

· 一穿三：其他玩家全部淘汰且你未被淘汰，最终获胜。
· 反制大师：单局成功反制 3 次以上。
· 秒杀：前 2 回合内淘汰对手。
· 被遗忘的战术（隐藏）：从未主动抽牌并获胜。

---

六、房间规则

Q19: 如何调整起始手牌数量、技能数量？

启动新游戏时会询问“房间规则设置”：

· 可以选择预设（保存在 uno/presets.json）。
· 也可以自定义：手牌上限（默认 15）、起始手牌（5~10）、初始技能（1~3）。

Q20: 预设保存在哪里？

uno/presets.json，同样是 Base64 编码。

---

七、彩色界面

Q21: 如何启用彩色界面？

启动游戏时询问“是否启用彩色界面？” 选 y 即可。需要安装 rich：

```bash
pip install rich
```

Q22: 彩色界面没生效？

检查是否安装了 rich。如果安装失败，游戏会自动降级到黑白界面。运行：

```bash
python -c "import rich; print(rich.__version__)"
```

---

八、常见错误

Q23: AttributeError: 'UNOGame' object has no attribute 'setup'

说明 core.py 中的 UNOGame 类缺少 setup 方法。请确认你的 core.py 是最新版本。

Q24: Exception: 无牌可抽！

当牌堆和弃牌堆都用尽时会报此错误。通常是某个技能吞牌导致牌池枯竭。已知修复方案：确保所有“覆盖手牌”的技能在覆盖前先弃掉旧手牌。

Q25: AttributeError: 'Player' object has no attribute 'owner'

出现在 _skill_urgency 中，应使用 self 而非 self.owner。请检查你的 core.py 是否已修复。

Q26: TypeError: Deck.reshuffle_from_discard() missing 1 required positional argument

Deck 需要持有弃牌堆引用。创建牌堆时应传入：

```python
self.deck = Deck(self.discard_pile)
```

Q27: 魂迁无限递归怎么办？

魂迁 的 activate 中必须在调用 apply_add_cards 之前设置 self.is_consumed = True。否则转移到自己时会重复触发。

Q28: 鹰眼/读心/显灵泄露了信息？

这些情报类技能的打印应使用 self.owner_print() 而非 print()，确保只有技能拥有者能看到。

---

九、测试

Q29: 如何运行测试？

在项目根目录（src/）下执行：

```bash
python -m unittest tests.test_1_3_3
python -m unittest tests.test_mod_index
```

应输出 Ran xxx tests ... OK。

Q30: 测试失败怎么办？

1. 检查 Player._skill_urgency 是否使用 self。
2. 检查 Deck.__init__ 是否正确接收弃牌堆。
3. 确认 mods/__init__.py 存在。
4. 对照最新版 core.py、achievements.py、skills_uno.py 逐一核对。

---

十、其他

Q31: 为什么电脑的 UNO 提醒会和我的一起显示？

因为 UNO 是公共事件，所有人都应看到。彩色界面下的输出交错是正常现象。

Q32: 我看不到电脑A 被淘汰的提示？

淘汰信息应通过人类玩家的 UI 输出。若使用 NullUI 的电脑玩家直接 print，会被屏蔽。当前版本已通过 human.ui.show(...) 修复。

Q33: 如何添加新的技能而不改核心代码？

1. 创建 mods/my_mod.py。
2. 定义继承自 Skill 的技能类。
3. 放入 SKILL_CLASSES 列表。
4. 启动游戏时输入 1,MOD_MY 即可加载。

Q34: 我可以把 SkillUNO 分享给朋友吗？

可以，直接打包整个项目目录，确保 uno/、main.py、mods/ 完整即可。存档和录像会随游戏目录一起保存。

---

如果你遇到的问题不在本列表中，请提交详细描述（附带报错信息和复现步骤），我们会尽快更新 FAQ。

---