import threading
import time

from typing import TYPE_CHECKING

from chatbridgereforged_mc.constants import *
if TYPE_CHECKING:
    from chatbridgereforged_mc.lib.logger import CBRLogger
    from chatbridgereforged_mc.net.tcpclient import CBRTCPClient
    from chatbridgereforged_mc.lib.config import Config


class GuardianBase:
    def __init__(self, logger: 'CBRLogger', name=''):
        self.logger = logger
        self.reset = False
        self.end = False
        self.name = name
        self.current = 0

    def start(self):
        threading.Thread(target=self.run, name=f"Restart_Guardian_{self.name}", daemon=True).start()
        self.logger.debug(f"Thread Restart_Guardian_{self.name} started")

    def run(self):
        self.end = False
        self.reset = False
        while not self.end:
            self.wait_restart()

    def stop(self):
        self.end = True
        self.reset = True

    def restart(self):
        self.reset = True
        if self.end:
            self.start()

    def wait_restart(self):
        pass

    def stopwatch(self, sec):
        for self.current in range(sec):
            time.sleep(1)
            if self.reset:
                return False
        return True


class PingGuardian(GuardianBase):
    def __init__(self, client_class: 'CBRTCPClient', logger, config: 'Config'):
        super().__init__(logger, "ping")
        self.client = client_class
        self.config = config

    def wait_restart(self):
        self.logger.debug("keep alive")
        for i in range(self.config.ping_time):
            time.sleep(1)
            if self.end:
                return
        ping_msg = json.dumps({"action": "keepAlive", "type": "ping"})
        if self.client.connected:
            self.client.send_msg(self.client.socket, ping_msg)


class RestartGuardian(GuardianBase):
    def __init__(self, logger, client_class: 'CBRTCPClient'):
        super().__init__(logger, "CBR_client")
        self.client = client_class
        self.wait_time = 0

    def _client_start(self):
        self.logger.debug(f"Try start")
        self.client.try_start(auto_connect=True)

    def get_time_left(self):
        return self.wait_time - self.current

    def wait_restart(self):
        for i in WAIT_TIME:
            self.wait_time = i
            finish = self.stopwatch(i)
            if finish and not self.reset:
                self._client_start()
            else:
                self.logger.debug(f"Auto_restart reset, restart after 5 sec")
                time.sleep(5)
                return
        while not self.end:
            finish = self.stopwatch(3600)
            if finish and not self.reset:
                self._client_start()
            else:
                self.logger.debug(f"Auto_restart reset, restart after 5 sec")
                time.sleep(5)
                return
