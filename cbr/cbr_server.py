from cbr.lib.config import Config, ConfigCheck
from cbr.lib.logger import CBRLogger
from cbr.net.tcpserver import CBRTCPServer


class CBRServer:
    def __init__(self):
        self.config = Config()
        self.logger = CBRLogger('CBR', self.config)
        try:
            self.logger.setup()
            self.config_check = ConfigCheck(self.logger, self.config)
            self.tcp_server = CBRTCPServer(self.logger, self.config.data)
        except SystemExit:
            self.logger.debug("EXIT")
            exit(0)
        except Exception:
            self.logger.bug()

    def start(self):
        try:
            self.tcp_server.start()
        except SystemExit:
            self.logger.debug("EXIT")
            exit(0)
        except Exception:
            self.logger.bug()
