# 更新日志 (Changelog)

本项目的所有重要变更都将记录在此文件中。
格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/)。
版本号遵循 [语义化版本 (Semantic Versioning)](https://semver.org/lang/zh-CN/)。

错误编号（ERROR-xxx）体系自 v1.3.1 起引入，用于追踪核心引擎的架构重构与历史 Bug 修复。
完整的 API 说明请参阅 [DEVELOPER_GUIDE.md](docs/DEVELOPER_GUIDE.md)。

---

## [Unreleased]

**重构文档**
**重构测试**
**把自动发现模组优化了一下**

---

## [v1.22.1] - 2026-11-13

### 用户视角
- 新增全屏 TUI 的鼠标点击交互，现在可以直接点击手牌和技能按钮出牌了。
- 优化了 TUI 体验，抽牌确认、选颜色、选技能全部支持按键化，不再弹输入框。

### 开发者视角
#### Added
- 补全技能按钮：绿色按钮显示所有可用主动技能，点击即发动。
- 帮助按钮：点击输出 UNO 帮助文本。
- 名字/赛季按钮化：默认名字与常用赛季按钮，自定义仍走输入框。

#### Changed
- 手牌改 `grid 4 列` 布局，15 张手牌自动换行不溢出。
- 按键化交互：`y/n` 确认、按 `0-3` 选颜色、按数字选技能。

---

## [v1.22.0] - 2026-11-13

### 用户视角
- 迎来了 TUI 阶段 3，支持全屏鼠标点击出牌。

### 开发者视角
#### Added
- 新增结构化 Action 协议（`PlayCardAction` / `DrawCardAction` / `QuitGameAction`）。
- `TextualUI` 渲染手牌按钮，可点击出牌，不可出的牌置灰。
- TUI 底部增加抽牌按钮与退出按钮。

#### Fixed
- 修复输入框焦点问题，用 `set_focus` 替代 `focus`。

#### Changed
- `core.py` 的 `choose_play` 支持 Action 分流，`ConsoleUI` 返回 `None` 走原流程零破坏。
- `pyproject.toml` 加 `package-data`，彩蛋 `archive.txt` 进 wheel。

---

## [v1.21.0] - 2026-11-07

### 用户视角
- TUI 阶段 2，支持全屏查看游戏日志和实时战况。

### 开发者视角
#### Added
- 新增全屏 `GameScreen`，日志实时滚动展示。
- 实现基于 `threading.Event` 的跨线程安全输入桥接。
- `Header` 动态显示当前回合玩家。
- 赛季输入增加白名单校验，非法输入红字提示。

#### Changed
- 去掉 `Header` 默认 icon 与 `Footer` palette 提示。
- `SystemExit` 兜底，`q` 退出时优雅回主菜单。

---

## [v1.20.1] - 2026-11-04

### 用户视角
- 优化了 TUI 菜单布局与视觉比例，适配大屏平板。

### 开发者视角
#### Changed
- 调整菜单卡片为响应式宽度。
- 按钮改为舒展比例，去掉突兀的边框。
- 优化排版间距与分割线。

---

## [v1.20.0] - 2026-11-04

### 用户视角
- 迎来了全新的 Textual 全屏 TUI 菜单，支持鼠标点击。

### 开发者视角
#### Added
- 新增可选依赖 `tui = [textual, rich]`。
- 新增 `textual_ui.py`，实现全屏主菜单。
- 新增 5 个 TUI 测试（渲染 + 点击回传 + 降级）。

#### Changed
- `src/uno/ui.py` 重构为 `ui` 包。
- `skilluno tui` 子命令启动，选新游戏后降级 `ConsoleUI`。

---

## [v1.19.2] - 2026-11-04

### 用户视角
- 修复了线上技能图鉴显示为空列表的问题。

### 开发者视角
#### Fixed
- `deploy-web.yml` 增加 `pip install -e .`，确保 CI 有依赖。
- `export_skills.py` 官方赛季导入失败时 `raise`，不再静默返回空。
- `export_skills.py` 导出 0 技能时 `sys.exit(1)`。
- `index.html` 区分数据为空与加载失败。

#### Changed
- `ui.py` 的 `rich` 改为可选 `import`，`UNOGame` 自动降级 `ConsoleUI`。
- `pyproject.toml` 的 `rich` 移至 `optional-dependencies`。
- `README` 补充 `pip install skilluno[rich]` 说明。

---

## [v1.19.1] - 2026-11-04

### 用户视角
- 修复了 v1.19.0 的发布挂起问题。

### 开发者视角
#### Fixed
- 修复 CI 构建环境异常导致的 PyPI 发布中断。

---

## [v1.19.0] - 2026-11-04

### 用户视角
- 新增交互式新手引导模式，再也不用担心不会玩了。
- 网页端新增了技能图鉴页面。

### 开发者视角
#### Added
- 新增交互式新手引导模式。
- 新增网页端技能图鉴页面与导出脚本。
- 5 个页面加技能图鉴导航入口。
- `deploy-web.yml` 自动导出技能数据。

---

## [v1.18.3] - 2026-11-03

### 用户视角
- 补齐了热座模式入口，现在可以和朋友们在同一个设备上轮流玩了。

### 开发者视角
#### Added
- `main.py` 增加游戏模式选择（单人/热座）。
- 热座支持 2~4 人，`@` 复用初始名字，重名报错重问。
- 新增 10 个测试（辅助函数 8 个 + `main` 集成 2 个）。

#### Changed
- 热座模式跳过 `show_record` 和 AI 难度选择。

---

## [v1.18.2] - 2026-10-31

### 用户视角
- 修复了在开启彩色界面时，选择“地狱难度”导致游戏崩溃的严重问题。

### 开发者视角
#### Fixed
- 修复 MCTS 在 `RichUI` 下的深拷贝崩溃：`RichConsole` 包含 `RLock` 导致 `deepcopy` 异常。
- 给 `Deck` / `Player` / `UNOGame` 加 `__deepcopy__`，跳过 `ui` / `recorder`。
- 新增 `test_mcts_with_rich_ui` 回归测试。

---

## [v1.18.1] - 2026-10-31

### 用户视角
- 调整了 AI 测试环境，使其更符合真实的单挑强度。

### 开发者视角
#### Changed
- `ab_test` 默认切至 `m3` 模式。
- 避免 2v2 联盟效应误导胜率数据，默认改为 1 MCTS vs 3 Heuristic。

---

## [v1.18.0] - 2026-10-31

### 用户视角
- 新增了极其强大的“地狱难度 AI（MCTS 算法）”，开局前可以选择 AI 难度了。

### 开发者视角
#### Added
- 新增 `MctsAI`（`max_time=1.0`, `max_iterations=100`）。
- POMDP 随机发牌推断 + `HeuristicAI` rollout 防递归。
- `ConsoleUI`/`NullUI` 新增 `show_error` 方法。
- 新增 7 个 MCTS 单元测试。
- `tools/ab_test.py` 支持 `mh`/`m3` 模式，1v3 胜率 70%。

#### Changed
- 主菜单增加 1/2/3 难度选择，地狱难度有红字警告。

---

## [v1.17.0] - 2026-10-30

### 用户视角
- 电脑 AI 变聪明了！它们现在学会留牌和卡下家了。

### 开发者视角
#### Added
- 新增启发式 AI `HeuristicAI`，实现留牌、卡下家、防守选色策略。
- 新增 7 个启发式单元测试。
- 新增 `tools/ab_test.py` 对局脚本，2000 局胜率 58.8%（比 SimpleAI 高 8.8 个百分点）。

---

## [v1.16.2] - 2026-10-30

### 用户视角
- 优化了 AI 底层架构，为后续的高级 AI 打下基础。

### 开发者视角
#### Changed
- 提取 AI 策略模式框架，抽离 `SimpleAI`。
- 新增 `src/uno/ai/` 模块（`base.py` / `simple.py`）。
- `Player` 支持 `ai_strategy` 注入，默认 `SimpleAI`。
- `UNOGame` 支持 `ai_strategy` 参数透传。
- 新增 7 个框架测试。

---

## [v1.16.1] - 2026-10-24

### 用户视角
- 重构了项目文档，使阅读体验更佳。

### 开发者视角
#### Changed
- 史诗级文档重构与发版路径修复。
- 将版本历史迁移至根目录 `CHANGELOG.md` 并规范格式。
- 修复 `bump.py` 中的旧路径引用与失效正则。
- 更新 `README.md` 链接指向 `CHANGELOG.md`。
- `Developer Guide` 补充自动发现机制小节，清理 `docs` 目录死链。

---

## [v1.16.0] - 2026-10-24

### 用户视角
- 网页版商店支持按标签筛选了。

### 开发者视角
#### Added
- 新增标签栏与响应式布局。
- 标签与搜索框支持联动筛选。
- 标签状态写入 URL 持久化。
- 新增 3 个静态完整性检查。

---

## [v1.15.3] - 2026-10-24

### 用户视角
- 网页端模组列表页新增了侧边栏标签筛选。

### 开发者视角
#### Added
- `mods` 列表页新增标签侧边栏，移动端折叠为顶部横向滚动。
- `search.js` 新增 `extractTags` / `filterByTag`。

#### Changed
- 标签筛选与关键词搜索联动，URL 支持 `?tag=` 参数。

---

## [v1.15.2] - 2026-10-23

### 用户视角
- 修复了模组商店里第三方模组无法显示的问题。

### 开发者视角
#### Fixed
- 菜单增加 `other` 列表渲染。
- 修复潜在路径问题。
- 4 个测试 `Fake` 类补 `get_other`。

---

## [v1.15.1] - 2026-10-23

### 用户视角
- 优化了下载器的报错提示。

### 开发者视角
#### Fixed
- 修正 workflow PR 标题日期。
- 细化 `_try_download` 的 `OSError` 捕获与报错语义。
- 新增 2 个网络 fallback 测试。

---

## [v1.15.0] - 2026-10-19

### 用户视角
- 模组系统迎来重大更新，原生支持“主动+被动”混合技能。

### 开发者视角
#### Added
- 新增 `SkillType.HYBRID`。
- `trigger` 与主动技能判定纳入 `HYBRID`。
- 新增 3 个 `HYBRID` 测试。
- 文档新增 3.2.1 混合技能小节。

---

## [v1.14.0] - 2026-10-18

### 用户视角
- 模组商店接入了自动发现机制，社区模组可以自动上架了。

### 开发者视角
#### Added
- 新增 `tools/discover_mods.py`：每日扫描 `skilluno-mod` topic 并重建 `other` 列表。
- 新增 `.github/workflows/discover-mods.yml`：结果以 PR 提交人工审核。
- 新增 `tests/test_discover_mods.py`（12 个 mock 测试）。
- 更新 `mods/HOW_TO_MAKE_A_MOD.md` 自动发现章节。

#### Changed
- `other` 完全重建，失效仓库自动移除（不删官方、不删 `handpicked`）。

---

## [v1.13.0] - 2026-10-17

### 用户视角
- 修复了 CI 上传旧版本文件导致发布失败的问题。

### 开发者视角
#### Changed
- 改用 PyPI Trusted Publishing。

---

## [v1.12.2] - 2026-10-17

### 用户视角
- 修复了 CLI 子命令失效的问题。

### 开发者视角
#### Fixed
- `pyproject.toml` 的 `skilluno` 入口从 `uno.main:cli` 改为 `uno.main:cli_entry`。
- 修复前：`skilluno mod list` 等子命令全部失效，会进入交互菜单。
- 影响版本：v1.12.1（PyPI 上已发布，已弃用）。

---

## [v1.12.1] - 2026-10-16

### 用户视角
- 商店主菜单可以按 `W` 打开网页版商店了。

### 开发者视角
#### Added
- 商店主菜单按 `W` → 打开网页版商店 URL。
- `web_open.py`：`webbrowser.open` 失败时打印 URL 供手动访问。
- 新增 7 个测试，总数 737 → 744。

---

## [v1.12.0] - 2026-10-16

### 用户视角
- 网页版商店视觉体验全面升级，适配手机、平板和桌面。

### 开发者视角
#### Added
- **404 页面**（`web/404.html`）。
- **favicon**（`web/favicon.svg`）。
- **页脚**：统一 GitHub / 制作模组链接。
- **Meta 信息**：`description` / `theme-color` / `og` 标签。

#### Changed
- **终端风视觉统一**：卡片边框、按钮 `[ 文字 ]` 样式、标题 `> ` 前缀。
- **响应式布局**：桌面 3 列 / 平板 2 列 / 手机 1 列。
- **加载动画**：`正在加载...` 三点循环。
- **状态提示统一**：错误/空状态样式。
- **移动端触摸优化**：可点击元素最小 44px，输入框字号 16px。

---

## [v1.11.0] - 2026-10-16

### 用户视角
- 新增了 `skilluno mod` 命令行接口，不用进交互菜单也能装模组了。

### 开发者视角
#### Added
- **`skilluno mod` 子命令**（`src/uno/mod_store/cli.py`）：支持 `list`、`search`、`info`、`install`、`uninstall`、`list-collections`、`install-collection`。
- **`cli_entry()`**：根据 `argv` 分发，有 `mod` 走 CLI，无则走交互菜单（向后兼容）。
- 新增 28 个测试，总数 708 → 736。

#### Changed
- `ModIndex.get_by_id` 支持查询官方模组（从 `official.json` 读取）。
- 修正官方模组顺序（S1/S2/S3/S4）。

---

## [v1.10.2] - 2026-10-16

### 用户视角
- 网页版商店新增了“模组集”，可以一键安装组合包了。

### 开发者视角
#### Added
- **模组集列表页**（`web/collections/index.html`）。
- **模组集详情页**（`web/collections/detail.html`）。
- **模组集数据**（`mods/collections.json`）：含"新手推荐包"和"被动觉醒精选"。
- **首页模组集分区**：显示前 3 个模组集。
- **部署 workflow**：复制 `collections.json` 到 `web/collections/`。

#### Fixed
- `collections/index.html` 补齐 `render.js` 引用（`escapeHtml` 未定义）。
- 本地开发服务器改用禁缓存策略。

---

## [v1.10.1] - 2026-10-16

### 用户视角
- 网页版商店新增了列表页和实时搜索功能。

### 开发者视角
#### Added
- **模组列表页**（`web/mods/index.html`）：显示所有模组（`handpicked` + `other`）。
- **搜索功能**（`web/assets/js/search.js`）：实时过滤，匹配 ID / name / author / author_github / tags，大小写不敏感，输入防抖 200ms。
- **URL 持久化**：搜索词写入 `?q=...`，刷新不丢。
- **空状态处理**：无结果、加载失败均有友好提示。

---

## [v1.10.0] - 2026-10-15

### 用户视角
- 网页版商店（首页）正式上线！

### 开发者视角
#### Added
- **`web/` 目录**：纯原生 HTML/CSS/JS 的网页版模组商店。
  - `index.html`：首页。
  - `assets/css/main.css`：深色 + 等宽字体 + 霓虹色风格。
  - `assets/js/api.js`：数据源用 `jsDelivr`，避免 `raw.githubusercontent.com` 国内不稳定。
  - `assets/js/render.js`：模组卡片和列表渲染。
  - `.nojekyll`：告诉 GitHub Pages 不用 `Jekyll` 处理。
- **GitHub Pages 部署**：`.github/workflows/deploy-web.yml`（push 自动部署，支持手动触发）。

### 未完成
- 模组列表页、详情页、模组集页（阶段二~四）。
- CLI 侧 `skilluno mod install` 命令。

---

## [v1.9.0] - 2026-10-07

### 用户视角
- 模组商店支持更新检查、卸载、启用切换以及一键安装模组集了。

### 开发者视角
#### Added
- **更新检查**：对比已安装模组的本地版本与索引最新版本，MainMenu 缓存更新结果，状态标记优先级 ↑ > ✓ > ○，按 U 更新。
- **卸载**：`D` 键触发，清理 `mods/{ID}.py` 和 `mods/_pending/{ID}.py`，从 `disabled` 列表移除。
- **启用/禁用切换**：`E` 键触发，`mods/enabled.json` 只存 `disabled` 列表。
- **模组集**：一键安装多个模组，失败继续下一个，验证失败的文件保留在 `_pending/`。
- **`src/uno/paths.py`**：统一的 `mods` 目录查找。
- **`src/uno/enabled.py`**：启用状态管理。

#### Changed
- `skills_uno.load_skills()` 兼容改造：新增 `mods_dir` / `enabled_path` 参数，默认 `None` 走旧逻辑。
- `UNOGame.__init__` 加 `enabled_path=None`，游戏核心跳过 `disabled` 列表里的模组。
- 新增 67 个测试，总数 630 → 697。

---

## [v1.8.0] - 2026-10-07

### 用户视角
- 新增历史记录功能，下载前会提示之前是否下过。

### 开发者视角
#### Added
- **历史记录系统**：记录下载、启用、保留、卸载操作。存储于 `mods/history.json`，最多保留 500 条，界面显示最近 50 条，原子写入（先写 `.tmp` 再 `os.replace`）。
- **历史页**：商店按 H 进入。
- **下载前历史提示**：确认页显示"之前下载过该模组"。
- **`ModIndex.get_by_id()`**：按 ID 查模组元数据。
- 新增 44 个测试，总数 586 → 630。

#### Fixed / 改进
- `presets.json` 移除版本控制追踪。
- `.gitignore` 修正 `_pending/` 规则。
- 测试文件 `test_all.py` / `test_1_3_3.py` 统一改名为 `test_core.py`。

---

## [v1.7.0] - 2026-10-07

### 用户视角
- 模组商店支持一键下载并安装了，且加入了严格的安全校验。

### 开发者视角
#### Added
- **模组下载**：从 GitHub 下载 `.py` 到 `mods/_pending/`。
  - URL 白名单（`raw.githubusercontent.com`、`cdn.jsdelivr.net`）。
  - 5MB 大小限制、10 秒超时、User-Agent、分支 fallback。
- **静态验证**（`validator.py`）：用 `ast.parse()` 解析 `SEASON_ID`，**绝不 `import` 执行**，单文件 500KB 上限。
- **确认页 / 启用页**：用户显式按 Y 才下载 / 启用。
- **覆盖备份**：已安装同 ID 时先备份 `.bak`，成功后删除，失败时恢复。
- 新增 88 个测试，总数 498 → 586。

### 安全约束
- 下载文件绝不直接进 `mods/`，只进 `mods/_pending/`。
- 重定向直接拒绝（不追踪）。
- 所有下载测试用 mock，CI 不联网。

---

## [v1.6.1] - 2026-10-07

### 用户视角
- 修复了搜索框无法输入包含命令字母的 Bug。

### 开发者视角
#### Fixed
- **现象**：搜索页输入 `example` 只显示 `amp`。
- **根因**：`_map_char` 把字母无条件映射为命令，`e/x/l/r/u/d/s/h/q` 被吞。
- **修复**：引入 `raw_input` 模式，搜索页输入状态跳过命令映射。
- **改动**：
  - `input_handler.read_key(raw_input=False)` / `_map_char(ch, raw_input=False)`
  - `router.run()` 按页面 `wants_raw_input()` 决定是否走 raw
  - `search.SearchPage.wants_raw_input()`：输入状态返回 `True`
- 新增 7 个 `raw_input` 模式测试，总数 491 → 498。

---

## [v1.6.0] - 2026-10-07

### 用户视角
- 模组商店新增搜索页面和模组详情页。

### 开发者视角
#### Added
- **搜索页 `src/uno/mod_store/search.py`**：输入框支持退格删除，匹配范围包括 `ID` / `name` / `author` / `author_github` / `tags`，结果最多返回 20 条。
- **详情页 `src/uno/mod_store/detail.py`**：展示基本字段、简介、技能、关系、权限声明。`lacover=null` 显示"任意版本"。
- **主菜单 `menu.py`**：精选模组上限从 8 提升到 12，超过 12 个时打印警告。
- **路由 `router.py`**：支持页面栈传参。
- **输入处理 `input_handler.py`**：UTF-8 多字节字符支持，新增 `BACKSPACE` 事件，`raw` 模式下 `Ctrl+C` 抛 `KeyboardInterrupt`。
- 全量测试：**396 → 491**，覆盖率 **84%**。

---

## [v1.5.0] - 2026-10-06

### 用户视角
- 模组商店的框架搭建完毕，虽然还不能下载，但可以进去看了。

### 开发者视角
#### Added
- **模组商店包 `src/uno/mod_store/`**：包含 `__init__.py`, `main.py`, `render.py`, `input_handler.py`, `menu.py`, `router.py`。
- **键位方案**：放弃方向键转义序列，改用单字符 `u/d/l/r` 移动，`~` 返回，回车/空格确认。
- **渲染特性**：中文字符按 2 宽度计算（`unicodedata.east_asian_width`），ANSI 着色在非 TTY 环境自动降级，边框使用 `╔╗╚╝║═`。
- 新增 44 个测试，全量测试总数：**351 → 396**。

---

## [v1.4.0] - 2026-10-06

### 用户视角
- 新增了统计面板，可以看到胜率和出牌数据啦！

### 开发者视角
#### Added
- **模组索引系统**：新增 `src/uno/mod_index.py`，支持读取索引、加载模组、搜索、获取官方模组等。
- **统计面板**：新增 `src/uno/stats.py`，聚合 `archive.txt` 与 `records/*.json`，基于 `rich` 渲染表格。
- **CLI 入口**：`src/uno/main.py` 新增 `cli()` 函数，通过 `pyproject.toml` 暴露为全局命令。
- **文档更新**：`mods/HOW_TO_MAKE_A_MOD.md` 新增「模组元数据 JSON 格式」章节。
- 测试总数：**328 → 347**，总体覆盖率：**81%**。

---

## [v1.3.3] - 2026-10-05

### 用户视角
- 修复了一些 bug。

### 开发者视角
#### Added
- 新增统计面板（`uno/stats.py`）。

#### Changed
- 补充测试用例至 328 个，覆盖率 ~81%。
- 文件结构调整：`main.py` 移入 `src/uno/`。

---

## [v1.3.2] - 2026-09-12

### 用户视角
- 修复了单机模式淘汰后无法正确记录赢家，以及热座模式不写存档的 2 个问题。

### 开发者视角
#### Fixed
- **ERROR-021**: `run()` 淘汰分支记录 `winner='?'`。
  - **修复**：遍历存活玩家获取真实 `winner_name`，写入 `record_event`。
- **ERROR-022**: 热座模式不写存档。
  - **修复**：在 `_end_hotseat_game` 中遍历所有人类玩家调用 `update_record`。

---

## [v1.3.1] - 2026-08-25

### 用户视角
- 修复了一些 bug。

### 开发者视角
#### Fixed
- 本版本进行了大规模核心重构，暗更新了 **ERROR-001 ~ ERROR-020**，涉及 UI 解耦、逻辑修复、架构清理等多个层面。
- **核心修复**：
  - 解决 `Player.eliminate` / `apply_add_cards` 硬编码玩家 0 的 UI 问题，改用 `game.broadcast(...)`。
  - 清除了 `Deck` / `SkillManager` / `UNOGame` 中残留的 `print`，统一走 UI 通道。
  - 修复了 `input()` 绕过 UI 层、重复检查代码、浅拷贝导致成就对象污染等问题。
  - 新增 `Skill.urgency_weight` 与 `evaluate_urgency(game)` 等底层接口。
  - 补齐了开发者文档中的 `human_ui` / `ai_ui` 说明。

---

## [v1.3.0] - 2026-08-23

### 用户视角
- 新增自定义房间规则，可以调整手牌上限和初始技能数了。

### 开发者视角
#### Added
- 新增 `uno/presets.py` 用于管理房间预设，支持 Base64 编码保存。
- 新增预设管理 API：`load_presets()` / `add_preset()` / `get_preset()`。

---

## [v1.2.1] - 2026-08-18

### 用户视角
- 修复了一些 bug。

### 开发者视角
#### Fixed
- 修复热座模式下的部分 UI 提示错误。
- 优化了回合流转逻辑中冗余的分支处理。

---

## [v1.2.0] - 2026-08-16

### 用户视角
- 新增热座模式，支持 2~4 人在同一屏幕上轮流操作。

### 开发者视角
#### Added
- `main.py` 允许选择「单人模式」或「热座模式」。
- 通过 `players` 参数传入玩家名单，所有玩家均为人类。
- `UNOGame.__init__` 新增 `human_ui` 与 `ai_ui` 参数，实现 UI 完全自定义。

---

## [v1.1.2] - 2026-08-16

### 用户视角
- 优化了底层输出，为后续功能做准备。

### 开发者视角
#### Fixed
- 修复了 UI 层的最后一批 `print` 残留，确认所有输出通道统一走 UI 抽象。

---

## [v1.1.1] - 2026-08-15

### 用户视角
- 修复了一些 bug。

### 开发者视角
#### Fixed
- 修复成就判定中事件日志顺序问题。
- 修复部分技能在极端条件下未正确记录事件的问题。

---

## [v1.1.0] - 2026-08-15

### 用户视角
- 新增成就系统，并支持 Mod 自定义成就。

### 开发者视角
#### Added
- 新增 `uno/achievements.py`，包含成就基类与成就管理器。
- 引入 4 个核心成就（一穿三、反制大师、秒杀、被遗忘的战术）。
- `archive.py` 支持 `achievements` 字段，`show_record` 显示成就列表。
- 赛季文件可定义 `ACHIEVEMENTS` 列表，加载器自动收集并注册。

---

## [v1.0.0] - 2026-08-13

### 用户视角
- 首个正式版本发布！支持多个赛季、彩色界面与 Mod 加载。

### 开发者视角
#### Added
- 核心引擎稳定，UI 解耦完成，事件系统、技能系统、组合技系统全部就绪。
- 引入 S1、S2、S4 三个赛季，共 31 张技能。
- 支持彩色 UI（`RichUI`）、调试模式、Mod 加载。

---

## [v0.9.1] - 2026-08-13

### 用户视角
- 修复了一些 bug。

### 开发者视角
#### Fixed
- 修复依赖检查中的遗漏边界情况。
- 修复 S2 技能被动在开局触发顺序问题。

---

## [v0.9.0] - 2026-08-13

### 用户视角
- 新增依赖、冲突与容忍系统，Mod 兼容性更好了。

### 开发者视角
#### Added
- `RELY_ON`：声明依赖，缺失时自动跳过并提示。
- `REJECT`：声明排斥目标，双方同时启用时都加载失败。
- `ONLY_TOLERATE`：白名单机制，仅允许与指定赛季共存。

#### Fixed
- 修复了一对多排斥处理（支持 A 同时排斥 B、C）。
- 修复了多对多排斥处理（支持链式排斥）。

---

## [v0.8.1] - 2026-08-12

### 用户视角
- 修复了已知 bug。

### 开发者视角
#### Fixed
已知 bug
- 修复回放文件在某些事件后未正确刷新的问题。

---

## [v0.8.0] - 2026-08-12

### 用户视角
- 我们加入了回放功能。

### 开发者视角
#### Added
对局回放与标记
- 游戏自动记录完整事件序列，保存为 JSON 到 `uno/records/`。
- 提供 `GameReplayer` 支持逐帧回放。
- 支持对局文件的多文件管理与选择。

---

## [v0.7.1] - 2026-08-12

### 用户视角
- 我们修复了一些 bug。

### 开发者视角
#### Fixed
双重冒号、UNO 幽灵
- 修复 `RichUI` 下输入提示出现双重冒号的问题。
- 修复 UNO 提醒误报（手牌不为 1 时也提示）。

---

## [v0.7.0] - 2026-08-12

### 用户视角
- 加入了富文本。

### 开发者视角
#### Added
可选富文本 UI
- 引入 `RichUI` 类，基于 `rich` 库实现彩色界面。
- 卡牌颜色映射、技能状态区分、回合标题、UNO 提醒彩色化。
- 未安装 `rich` 时自动降级为 `ConsoleUI`。

---

## [v0.6.6] - 2026-08-12

### 用户视角
- 我们改进了一下游戏核心。

### 开发者视角
#### Added
`play_turn` 方法
- 将回合流程封装到独立方法中，便于维护与扩展。

---

## [v0.6.5] - 2026-08-12

### 用户视角
- 修复了一些 bug。

### 开发者视角
#### Fixed
人类玩家信息泄露
- 鹰眼、读心、显灵等情报类技能改为仅拥有者可见（`owner_print`）。

---

## [v0.6.4] - 2026-08-12

### 用户视角
- 我们改进了 UI。

### 开发者视角
#### Changed
微调：`ConsoleUI`
- 增加 `pause`、`clear_screen` 等辅助方法。

---

## [v0.6.3] - 2026-08-12

### 用户视角
- 修复了一些 bug。

### 开发者视角
#### Fixed
已知 bug
- 修复技能反制链中部分场景下的顺序问题。

---

## [v0.6.2] - 2026-08-12

### 用户视角
- 我们给模组增加了更多自由度 (¯▽¯)👍。

### 开发者视角
#### Added
`add_multiplier` 与 `skill_activation_name`
- `BEING_ADDED_CARDS` / `CARDS_ADDED` 事件新增 `add_multiplier`。
- `SKILL_ACTIVATED` 事件新增 `skill_activation_name`。

---

## [v0.6.1] - 2026-08-12

### 用户视角
- 我们重构了一下组合技。

### 开发者视角
#### Changed
组合技系统
- 移除核心引擎中硬编码的苏秦 & 张仪组合技。
- 引入 `ComboBase` 抽象基类，Mod 可自定义组合技。
- `Skill` 新增 `combo_partners` 与 `combo_effect` 属性。

---

## [v0.6.0] - 2026-08-12

### 用户视角
- 我们重构了一下 UI。

### 开发者视角
#### Changed
UI 解耦
- 引入 `ConsoleUI` 与 `NullUI`。
- `Player` 不再直接处理输入输出，改由 `ui` 属性驱动。
- AI 玩家使用 `NullUI` 静默。

---

## [v0.5.5] - 2026-08-09

### 用户视角
- 自制编码 拜拜 👋。

### 开发者视角
#### Changed
恢复：Base64 编码
- 从自制编码系统回退至 Base64，稳定可靠。

---

## [v0.5.4] - 2026-08-08

### 用户视角
- 自制编码——启动 🎉。

### 开发者视角
#### Added
自制编码系统（已回退）
- 实验性质，后于 v0.5.5 回退。

---

## [v0.5.3] - 2026-08-08

### 用户视角
- 我们加了点小测试。

### 开发者视角
#### Added
单元测试
- 首次引入 `tests/` 测试套件。

---

## [v0.5.2] - 2026-08-08

### 用户视角
- 修复了已知 bug。

### 开发者视角
#### Fixed
已知 bug
- 修复部分技能在边界条件下的行为。

---

## [v0.5.1] - 2026-08-07

### 用户视角
- 我们和联机功能说拜拜了 👋。

### 开发者视角
#### Changed
删除联机功能，S3 回归空盒
- 因复杂度原因，暂时移除联机模块。
- S3 同盟赛季回归占位状态。

---

## [v0.5.0] - 2026-08-06

### 用户视角
- 现在可以保存存档了。
- 联机功能开发中……

### 开发者视角
#### Added
Base64 存档、玩家 ID 统一
- 战绩保存至 `uno/archive.txt`，Base64 编码。
- 玩家可自定义 ID。
- 首次尝试联机功能（后于 `v0.5.1` 移除）。

---

## [v0.4.1] - 2026-08-03

### 用户视角
- 现在可以导入模组了。

### 开发者视角
#### Added
支持输入自制 Mod 名字
- 赛季选择时可直接输入 Mod 的 `SEASON_ID`。

---

## [v0.4.0] - 2026-08-03

### 用户视角
- 现在可以制作 mod 了。
- 在 mods 文件夹下增加了一个 [指南](mods/HOW_TO_MAKE_A_MOD.md)。

### 开发者视角
#### Added
`mods/` 文件夹，支持 Mod 制作
- 玩家可在 `mods/` 下放置 `.py` 文件，定义自定义赛季。
- 提供 `mods/HOW_TO_MAKE_A_MOD.md` 指南。

---

## [v0.3.3] - 2026-08-02

### 用户视角
- 修复了一些 bug。

### 开发者视角
#### Fixed
魂迁无限递归
- `HunQian` 在转移加牌前先标记已消耗，防止转移给自己时重复触发。

---

## [v0.3.2] - 2026-08-01

### 用户视角
- 增加了调试模式。

### 开发者视角
#### Changed
调试模式
- 调试输出显示事件触发、技能状态、手牌颜色分布。

---

## [v0.3.1] - 2026-08-01

### 用户视角
- 现在可以选择多个赛季。
- 现在可以动态导入赛季模块了。

### 开发者视角
#### Added
赛季组合选择，技能加载器
- `main.py` 支持逗号分隔的赛季组合。
- 引入 `SkillLoader` 动态导入赛季模块。

---

## [v0.3.0] - 2026-08-01

### 用户视角
- 增加了 16 张技能 (S2+S3+S4)。
- 增加了组合技 (`苏秦` 和 `张仪`)。

### 开发者视角
#### Added
S2、S4 实装
- 8 张 S2 技能：始皇帝、苏秦、张仪、双生花、金身、鹰眼、孤勇者、忘忧。
- 8 张 S4 技能：赝品、探囊、显灵、嫁祸、激发、业力、夺心魄、魂迁。

双生花、苏秦 & 张仪组合技
- 双生花被动可重掷骰子/转盘。
- 苏秦 & 张仪可发动「合纵连横- 骰子审判」。

---

## [v0.2.1] - 2026-07-29

### 用户视角
- 加上了 UNO 时的提醒。
- 加上了对手手牌数的显示。
- 增加了帮助引导。
- 修复了一些 bug。

### 开发者视角
#### Added
UNO 提醒、对手手牌数显示、帮助引导

#### Fixed
加牌、牌堆重洗、浓烟、惊雷等
- 修复 +2/+4 跳过错误玩家的 bug。
- 修复牌堆重洗时「无牌可抽」异常。
- 浓烟显示已用状态，开局自动触发。
- 惊雷改为全体玩家依次掷骰子（≥5 免罚）。
- 车同轨后同步当前颜色。

---

## [v0.2.0] - 2026-07-28

### 用户视角
- 增加了 15 个技能 (S1)。
- 修复了一些 bug。

### 开发者视角
#### Added
事件驱动框架，S1 15 张技能
- 引入 `GameEvent`、`SkillManager`、`Skill` 基类。
- 实装 S1 全部 15 张技能。
- 技能消耗、反制（破万法/储能）逻辑。

#### Fixed
- 修复技能重复触发 bug（离析、储能守卫）。

---

## [v0.1.1] - 2026-07-26

### 用户视角
- 项目初始化，添加了核心基础代码。

### 开发者视角
#### Added
核心模块
- 添加 `core.py`、`skills_uno.py` 等基础文件。

---

## [v0.1.0] - 2026-07-26

### 用户视角
- 发布了首个可运行版本。

### 开发者视角
#### Added
- 简易 UNO 框架。
- 手牌上限 15 张，达到 16 张立即淘汰。
- 1 人类玩家 + 3 电脑 AI。

---

## 路线图 (Roadmap)

| 编号 | 描述 | 状态 / 计划版本 |
|---|---|---|
| TODO-001 | 成就按玩家分别评估（热座模式） | 已完成 |
| TODO-002 | AI 战术增强（考虑对手手牌数、技能状态） | 待定 |
| TODO-003 | 统计面板 | 已于 v1.3.3 完成 |
| TODO-004 | 随机赛季 | 待定 |
| TODO-005 | 固定种子及每日任务 | 待定 |
| TODO-006 | 联机模式 | 待定 |
| TODO-007 | 支持主动+被动混合技能 (HYBRID) | 已于 v1.15.0 完成 |
| TODO-008 | 自动发现社区模组机制 | 已于 v1.14.0 完成 |

---
*注：完整的测试与验证信息，请查看项目根目录下的 `tests/` 文件夹及 CI 状态。*

[Unreleased]: https://github.com/zhuyiming0208/SkillUNO/compare/v1.22.1...HEAD
[v1.22.1]: https://github.com/zhuyiming0208/SkillUNO/compare/v1.22.0...v1.22.1
[v1.22.0]: https://github.com/zhuyiming0208/SkillUNO/compare/v1.21.0...v1.22.0
[v1.21.0]: https://github.com/zhuyiming0208/SkillUNO/compare/v1.20.1...v1.21.0
[v1.20.1]: https://github.com/zhuyiming0208/SkillUNO/compare/v1.20.0...v1.20.1
[v1.20.0]: https://github.com/zhuyiming0208/SkillUNO/compare/v1.19.2...v1.20.0
[v1.19.2]: https://github.com/zhuyiming0208/SkillUNO/compare/v1.19.1...v1.19.2
[v1.19.1]: https://github.com/zhuyiming0208/SkillUNO/compare/v1.19.0...v1.19.1
[v1.19.0]: https://github.com/zhuyiming0208/SkillUNO/compare/v1.18.3...v1.19.0
[v1.18.3]: https://github.com/zhuyiming0208/SkillUNO/compare/v1.18.2...v1.18.3
[v1.18.2]: https://github.com/zhuyiming0208/SkillUNO/compare/v1.18.1...v1.18.2
[v1.18.1]: https://github.com/zhuyiming0208/SkillUNO/compare/v1.18.0...v1.18.1
[v1.18.0]: https://github.com/zhuyiming0208/SkillUNO/compare/v1.17.0...v1.18.0
[v1.17.0]: https://github.com/zhuyiming0208/SkillUNO/compare/v1.16.2...v1.17.0
[v1.16.2]: https://github.com/zhuyiming0208/SkillUNO/compare/v1.16.1...v1.16.2
[v1.16.1]: https://github.com/zhuyiming0208/SkillUNO/compare/v1.16.0...v1.16.1
[v1.16.0]: https://github.com/zhuyiming0208/SkillUNO/compare/v1.15.3...v1.16.0
[v1.15.3]: https://github.com/zhuyiming0208/SkillUNO/compare/v1.15.2...v1.15.3
[v1.15.2]: https://github.com/zhuyiming0208/SkillUNO/compare/v1.15.1...v1.15.2
[v1.15.1]: https://github.com/zhuyiming0208/SkillUNO/compare/v1.15.0...v1.15.1
[v1.15.0]: https://github.com/zhuyiming0208/SkillUNO/compare/v1.14.0...v1.15.0
[v1.14.0]: https://github.com/zhuyiming0208/SkillUNO/compare/v1.13.0...v1.14.0
[v1.13.0]: https://github.com/zhuyiming0208/SkillUNO/compare/v1.12.2...v1.13.0
[v1.12.2]: https://github.com/zhuyiming0208/SkillUNO/compare/v1.12.1...v1.12.2
[v1.12.1]: https://github.com/zhuyiming0208/SkillUNO/compare/v1.12.0...v1.12.1
[v1.12.0]: https://github.com/zhuyiming0208/SkillUNO/compare/v1.11.0...v1.12.0

`再之前的就没有保存了……`
