"""页面栈与路由。"""
from uno.mod_store.render import clear_screen
from uno.mod_store import input_handler as ih


class Action:
    """路由动作常量。"""
    QUIT = "QUIT"
    BACK = "BACK"
    SEARCH = "SEARCH"
    HELP = "HELP"
    DETAIL = "DETAIL"
    HISTORY = "HISTORY"


class Router:
    def __init__(self, mod_index=None):
        self.stack = []
        self.running = True
        self.mod_index = mod_index

    def push(self, page):
        self.stack.append(page)

    def pop(self):
        if self.stack:
            return self.stack.pop()
        return None

    def current(self):
        return self.stack[-1] if self.stack else None

    def run(self):
        """主循环：渲染栈顶 → 读键 → 分发。"""
        try:
            while self.running and self.stack:
                page = self.current()
                clear_screen()
                print(page.render())

                event = ih.read_key()
                if event is None:
                    # 非 TTY 或读键失败，退出
                    break

                result = page.handle_key(event)
                self._dispatch(result)
        except KeyboardInterrupt:
            pass
        finally:
            clear_screen()

    def _dispatch(self, result):
        if result is None:
            return
    
        if isinstance(result, tuple):
            action, payload = result
        else:
            action, payload = result, None

        if action == Action.QUIT:
            self.running = False
            return

        if action == Action.BACK:
            self.pop()
            if not self.stack:
                self.running = False
            return

        if action == Action.SEARCH:
            if self.mod_index is None:
                # 理论上不会到这儿（run_mod_store 会传），
                # 但防御一下，避免静默崩溃
                print("错误：模组索引未初始化，无法搜索。")
                return
            from uno.mod_store.search import SearchPage
            self.push(SearchPage(self.mod_index))
            return

        if action == Action.DETAIL:
            if payload is None:
                return
            from uno.mod_store.detail import DetailPage
            self.push(DetailPage(payload, self.mod_index))
            return

        return