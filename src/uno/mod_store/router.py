"""页面栈与路由。"""
from uno.mod_store.render import clear_screen
from uno.mod_store import input_handler as ih


class Action:
    """路由动作常量。

    页面 handle_key() 返回：
      - None：继续当前页面
      - Action.QUIT：退出商店
      - Action.BACK：返回上一页
      - 其他 Action.* 或字符串：跳转到对应页面（阶段三实现）
    """
    QUIT = "QUIT"
    BACK = "BACK"
    SEARCH = "SEARCH"
    HELP = "HELP"
    DETAIL = "DETAIL"
    HISTORY = "HISTORY"


class Router:
    def __init__(self):
        self.stack = []
        self.running = True

    def push(self, page):
        self.stack.append(page)

    def pop(self):
        if self.stack:
            return self.stack.pop()
        return None

    def current(self):
        return self.stack[-1] if self.stack else None

    def run(self):
        """主循环：渲染栈顶页面 → 读键 → 分发。"""
        try:
            while self.running and self.stack:
                page = self.current()
                clear_screen()
                print(page.render())

                event = ih.read_key()
                if event is None:
                    # 非 TTY 或读键失败，退出循环（避免 CI 挂）
                    break

                if event.type == ih.EventType.QUIT:
                    self.running = False
                    break

                result = page.handle_key(event)
                self._dispatch(result)
        except KeyboardInterrupt:
            # Ctrl+C 优雅退出
            pass
        finally:
            clear_screen()

    def _dispatch(self, action):
        if action is None:
            return
        if action == Action.QUIT:
            self.running = False
            return
        if action == Action.BACK:
            self.pop()
            return
        # 其他动作（SEARCH / DETAIL / HISTORY / HELP）
        # 阶段三实现对应页面；本阶段仅做占位。
        # 简单提示后继续。
        # 不 print 消息，避免污染渲染。
        return