import os
from typing import Dict, List

import trio

import cbr
from cbr.lib.client import Client
from cbr.lib.config import ConfigManager
from cbr.lib.logger import CBRLogger
from cbr.lib.typeddicts import TypedClientsConfig
from cbr.lib.zip import Compressor
from cbr.net.tcpserver import CBRTCPServer

CBR_VERSION = "0.3.0-dev005"

logger = CBRLogger('CBR')


def setup_client(config: List[TypedClientsConfig]) -> Dict[str, Client]:
    result: Dict[str, Client] = {}
    for d in config:
        result[d['name']] = Client(d['name'], d['password'])
    return result


async def start():
    # TODO: permission system(happy lazy)
    config_checker = ConfigManager(logger)
    config = config_checker.read()
    log_config = config["log"]
    log_compressor = Compressor(
        logger, "latest.log", log_config["size_to_zip"]
    )
    log_compressor.zip_log()
    if log_config["split_log"]:
        chat_compressor = Compressor(
            logger, "chat.log", log_config["size_to_zip_chat"], "chat_"
        )
        chat_compressor.zip_log()
    logger.setup(config["debug"], split_log=log_config["split_log"])
    logger.info(f"CBR is now starting at pid {os.getpid()}")
    logger.info(f'Version: {CBR_VERSION}, Lib version: {cbr.__version__}')
    clients = setup_client(config["clients"])
    settings = config["server_setting"]
    tcp_server = CBRTCPServer(
        logger,
        settings["host_name"],
        settings["port"],
        settings["aes_key"],
        clients
    )
    async with trio.open_nursery() as root:
        root.start_soon(tcp_server.run)  # type: ignore
        # There can be more services parallelly running
