from uno.core import UNOGame
from uno.archive import show_record
from uno.replay import GameRecorder, GameReplayer
from uno.ui import ConsoleUI

VERSION = "v1.8.0"

def main():
    print(f"欢迎来到 SkillUNO {VERSION}！")

    # --- 玩家身份 ---
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
        import rich  # noqa: F401
        rich_available = True
    except ImportError:
        rich_available = False

    if rich_available:
        use_rich = input("是否启用彩色界面？(y/n，默认y): ").strip().lower() != 'n'
    else:
        print("未安装 rich 库，将使用普通界面。安装命令：pip install rich")
        use_rich = False

    # --- 开发工具（可注释掉） ---
    # from uno.season1 import PoWanFa, QiaoWu, ChuNeng
    # dev = {
    #     player_name: [PoWanFa, QiaoWu, ChuNeng],
    # }
    # game = UNOGame(player_name, enabled_seasons, debug=debug,
    #                dev_skills=dev, use_rich_ui=use_rich)
    # game.run()
    # return

    # --- 录制选项 ---
    recorder = None
    rec_choice = input("是否录制本局游戏？(y/n, 默认n): ").strip().lower()
    if rec_choice == 'y':
        recorder = GameRecorder()

    # --- 开始游戏 ---
    game = UNOGame(
        player_name,
        enabled_seasons,
        debug=debug,
        use_rich_ui=use_rich,
        recorder=recorder,
    )
    game.run()


def replay():
    """回放模式：列出所有录像文件，选择后逐帧播放。"""
    ui = ConsoleUI()
    try:
        replayer = GameReplayer.interactive_choose(ui)
        replayer.replay_all()
    except FileNotFoundError as e:
        ui.show(f"错误：{e}")
    except Exception as e:
        ui.show(f"回放出错：{e}")


def stats_panel():
    """统计面板。"""
    from uno.stats import StatsPanel
    StatsPanel().show_all()

def mod_store():
    """启动模组商店 CLI（阶段二仅预留入口，未挂到主菜单）。"""
    from uno.mod_store import run_mod_store
    run_mod_store()

def cli():
    while True:
        print(f"\nSkillUNO {VERSION}")
        action = input(
            "1. 新游戏\n"
            "2. 回放录像\n"
            "3. 统计面板\n"
            "4. 模组商店\n"
            "0. 退出\n"
            "请选择: "
        ).strip()
        if action in ('0', 'q'):
            print("再见！")
            break
        elif action == '1':
            main()
        elif action == '2':
            replay()
        elif action == '3':
            stats_panel()
        elif action == '4':
            mod_store()
        # 其他输入 → 回到菜单


if __name__ == "__main__":
    cli()
