"""新手引导：交互式教学。

设计：
- 不走 game.run()（会卡人类输入 + 完整对局太久）
- 建真实 UNOGame（S1、3 张手牌、0 技能），演示真实数据
- 手动控制：玩家真实操作 1 次，展示结果
- 全程解说，最后提示完成
"""
from uno.core import UNOGame


def _pause():
    input("\n按回车继续...")


def _show_concept():
    print("\n=== 新手引导 · 基本规则 ===")
    print("SkillUNO 是 UNO 的进阶变体。基本规则：")
    print("  1. 你的回合，必须打出一张与牌堆顶【同色】或【同数字】的牌")
    print("  2. 如果没有可出的牌，直接按回车抽一张")
    print("  3. 手牌清空即获胜")
    print("  4. 手牌超过上限（默认 15 张）会被淘汰")
    _pause()


def _show_skill_intro():
    print("\n=== 技能系统简介 ===")
    print("SkillUNO 的最大特色是【技能】：")
    print("  · 主动技能：自己回合输入 s 可发动")
    print("  · 被动技能：满足条件自动触发（如死亡时复活）")
    print("  · 亡语技能：玩家被淘汰时触发")
    print("  · 混合技能：主动 + 被动兼有")
    print("\n每局开始会随机分配技能，用 help 技能名 可查看详情")
    _pause()


def run_tutorial():
    print("\n" + "=" * 50)
    print(" 欢迎来到新手引导")
    print("=" * 50)

    _show_concept()

    # 真实游戏：S1、3 张手牌、0 技能
    game = UNOGame(
        "新手",
        ["S1"],
        debug=False,
        use_rich_ui=False,
        initial_hand_size=3,
        initial_skill_count=0,
    )
    game.setup()

    me = game.players[0]
    top = game.discard_pile[-1]

    print("\n=== 真实牌局演示 ===")
    print(f"牌堆顶：{top}（有效颜色：{game.current_color}）")
    print("下面就是真实的游戏界面。试着出一张牌吧（或直接回车抽牌）：")
    print()

    idx = me.choose_play(top, game.current_color, game)
    if idx is None:
        drawn = game.deck.draw(1)
        me.hand.append(drawn)
        print(f"\n你抽到了：{drawn}")
    else:
        card = me.hand.pop(idx)
        print(f"\n你打出了：{card}")
        print("在真实游戏里，这张牌的效果会立刻生效。")

    _pause()
    _show_skill_intro()

    print("\n" + "=" * 50)
    print(" 引导结束！你已经掌握了基本玩法。")
    print(" 去挑战真正的 AI 吧！")
    print("=" * 50)


if __name__ == "__main__":
    run_tutorial()
