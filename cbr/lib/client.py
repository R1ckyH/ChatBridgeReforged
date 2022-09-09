import trio


class Client:

    def __init__(self, name: str, password: str) -> None:
        self.name = name
        self.password = password
        self.online = False
        self.type = False
        self.stream = None
        self.send_lock = trio.Lock()
        self.ping = None
        self.ping_lock = trio.CancelScope()
        self.cmd_lock = trio.CancelScope()
        self.cmd_result = None
        self.process = None
        self.lib_version = None
