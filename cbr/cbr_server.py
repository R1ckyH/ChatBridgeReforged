import os
import trio

import cbr
from cbr.lib.compress import CompressManager
from cbr.lib.config import ConfigManager
from cbr.lib.logger import CBRLogger
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
        self.compress_manager = CompressManager(self.logger, "logs")

    async def start(self):
        config = self.config_manager.read()
        self.compress_manager.compress_setup_log(config["log"], config["debug"])
        self.logger.info(f"Version: {cbr.__version__}, Lib version: {cbr.__lib_version__}")
        try:
            tcp_server = CBRTCPServer(self.logger, config)
        except ValueError:
            self.logger.bug()
            self.logger.warning("Please check config.yml carefully")
            self.logger.info("Exit now")
            exit(0)
        except Exception:
            self.logger.bug(exit_now=True)
        async with trio.open_nursery() as root:
            root.start_soon(tcp_server.run)  # type: ignore
            # There can be more services parallelly running
