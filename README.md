![Python Tests](https://github.com/zhuyiming0208/SkillUNO/actions/workflows/test.yml/badge.svg)
![PyPI](https://img.shields.io/pypi/v/skilluno.svg)
![PyPI Downloads](https://img.shields.io/pypi/dm/skilluno.svg)
![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)

# SkillUNO

> 一个基于 Python 的 UNO 卡牌游戏框架，支持 Mod 化技能、赛季、成就、回放、热座模式、CLI 商店与网页版商店。

*(部分代码由 AI 辅助生成)*

---

## 目录

- [游戏截图](#游戏截图)
- [特性](#特性)
- [快速开始](#快速开始)
- [使用方式](#使用方式)
  - [交互式菜单](#交互式菜单)
  - [CLI 子命令](#cli-子命令)
- [模组系统](#模组系统)
  - [安装社区模组](#安装社区模组)
  - [制作自己的模组](#制作自己的模组)
- [网页版商店](#网页版商店)
- [项目结构](#项目结构)
- [开发](#开发)
- [兼容性](#兼容性)
- [文档](#文档)
- [许可证](#许可证)

---

## 游戏截图

![游戏界面 1](https://cdn.jsdelivr.net/gh/zhuyiming0208/SkillUNO@main/docs/screenshots/gameplay1.jpg)

![游戏界面 2](https://cdn.jsdelivr.net/gh/zhuyiming0208/SkillUNO@main/docs/screenshots/gameplay2.jpg)

---

## 特性

| 特性 | 说明 |
|---|---|
| **事件驱动技能系统** | 技能通过订阅游戏事件（GAME_START / TURN_START / BEING_ADDED_CARDS 等）触发，支持自动与手动激活 |
| **赛季系统** | 内置 S1 经典 / S2 被动觉醒 / S3 同盟 / S4 补丁 四个官方赛季，含 30+ 技能 |
| **Mod 化扩展** | 支持社区作者发布自定义赛季与技能，通过 CLI 商店或网页商店安装 |
| **成就系统** | 内置成就 + 隐藏成就，记录在存档中，跨局累计 |
| **完整对局回放** | 每局可录制，支持交互式回放，逐事件查看 |
| **热座模式** | 2~4 人本地轮流同屏操作 |
| **统计面板** | 玩家胜率排行、技能使用次数、牌型频率、对局统计 |
| **可选彩色 UI** | 基于 `rich` 库，未安装时自动降级为纯文本 |
| **CLI 模组商店** | 交互式菜单 + 命令行子命令双入口 |
| **网页版商店** | 深色终端风，支持浏览、搜索、查看详情、一键安装命令 |

---

## 快速开始

### 方式一：可编辑安装（推荐）

```bash
git clone https://github.com/zhuyiming0208/SkillUNO.git
cd SkillUNO
pip install -e .
skilluno
```

方式二：不安装，直接运行

```bash
git clone https://github.com/zhuyiming0208/SkillUNO.git
cd SkillUNO
PYTHONPATH=src python -m uno.main
```

方式三：Termux（Android）

```bash
pkg install python git
git clone https://github.com/zhuyiming0208/SkillUNO.git
cd SkillUNO
pip install -e .
skilluno
```

Termux 提示：软键盘没有方向键，商店内使用 u/d/l/r 代替上下左右，~ 代替 Esc。

---

使用方式

交互式菜单

```bash
skilluno
```

进入主菜单：

```
SkillUNO vX.Y.Z
1. 新游戏
2. 回放录像
3. 统计面板
4. 模组商店
0. 退出
```

· 新游戏：选择赛季组合、房间规则、是否录制
· 回放：从 src/uno/records/ 里选择录像播放
· 统计面板：读取存档与回放，显示胜率排行、技能使用、牌型频率
· 模组商店：浏览、搜索、安装、卸载、启用/禁用模组（按 W 打开网页版）

CLI 子命令

```bash
skilluno mod list                  # 列出全部模组
skilluno mod search <关键词>        # 模糊搜索
skilluno mod info <ID>             # 查看模组详情
skilluno mod install <ID>          # 下载 + 验证 + 启用
skilluno mod uninstall <ID>        # 卸载
skilluno mod list-collections      # 列出模组集
skilluno mod install-collection <ID>   # 一键安装模组集
skilluno mod --help                # 查看帮助
```

---

模组系统

安装社区模组

方式一：CLI 商店

```bash
skilluno
# 选 4 进入商店
# 按 S 搜索、Enter 查看详情、I 安装
```

方式二：命令行

```bash
skilluno mod install EXAMPLE
```

方式三：网页版商店

访问 https://zhuyiming0208.github.io/SkillUNO/ ，复制安装命令。

安全机制

下载的模组经过多重验证：

1. URL 白名单：只允许 raw.githubusercontent.com 和 cdn.jsdelivr.net
2. 大小限制：单文件 ≤ 5MB
3. 静态验证：用 ast.parse 解析 SEASON_ID，绝不 import 执行
4. 隔离区：下载到 mods/_pending/，用户显式确认后才启用
5. 备份：覆盖已安装模组前先备份 .bak

制作自己的模组

见 模组制作指南。

---

网页版商店

网址：https://zhuyiming0208.github.io/SkillUNO/

纯静态 HTML/CSS/JS，无构建依赖。包含：

· 首页：官方模组 + 精选模组 + 模组集
· 列表页：全部模组 + 搜索
· 详情页：模组信息、依赖、权限声明、一键复制安装命令
· 模组集：浏览和批量安装

源码位于 web/ 目录。改完后：

```bash
cd web
python -m http.server 8000
# 浏览器访问 http://localhost:8000
```

---

项目结构

```
SkillUNO/
├── docs/                  项目文档
│   ├── DEVELOPER_GUIDE.md
│   ├── FAQ.md
│   ├── VersionBriefHistory.md
│   └── screenshots/
├── mods/                  模组元数据
│   ├── mod_idx.json       第三方模组索引
│   ├── official.json      官方模组列表
│   ├── S1~S4.json         官方赛季元数据
│   ├── example.json       示例模组
│   └── collections.json   模组集
├── src/uno/               核心代码
│   ├── core.py            游戏核心（牌、玩家、回合、事件）
│   ├── season1~4.py       官方赛季技能
│   ├── skills_uno.py      技能加载器
│   ├── achievements.py    成就系统
│   ├── archive.py         存档读写
│   ├── replay.py          回放录制与播放
│   ├── stats.py           统计面板
│   ├── ui.py              UI 抽象（ConsoleUI / RichUI / NullUI）
│   ├── mod_index.py       模组索引读取
│   └── mod_store/         CLI 模组商店
│       ├── menu.py / search.py / detail.py / history_view.py
│       ├── downloader.py / validator.py
│       ├── uninstaller.py / updater.py
│       └── cli.py         命令行子命令
├── tests/                 测试（700+ 用例）
├── web/                   网页版商店
├── tools/bump.py          版本号升级工具
└── .github/workflows/     CI（测试 + 网页部署）
```

---

开发

运行测试

```bash
python -m pytest tests/ -v
```

带覆盖率：

```bash
python -m pytest tests/ --cov=src/uno --cov-report=term-missing
```

贡献

欢迎提交 Issue 或 PR。添加新功能时请：

1. 保持测试覆盖率
2. 更新 docs/VersionBriefHistory.md
3. 用 setver X.Y.Z 升级版本号

版本号工具

```bash
setver 1.13.0 --new-entry "新功能说明"
```

（setver 是 tools/bump.py 的别名，需自行配置）

---

兼容性

项 支持
Python 3.10 / 3.11 / 3.12 / 3.14
平台 Linux / macOS / Android (Termux) / Windows
可选依赖 rich（彩色 UI）

---

文档

· 开发者指南
· FAQ
· 从小白到高手
· 版本历史
· 模组制作

---

许可证

MIT
