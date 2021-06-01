from cbr.lib.logger import CBRLogger
from cbr.lib.config import Config, Config_check
from cbr.net.tcpserver import CBRTCPServer

class CBRServer:
    def __init__(self):
        self.config = Config()
        self.logger = CBRLogger('CBR', self.config)
        try:
            self.config_check = Config_check(self.logger, self.config)
            self.tcp_server = CBRTCPServer(self.logger, self.config.data)
            self.tcp_server.start()
        except SystemExit:
            self.logger.debug("EXIT")
            exit(0)
        except:
            self.logger.bug()