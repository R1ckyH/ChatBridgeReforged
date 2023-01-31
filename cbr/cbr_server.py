import os

import cbr
from cbr.lib.config import ConfigManager
from cbr.lib.logger import CBRLogger
from cbr.lib.zip import Compressor
from cbr.net.tcpserver import CBRTCPServer


class CBRServer:
    def __init__(self):
        # TODO: permission system(happy lazy)
        self.logger = CBRLogger("CBR")
        self.logger.info(f"CBR is now starting at pid {os.getpid()}")

        if not os.path.exists("config"):
            os.mkdir("config")
        if not os.path.exists("plugins"):
            os.mkdir("plugins")

        self.config_manager = ConfigManager(self.logger)
        self.config = self.config_manager.read()
        self.logger.debug_config = self.config.debug
        self.logger.info(f"Version: {cbr.__version__}, Lib version: {cbr.__lib_version__}")

        self.compressor = Compressor(self.logger)
        self.compressor.zip_log("latest.log", self.config.log["size_to_zip"])

        split_log = self.config.log["split_log"]
        self.logger.setup(split_log=split_log)
        if split_log:
            self.compressor.zip_log("chat.log", self.config.log["size_to_zip_chat"])
            self.logger.setup(True)

        try:
            self.tcp_server = CBRTCPServer(self.logger, self.config)
        except ValueError:
            self.logger.bug()
            self.logger.warning("Please check config.yml carefully")
            self.logger.info("Exit now")
            exit(0)
        except Exception:
            self.logger.bug(exit_now=True)

    def start(self):
        try:
            self.tcp_server.start()
        except SystemExit:
            self.logger.info("Exit now")
            exit(0)
        except Exception:
            self.logger.bug(exit_now=True)
