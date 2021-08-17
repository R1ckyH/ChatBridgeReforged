from cbr.lib.config import Config
from cbr.lib.logger import CBRLogger
from cbr.net.tcpserver import CBRTCPServer


class CBRServer:
    def __init__(self):
        # TODO: permission system(happy lazy)
        self.config = Config()
        self.logger = CBRLogger('CBR', self.config)
        try:
            self.logger.setup()
            self.logger.info(f"CBR is now starting")
            self.config.init_config(self.logger)
            self.tcp_server = CBRTCPServer(self.logger, self.config)
        except ValueError:
            self.logger.bug(exit_now=False, error=True)
            self.logger.warning('Please check config.yml carefully')
            self.logger.info("Exit now")
            exit(0)
        except Exception:
            self.logger.bug(error=True)

    def start(self):
        try:
            self.tcp_server.start()
        except SystemExit:
            self.logger.info("Exit now")
            exit(0)
        except Exception:
            self.logger.bug()
