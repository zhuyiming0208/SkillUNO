# SkillUNO 修复摘要 (FixSummary)

本文档记录 SkillUNO 从 v0.1.0 到当前版本的所有版本变更。
ERROR 编号体系自 v1.3.1 起引入。
完整的 API 说明请参阅 docs/DEVELOPER_GUIDE.md。

本文档按版本顺序（由新到旧）记录从 v0.1.0 到 v1.5.0 期间的所有修复内容。每个版本列出该版本修复的 bug、调整的功能及对应的错误编号。

> **当前版本：v1.5.0**（2026-10-06）

---
## v1.6.0（2026-10-07）

本版本完成 **CLI 模组商店阶段三**：浏览与搜索。

### 新增：搜索页 `src/uno/mod_store/search.py`

- 输入框支持退格删除（中文按字符删，不按字节）
- 匹配范围：`ID` / `name` / `author` / `author_github` / `tags`，大小写不敏感
- 结果最多返回 20 条；超过时提示"请细化搜索词"
- 上下键选择结果，`Enter` 进入详情页，`~` 返回输入框，再 `~` 返回首页

### 新增：详情页 `src/uno/mod_store/detail.py`

- 展示基本字段（名称 / 作者 / 版本 / 兼容性 / GitHub / 协议）
- `lacover=null` 显示"任意版本"
- 简介、技能、关系（依赖 / 排斥 / 白名单）、权限声明分区展示
- 空关系显示"无"，空 `needs` 显示"未声明"
- `I` / `R` 返回 `INSTALL` / `VIEW_SOURCE` 指令（阶段四实现）

### 修改：主菜单 `menu.py`

- 精选模组上限从 8 提升到 12
- 超过 12 个时打印警告，只保留前 12 个
- 空状态显示"暂无精选模组"

### 修改：路由 `router.py`

- 支持页面栈传参，`handle_key` 可返回 `(action, payload)` 元组
- `_dispatch` 分发 `SEARCH` / `DETAIL` 动作

### 修改：输入处理 `input_handler.py`

- UTF-8 多字节字符支持（按首字节判断长度补读后续字节）
- 新增 `BACKSPACE` 事件类型（`\x7f` / `\x08`）
- raw 模式下 `Ctrl+C` 显式抛 `KeyboardInterrupt`

### 测试

- 新增 `tests/test_mod_store_search.py`（约 17 个）
- 新增 `tests/test_mod_store_detail.py`（约 19 个）
- 新增 `tests/test_mod_store_menu_limit.py`（6 个）
- 新增 `tests/test_mod_store_coverage.py`（约 45 个，补 router/input/main 覆盖率）
- 全量测试：**396 → 491**，覆盖率 **84%**

---
## v1.5.0（2026-10-06）

本版本新增 **CLI 模组商店框架**（阶段二），为后续的下载、搜索、历史功能搭建终端界面骨架。

### 新增：模组商店包 `src/uno/mod_store/`

| 文件 | 职责 |
|------|------|
| `__init__.py` | 暴露 `run_mod_store` |
| `main.py` | 商店入口；通过 `Path(__file__)` 向上查找 `mods/` |
| `render.py` | 终端渲染：画框、对齐、ANSI 着色、清屏、光标 |
| `input_handler.py` | 键盘输入：单字符键 + 统一 `KeyEvent` |
| `menu.py` | 主菜单：官方模组区 + 精选模组区 + 操作栏 |
| `router.py` | 页面栈与路由；`Action` 常量 |

### 键位方案（Termux/Android 实测）

放弃方向键转义序列（软键盘字节间隔不可靠），改用单字符：

| 键 | 功能 |
|----|------|
| `u` / `d` | 上 / 下 |
| `l` / `r` | 左 / 右 |
| `s` | 搜索 |
| `h` | 帮助 |
| `q` | 退出 |
| `~` | 返回（代替 ESC） |
| `x` | 删除（阶段三预留） |
| `\r` / `\n` / 空格 / `e` | 确认 |

### 渲染特性

- 中文字符按 2 宽度计算（`unicodedata.east_asian_width`）
- ANSI 着色在 `NO_COLOR` / 非 TTY 环境自动降级
- 边框使用 `╔╗╚╝║═`

### 安全与兼容

- 非 TTY 环境（CI）下 `read_key()` 返回 `None`，不会挂
- 终端 `termios` 通过 `try/finally` 保证恢复
- 精选模组超过 8 个时显示"还有 N 个"

### 测试

- 新增 `tests/test_mod_store_render.py`（22 个测试）
- 新增 `tests/test_mod_store_menu.py`（22 个测试）
- 全量测试总数：**351 → 396**

---

## v1.4.0（2026-10-06）

本版本为**功能扩展版本**，聚焦模组生态与数据可视化。

### 新增：模组索引系统

- 新增 `src/uno/mod_index.py`：
  - `ModIndex` 类，读取 `mods/mod_idx.json` 索引与各模组元数据 JSON。
  - 支持 `load_index` / `load_mod` / `get_handpicked` / `get_all` / `search` / `get_official`。
  - 必填字段校验（`ID`、`name`、`description`、`author`、`repo`、`version`、`micover`、`lacover`、`skills`），缺失时打印中文警告并跳过。
  - `OFFICIAL_MODS` 常量硬编码 S1/S2/S4 三个官方赛季。
  - `get_official()` 返回深拷贝，防止外部修改污染常量。
- 新增 `mods/mod_idx.json`：模组索引文件，初始为空。
- 新增 `mods/example.json`：模组元数据模板（仅供作者参考，不参与索引）。
- 支持带/不带 BOM 的 UTF-8 编码（`utf-8-sig`）。

### 新增：统计面板

- 新增 `src/uno/stats.py`：
  - `StatsCollector`：聚合 `archive.txt`（玩家胜率、成就）与 `records/*.json`（技能使用、牌型频率、回合数、胜者分布）。
  - `StatsPanel`：基于 `rich` 的富文本渲染（表格 + 面板），无 `rich` 时自动降级为纯文本。
  - 支持 `show_all` / `show_player_ranking` / `show_skill_usage` / `show_card_stats` / `show_game_stats`。

### 新增：CLI 入口

- `src/uno/main.py` 新增 `cli()` 函数，注册为 `skilluno` console script 入口。
- 主菜单新增「3. 统计面板」选项。
- 通过 `pyproject.toml` 的 `[project.scripts]` 暴露为全局命令。

### 文档更新

- `mods/HOW_TO_MAKE_A_MOD.md` 新增「模组元数据 JSON 格式」章节：
  - 单模组 JSON 字段说明表（必填/可选、类型、说明）。
  - 空值写法（`{}` / `[]` / `null`）。
  - 索引文件 `mod_idx.json` 格式。
  - 自动发现机制（GitHub topic `skilluno-mod` + 仓库根目录 `skilluno_mod.json`）。
  - 第三方模组安全声明。

### 测试

- 新增 `tests/test_mod_index.py`（21 个测试）：
  - 索引读取（成功 / 缺失 / 损坏）。
  - 模组读取（成功 / 缺失 / 缺必填字段 / 损坏）。
  - 列表合并（`handpicked` + `other`）。
  - 搜索（ID 大小写、作者、名称、无匹配、空关键词、空索引）。
  - 官方模组（数量 / ID / 深拷贝）。
- 现有测试保持通过。

### 版本统计

- 测试总数：**328 → 347**
- 总体覆盖率：**81%**

---

## v1.3.3（2026-10-05）

本版本新增统计面板并补充测试。

### 新增：统计面板

- **位置**：`uno/stats.py`，入口 `skilluno` → 菜单 → 3
- **功能**：
  - 玩家胜率排行（读 `archive.txt`）
  - 技能使用次数（聚合所有 `records/replay_*.json`）
  - 牌型出现频率
  - 对局统计（总局数、回合数、胜者分布）
- **降级**：未安装 rich 时自动切换为普通文本表格

### 其他

- 补充测试用例至 328 个，覆盖率 ~81%
- 文件结构调整：`main.py` 移入 `src/uno/`

---

## v1.3.2（2026-09-12）

本版本修复了 2 个高危逻辑问题。

### ERROR-021：`run()` 淘汰分支记录 `winner='?'`

- **位置**：`uno/core.py` → `UNOGame.run`（单机模式淘汰分支）
- **问题**：
  1. `winner` 被硬编码为 `'?'`，但此刻必然存在至少一名存活 AI 玩家。
  2. 成就系统若依赖 `game_end` 事件的 `winner` 字段进行判定，会因 `'?'` 而无法正确评估。
  3. 回放文件中的 `game_end` 事件也会写入 `'?'`，导致回放分析工具无法识别实际赢家。
- **修复**：
  ```python
  survivors = [p for p in self.players if not p.eliminated]
  winner_name = survivors[0].name if survivors else '?'
  self.record_event('game_end', winner=winner_name)
```

· 严重程度：🟡 中

ERROR-022：热座模式不写存档

· 位置：uno/core.py → UNOGame._end_hotseat_game
· 问题：
  1. _end_hotseat_game 只做广播和事件记录，没有调用 update_record。
  2. 热座模式下所有玩家的胜负场次都不会被写入 archive.txt。
  3. 由于热座模式为多人聚会而设计，战绩不保存等于该模式的核心价值缺失。
· 修复：
  ```python
  for p in self.players:
      if not p.is_human:
          continue
      update_record(p.name, p == winner, [])
      show_record(p.name)
  ```
  当前版本暂不评估成就，只记录胜负。按玩家分别评估成就列为 v1.4.0 待办。
· 严重程度：🔴 高

---

v1.3.1（2026-08-25）

本版本进行了大规模核心重构，暗更新了 ERROR-001 ~ ERROR-020，涉及 UI 解耦、逻辑修复、架构清理等多个层面。

ERROR-001：Player.eliminate 硬编码玩家0 的 UI

· 位置：uno/core.py → Player.eliminate
· 问题：任何玩家被淘汰时，都通过 game.players[0].ui 显示信息。
· 修复：改用 game.broadcast(...)，向所有可见 UI 广播。
· 严重程度：🔴 高

ERROR-002：Deck.reshuffle_from_discard 残留 print

· 位置：uno/core.py → Deck.reshuffle_from_discard
· 问题：Deck 直接调用 print，绕过 UI 抽象层。
· 修复：Deck.__init__ 接收 ui 参数，_notify 方法走 UI 通道。
· 严重程度：🟡 中

ERROR-003：SkillManager.trigger 残留 print

· 位置：uno/core.py → SkillManager.trigger
· 问题：调试输出直接 print，RichUI 模式下格式不一致。
· 修复：改为 self.game.ui.show(...)。
· 严重程度：🟡 中

ERROR-004：SkillManager._query_counters 残留 print

· 位置：uno/core.py → SkillManager._query_counters
· 问题：反制信息通过 print 输出，绕过 UI 层。
· 修复：改为 player.ui.show(...)。
· 严重程度：🔴 高

ERROR-005：UNOGame.setup 残留 print

· 位置：uno/core.py → UNOGame.setup
· 问题：起始牌、重翻牌信息通过 print，绕过 UI。
· 修复：改为 self.ui.show(...)。
· 严重程度：🟡 中

ERROR-006：UNOGame.apply_add_cards 残留 print

· 位置：uno/core.py → UNOGame.apply_add_cards
· 问题：加牌通知通过 print，绕过 UI。
· 修复：改为 self.broadcast(...)。
· 严重程度：🟡 中

ERROR-007：UNOGame.show_hand_colors 残留 print

· 位置：uno/core.py → UNOGame.show_hand_colors
· 问题：调试信息直接 print。
· 修复：改为 self.ui.show(...)。
· 严重程度：🟢 低

ERROR-008：热座清屏绕过 UI 抽象

· 位置：uno/core.py → Player.human_choose
· 问题：直接调用 input() 和 os.system('cls')，绕过 UI 层。
· 修复：新增 ConsoleUI.pause() 和 ConsoleUI.clear_screen()，调用走抽象。
· 严重程度：🔴 高

ERROR-009：run() 重复检查代码

· 位置：uno/core.py → UNOGame.run
· 问题：play_turn() 之后与循环顶部的检查完全重复。
· 修复：删除 play_turn() 之后的检查，让循环自然回到顶部。
· 严重程度：🟢 低

ERROR-010：CORE_ACHIEVEMENTS.copy() 浅拷贝

· 位置：uno/core.py → UNOGame.__init__
· 问题：浅拷贝导致多个游戏实例共享成就对象，可能互相污染状态。
· 修复：引入工厂函数 get_core_achievements()，每次返回全新实例列表。
· 严重程度：🟡 中

ERROR-011：record_event 与 recorder.record 不同步

· 位置：uno/core.py → UNOGame.record_event
· 问题：record_event 只写入 event_log（成就系统），未写入 recorder（回放）。
· 修复：record_event 内部同时调用 recorder.record。
· 严重程度：🟡 中

ERROR-012：Deck.draw() 返回值类型不一致

· 位置：uno/core.py → Deck.draw
· 问题：draw(1) 返回单张 Card，draw(2) 返回 List[Card]，调用方容易出错。
· 修复：新增 draw_one() 与 draw_many(count) 明确返回类型。
· 严重程度：🟡 中

ERROR-013：reshuffle_from_discard 异常未处理

· 位置：uno/core.py → UNOGame.apply_add_cards
· 问题：牌堆和弃牌堆同时耗尽时抛出异常导致游戏崩溃。
· 修复：apply_add_cards 捕获异常并优雅降级（广播提示）。
· 严重程度：🔴 高

ERROR-014：_skill_urgency 硬编码技能名

· 位置：uno/core.py → Player._skill_urgency
· 问题：AI 只认识 S1/S2/S4 的特定技能名，无法评估 Mod 新技能。
· 修复：新增 Skill.urgency_weight 属性与 Skill.evaluate_urgency(game) 方法。
· 严重程度：🟡 中

ERROR-015：apply_add_cards 硬编码玩家0 的 UI

· 位置：uno/core.py → UNOGame.apply_add_cards
· 问题：加牌通知通过 players[0].ui 显示，语义错误。
· 修复：新增 UNOGame.broadcast() 方法，向所有可见 UI 广播。
· 严重程度：🟡 中

ERROR-016：热座模式只检查玩家0 的淘汰

· 位置：uno/core.py → UNOGame.run
· 问题：热座模式下仅检查 players[0] 的淘汰状态，其他玩家淘汰不会结束游戏。
· 修复：热座模式下遍历所有存活玩家，len(active) <= 1 才结束。
· 严重程度：🔴 高

ERROR-017：update_record 在 run() 中重复调用

· 位置：uno/core.py → UNOGame.run
· 问题：胜利分支中 update_record 被调用两次（第一次没带成就）。
· 修复：删除第一次调用，只保留带 achievements 的那次。
· 严重程度：🟢 低

ERROR-018：CORE_ACHIEVEMENTS 共享状态

· 位置：uno/core.py 顶部导入
· 问题：CORE_ACHIEVEMENTS 是模块级列表，多个游戏实例共享成就对象。
· 修复：同 ERROR-010，改用工厂函数。
· 严重程度：🟡 中

ERROR-019：human_ui / ai_ui 文档缺失

· 位置：DEVELOPER_GUIDE.md
· 问题：UNOGame.__init__ 支持 human_ui 与 ai_ui 参数，但未在开发者文档中说明用途和默认值。
· 修复：
  · 在开发者文档第四章「UI 系统」中新增 4.2 小节「UI 参数」。
  · 详细说明 human_ui / ai_ui 的类型、默认值、优先级规则与使用示例。
· 严重程度：🟢 低

ERROR-020：RichUI 的 ui.console 直接调用

· 位置：uno/core.py → Player.human_choose、UNOGame.play_turn
· 问题：直接访问 ui.console.print(...)，绕过 UI 抽象。
· 修复：
  · 在 ConsoleUI 和 RichUI 中新增统一的 print_inline(text, end='') 方法。
  · 所有直接 ui.console.print(...) 调用替换为 ui.print_inline(...)。
· 严重程度：🟡 中

---

v1.3.0（2026-08-23）

新增：自定义房间规则

· 支持开局前调整手牌上限、起始手牌数量、初始技能数量。
· 新增 uno/presets.py 用于管理房间预设，支持 Base64 编码保存。
· 可在启动时选择预设或自定义，并将自定义配置保存为预设。

新增：预设管理 API

· load_presets()：读取所有预设。
· add_preset(name, hand_limit, initial_hand_size, initial_skill_count)：添加或更新预设。
· get_preset(name)：按名称获取预设。

---

v1.2.1（2026-08-18）

修复：常规 bug 清理

· 修复热座模式下的部分 UI 提示错误。
· 优化了回合流转逻辑中冗余的分支处理。

---

v1.2.0（2026-08-16）

新增：热座模式

· 在 main.py 中允许玩家选择「单人模式」或「热座模式」。
· 热座模式下支持 2~4 名真人玩家轮流在同一屏幕上操作。
· 游戏会提示「请将屏幕转交给下一位玩家」并清空输入缓冲区。
· 通过 players 参数传入玩家名单，所有玩家均为人类。

新增：UI 参数解耦

· UNOGame.__init__ 新增 human_ui 与 ai_ui 参数。
· 人类玩家 UI 与 AI 玩家 UI 可分别传入，实现完全自定义。

---

v1.1.2（2026-08-16）

修复：UI 最终解耦

· 修复了 UI 层的最后一批评 print 残留。
· 确认所有输出通道统一走 UI 抽象。

---

v1.1.1（2026-08-15）

修复：已知 bug 清理

· 修复成就判定中事件日志顺序问题。
· 修复部分技能在极端条件下未正确记录事件的问题。

---

v1.1.0（2026-08-15）

新增：成就系统

· 新增 uno/achievements.py，包含成就基类与成就管理器。
· 引入 4 个核心成就：
  · 一穿三：其他玩家全部淘汰且你未被淘汰，最终获胜。
  · 反制大师：单局成功反制 3 次以上。
  · 秒杀：前 2 回合内淘汰对手。
  · 被遗忘的战术（隐藏）：从未主动抽牌并获胜。

新增：存档支持成就

· archive.py 支持 achievements 字段。
· show_record 显示玩家已获得的成就列表。

新增：Mod 可添加成就

· 赛季文件可定义 ACHIEVEMENTS 列表，加载器自动收集并注册。

---

v1.0.0（2026-08-13）

首个正式版本

· 核心引擎稳定，UI 解耦完成，事件系统、技能系统、组合技系统全部就绪。
· 引入 S1、S2、S4 三个赛季，共 31 张技能。
· 支持彩色 UI（RichUI）、调试模式、Mod 加载。

---

v0.9.1（2026-08-13）

修复：所有已知 bug

· 修复依赖检查中的遗漏边界情况。
· 修复 S2 技能被动在开局触发顺序问题。

---

v0.9.0（2026-08-13）

新增：依赖 / 冲突 / 仅容忍系统

· RELY_ON：声明依赖的赛季或 Mod，缺失时自动跳过并提示。
· REJECT：声明排斥目标，双方同时启用时都加载失败。
· ONLY_TOLERATE：白名单机制，仅允许与指定赛季共存。

修复：一对多排斥处理

· 支持 A 同时排斥 B、C 的情况，全部标记为失败。

修复：多对多排斥处理

· 支持链式排斥，统一收集后处理。

---

v0.8.1（2026-08-12）

修复：已知 bug

· 修复回放文件在某些事件后未正确刷新的问题。

---

v0.8.0（2026-08-12）

新增：对局回放与标记

· 游戏自动记录完整事件序列，保存为 JSON 到 uno/records/。
· 提供 GameReplayer 支持逐帧回放。
· 支持对局文件的多文件管理与选择。

---

v0.7.1（2026-08-12）

修复：双重冒号、UNO 幽灵

· 修复 RichUI 下输入提示出现双重冒号的问题。
· 修复 UNO 提醒误报（手牌不为 1 时也提示）。

---

v0.7.0（2026-08-12）

新增：可选富文本 UI

· 引入 RichUI 类，基于 rich 库实现彩色界面。
· 卡牌颜色映射、技能状态区分、回合标题、UNO 提醒彩色化。
· 未安装 rich 时自动降级为 ConsoleUI。

---

v0.6.6（2026-08-12）

新增：play_turn 方法

· 将回合流程封装到独立方法中，便于维护与扩展。

---

v0.6.5（2026-08-12）

修复：人类玩家信息泄露

· 鹰眼、读心、显灵等情报类技能改为仅拥有者可见（owner_print）。

---

v0.6.4（2026-08-12）

微调：ConsoleUI

· 增加 pause、clear_screen 等辅助方法。

---

v0.6.3（2026-08-12）

修复：已知 bug

· 修复技能反制链中部分场景下的顺序问题。

---

v0.6.2（2026-08-12）

新增：add_multiplier 与 skill_activation_name

· BEING_ADDED_CARDS / CARDS_ADDED 事件新增 add_multiplier。
· SKILL_ACTIVATED 事件新增 skill_activation_name。

---

v0.6.1（2026-08-12）

重构：组合技系统

· 移除核心引擎中硬编码的苏秦 & 张仪组合技。
· 引入 ComboBase 抽象基类，Mod 可自定义组合技。
· Skill 新增 combo_partners 与 combo_effect 属性。

---

v0.6.0（2026-08-12）

重构：UI 解耦

· 引入 ConsoleUI 与 NullUI。
· Player 不再直接处理输入输出，改由 ui 属性驱动。
· AI 玩家使用 NullUI 静默。

---

v0.5.5（2026-08-09）

恢复：Base64 编码

· 从自制编码系统回退至 Base64，稳定可靠。

---

v0.5.4（2026-08-08）

尝试：自制编码系统（已回退）

· 实验性质，后于 v0.5.5 回退。

---

v0.5.3（2026-08-08）

新增：单元测试

· 首次引入 tests/ 测试套件。

---

v0.5.2（2026-08-08）

修复：已知 bug

· 修复部分技能在边界条件下的行为。

---

v0.5.1（2026-08-07）

调整：删除联机功能，S3 回归空盒

· 因复杂度原因，暂时移除联机模块。
· S3 同盟赛季回归占位状态。

---

v0.5.0（2026-08-06）

新增：Base64 存档、玩家 ID 统一

· 战绩保存至 uno/archive.txt，Base64 编码。
· 玩家可自定义 ID。
· 首次尝试联机功能（后于 v0.5.1 移除）。

---

v0.4.1（2026-08-03）

新增：支持输入自制 Mod 名字

· 赛季选择时可直接输入 Mod 的 SEASON_ID。

---

v0.4.0（2026-08-03）

新增：mods/ 文件夹，支持 Mod 制作

· 玩家可在 mods/ 下放置 .py 文件，定义自定义赛季。
· 提供 mods/HOW_TO_MAKE_A_MOD.md 指南。

---

v0.3.3（2026-08-02）

修复：魂迁无限递归

· HunQian 在转移加牌前先标记已消耗，防止转移给自己时重复触发。

---

v0.3.2（2026-08-01）

增强：调试模式

· 调试输出显示事件触发、技能状态、手牌颜色分布。

---

v0.3.1（2026-08-01）

新增：赛季组合选择，技能加载器

· main.py 支持逗号分隔的赛季组合。
· 引入 SkillLoader 动态导入赛季模块。

---

v0.3.0（2026-08-01）

新增：S2、S4 实装

· 8 张 S2 技能：始皇帝、苏秦、张仪、双生花、金身、鹰眼、孤勇者、忘忧。
· 8 张 S4 技能：赝品、探囊、显灵、嫁祸、激发、业力、夺心魄、魂迁。

新增：双生花、苏秦 & 张仪组合技

· 双生花被动可重掷骰子/转盘。
· 苏秦 & 张仪可发动「合纵连横·骰子审判」。

---

v0.2.1（2026-07-29）

修复：加牌、牌堆重洗、浓烟、惊雷等

· 修复 +2/+4 跳过错误玩家的 bug。
· 修复牌堆重洗时「无牌可抽」异常。
· 浓烟显示已用状态，开局自动触发。
· 惊雷改为全体玩家依次掷骰子（≥5 免罚）。
· 车同轨后同步当前颜色。

新增：UNO 提醒、对手手牌数显示、帮助引导

---

v0.2.0（2026-07-28）

新增：事件驱动框架，S1 15 张技能

· 引入 GameEvent、SkillManager、Skill 基类。
· 实装 S1 全部 15 张技能。
· 技能消耗、反制（破万法/储能）逻辑。
· 修复技能重复触发 bug（离析、储能守卫）。

---

v0.1.1（2026-07-26）

新增：核心模块

· 添加 core.py、skills_uno.py 等基础文件。

---

v0.1.0（2026-07-26）

首个可运行版本

· 简易 UNO 框架。
· 手牌上限 15 张，达到 16 张立即淘汰。
· 1 人类玩家 + 3 电脑 AI。

---

后续版本计划

编号 描述 计划版本
TODO-001 成就按玩家分别评估（热座模式） v1.4.0+
TODO-002 AI 战术增强（考虑对手手牌数、技能状态） v1.4.0+
TODO-003 统计面板 v1.5.0
TODO-004 随机赛季 待定
TODO-005 固定种子及每日任务 待定
TODO-006 联机模式 待定

---

修复验证

所有修复均已通过 tests/test_all.py 的单元测试套件验证。当前共 30 个测试，涵盖：

· 卡牌逻辑（同色、同数字、万能牌）
· 牌堆管理（大小、抽牌、重洗）
· 玩家状态（手牌上限、技能显示）
· 技能管理器（自动触发、人类拦截）
· 游戏流程（全 AI 对局、加牌倍数、开发技能覆写）
· 加载器（依赖、排斥、容忍）
· 成就系统（全部 4 个成就 + 管理器）
· 回放系统（录制、保存、读取）
· 自定义房间规则
· 热座模式创建

运行方式：

```bash
python -m unittest tests.test_1_3_3
python -m unittest tests.test_mod_index
```

预期输出：Ran xxx tests in ... OK。

---

最后更新：2026-10-06 · v1.4.0
