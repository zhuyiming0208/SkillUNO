"""打开网页版商店。"""
import webbrowser


WEB_URL = "https://zhuyiming0208.github.io/SkillUNO/"


def open_web_store():
    """尝试打开浏览器访问网页版商店。

    返回 (是否成功, 提示信息)。
    Termux 上没有默认浏览器时 webbrowser.open 会失败或返回 False，
    此时提示用户手动复制链接。
    """
    try:
        opened = webbrowser.open(WEB_URL)
    except Exception:
        opened = False

    if opened:
        return True, f"已在浏览器中打开：{WEB_URL}"
    return False, f"未能自动打开浏览器。请手动访问：\n  {WEB_URL}"
