import os

import cbr
from cbr.lib.config import ConfigManager
from cbr.lib.logger import CBRLogger
from cbr.lib.zip import Compressor
from cbr.net.tcpserver import CBRTCPServer

CBR_VERSION = "0.3.0-dev003"

logger = CBRLogger('CBR')


def start():
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
    tcp_server = CBRTCPServer(logger, config)
    tcp_server.start()
