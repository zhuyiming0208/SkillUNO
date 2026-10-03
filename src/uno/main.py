import sys
import os
from uno.core import UNOGame
from uno.archive import show_record
from uno.replay import GameRecorder, GameReplayer
from uno.presets import load_presets, add_preset, get_preset
from uno.ui import ConsoleUI

VERSION = "v1.3.0"

def main():
    print(f"欢迎来到 SkillUNO {VERSION}！")

    # --- 选择游戏模式 ---
    print("\n请选择游戏模式：")
    print("  1. 单人模式（你 vs 3 个 AI）")
    print("  2. 热座模式（2~4 人轮流同屏操作）")
    mode_choice = input("请输入模式编号（默认1）: ").strip()
    if mode_choice == '2':
        hotseat_mode = True
        while True:
            try:
                num_players = int(input("请输入玩家数量（2~4）: ").strip())
                if 2 <= num_players <= 4:
                    break
                else:
                    print("玩家数量必须在 2~4 之间。")
            except ValueError:
                print("请输入有效数字。")
        players = []
        for i in range(num_players):
            default_name = f"玩家{i+1}"
            name = input(f"请输入第{i+1}位玩家的名字（直接回车默认'{default_name}'）: ").strip()
            if not name:
                name = default_name
            players.append(name)
    else:
        hotseat_mode = False
        players = None

        player_name = input("请输入你的名字（直接回车默认'你'）: ").strip()
        if not player_name:
            player_name = "你"
        show_record(player_name)
        print(f"\n你好，{player_name}！")

    # --- 赛季选择 ---
    print("\n可用赛季：")
    print("  官方：1 - 经典赛季 (S1)")
    print("        2 - 被动觉醒赛季 (S2)")
    print("        3 - 同盟赛季(S3)")
    print("        4 - 补丁赛季 (S4)")
    print("  自定义：请将 Mod 放入 mods/ 文件夹，并输入其 SEASON_ID")
    choice = input("请选择赛季组合: ").strip()
    season_map = {'1': 'S1', '2': 'S2', '4': 'S4'}
    enabled_seasons = []
    parts = [p.strip() for p in choice.split(',') if p.strip()]
    for p in parts:
        if p in season_map:
            enabled_seasons.append(season_map[p])
        else:
            enabled_seasons.append(p)
    if not enabled_seasons:
        print("未选择任何赛季，默认启用 S1。")
        enabled_seasons = ['S1']

    # --- 调试模式 ---
    debug_choice = input("是否开启调试模式？(0关闭, 1开启，默认0): ").strip()
    debug = debug_choice == '1'

    # --- 彩色 UI 检查 ---
    try:
        import rich
        rich_available = True
    except ImportError:
        rich_available = False
    if rich_available:
        use_rich = input("是否启用彩色界面？(y/n，默认y): ").strip().lower() != 'n'
    else:
        print("未安装 rich 库，将使用普通界面。安装命令：pip install rich")
        use_rich = False

    # --- 房间规则设置 ---
    print("\n--- 房间规则设置 ---")
    print("请选择设置方式：")
    print("  1. 使用预设")
    print("  2. 自定义")
    print("  3. 默认")
    room_choice = input("请输入编号（默认自定义）: ").strip()
    if room_choice == '1':
        presets = load_presets()
        if not presets:
            print("没有可用的预设，将进入自定义设置。")
            room_choice = '2'
        else:
            print("可用的预设：")
            for i, p in enumerate(presets):
                print(f"  {i}: {p['name']} (手牌上限{p['hand_limit']}, 起始手牌{p['initial_hand_size']}, 初始技能{p['initial_skill_count']})")
            idx = input("请输入预设序号（直接回车使用第一个）: ").strip()
            if idx == '':
                idx = 0
            else:
                try:
                    idx = int(idx)
                    if idx < 0 or idx >= len(presets):
                        raise ValueError
                except:
                    print("无效序号，使用第一个预设。")
                    idx = 0
            preset = presets[idx]
            hand_limit = preset['hand_limit']
            initial_hand_size = preset['initial_hand_size']
            initial_skill_count = preset['initial_skill_count']
    if room_choice == '2':  # 自定义
        while True:
            try:
                hand_limit = int(input("手牌上限（默认15）: ").strip() or 15)
                if hand_limit < 1:
                    print("手牌上限必须大于0。")
                    continue
                break
            except ValueError:
                print("请输入有效数字。")
        while True:
            try:
                initial_hand_size = int(input("起始手牌数量（5~10，默认7）: ").strip() or 7)
                if 5 <= initial_hand_size <= 10:
                    break
                else:
                    print("起始手牌数量必须在5~10之间。")
            except ValueError:
                print("请输入有效数字。")
        while True:
            try:
                initial_skill_count = int(input("初始技能数量（1~3，默认3）: ").strip() or 3)
                if 1 <= initial_skill_count <= 3:
                    break
                else:
                    print("初始技能数量必须在1~3之间。")
            except ValueError:
                print("请输入有效数字。")
        save_choice = input("是否保存为预设？(y/n，默认n): ").strip().lower()
        if save_choice == 'y':
            preset_name = input("预设名称: ").strip()
            if preset_name:
                add_preset(preset_name, hand_limit, initial_hand_size, initial_skill_count)
                print(f"预设 '{preset_name}' 已保存。")
    else: # 默认
        hand_limit = 15
        initial_hand_size = 7
        initial_skill_count = 3
        print(f"""{hand_limit = }
              {initial_hand_size = }
              {initial_skill_count = }""")
    # --- 录制选项 ---
    recorder = None
    rec_choice = input("是否录制本局游戏？(y/n, 默认n): ").strip().lower()
    if rec_choice == 'y':
        recorder = GameRecorder()

    # --- 开始游戏 ---
    if hotseat_mode:
        game = UNOGame(
            enabled_seasons=enabled_seasons,
            debug=debug,
            use_rich_ui=use_rich,
            recorder=recorder,
            players=players,
            hand_limit=hand_limit,
            initial_hand_size=initial_hand_size,
            initial_skill_count=initial_skill_count
        )
    else:
        game = UNOGame(
            player_name,
            enabled_seasons,
            debug=debug,
            use_rich_ui=use_rich,
            recorder=recorder,
            hand_limit=hand_limit,
            initial_hand_size=initial_hand_size,
            initial_skill_count=initial_skill_count
        )
    game.run()

def replay():
    ui = ConsoleUI()
    try:
        replayer = GameReplayer.interactive_choose(ui)
        replayer.replay_all()
    except FileNotFoundError as e:
        ui.show(f"错误：{e}")
    except Exception as e:
        ui.show(f"回放出错：{e}")



def cli():
    print(f"SkillUNO {VERSION}")
    action = input("1. 新游戏  2. 回放录像\n请选择: ").strip()
    if action == '2':
        replay()
    else:
        main()


if __name__ == "__main__":
    cli()
