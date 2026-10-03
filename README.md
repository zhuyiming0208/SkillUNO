![Python Tests](https://github.com/zhuyiming0208/SkillUNO/actions/workflows/test.yml/badge.svg)

# SkillUNO

一个基于 Python 的 UNO 卡牌游戏框架，支持 Mod 化技能、赛季、成就、回放与热座模式。
(部分代码由 AI 辅助生成)

## 游戏截图

![游戏界面 1](https://cdn.jsdelivr.net/gh/zhuyiming0208/SkillUNO@main/docs/screenshots/gameplay1.jpg)


![游戏界面 2](https://cdn.jsdelivr.net/gh/zhuyiming0208/SkillUNO@main/docs/screenshots/gameplay2.jpg)

## 特性

- 事件驱动的技能系统
- 可自定义赛季与 Mod
- 成就与隐藏成就
- 完整对局回放
- 热座模式（本地多人）
- 可选彩色 UI（基于 rich）

## 快速开始

\`\`\`bash
git clone https://github.com/zhuyiming0208/SkillUNO.git
cd SkillUNO
pip install -e .
skilluno
\`\`\`

如果不安装，也可以直接运行：

\`\`\`bash
PYTHONPATH=src python -m uno.main
\`\`\`

## 文档

- [开发者指南](docs/DEVELOPER_GUIDE.md)
- [FAQ](docs/FAQ.md)
- [从小白到高手](docs/how_to_go_from_a_beginner_to_an_expert.md)
- [版本历史](docs/VersionBriefHistory.md)

## 许可证

MIT
