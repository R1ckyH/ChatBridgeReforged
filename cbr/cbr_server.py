import os
import trio

from typing import Dict, List

import cbr
from cbr.lib.compress import CompressManager
from cbr.lib.client import Client
from cbr.lib.config import ConfigManager
from cbr.lib.logger import CBRLogger
from cbr.lib.typeddicts import TypedClientsConfig
from cbr.net.tcpserver import CBRTCPServer


def setup_client(config: List[TypedClientsConfig]) -> Dict[str, Client]:
    result: Dict[str, Client] = {}
    for d in config:
        result[d['name']] = Client(d['name'], d['password'])
    return result


class CBRServer:
    def __init__(self):
        # TODO: permission system(happy lazy)
        self.logger = CBRLogger("CBR")
        self.logger.info(f"CBR is now starting at pid {os.getpid()}")

        if not os.path.exists("config"):
            os.mkdir("config")
        if not os.path.exists('logs'):
            os.mkdir('logs')
        if not os.path.exists("plugins"):
            os.mkdir("plugins")

        self.config_manager = ConfigManager(self.logger)
        self.compress_manager = CompressManager(self.logger, "logs")

    async def start(self):
        try:
            config = self.config_manager.read()
            self.compress_manager.compress_setup_log(config["log"], config["debug"])
            self.logger.info(f"Version: {cbr.__version__}, Lib version: {cbr.__lib_version__}")
            clients = setup_client(config["clients"])
            tcp_server = CBRTCPServer(self.logger, config["server_setting"], clients)
            async with trio.open_nursery() as root:
                root.start_soon(tcp_server.run)  # type: ignore
                # There can be more services parallelly running
        except Exception:
            self.logger.bug(exit_now=True)
