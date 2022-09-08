import os

from cbr.lib.config import ConfigManager
from cbr.lib.logger import CBRLogger
from cbr.lib.zip import Compressor
from cbr.net.tcpserver import CBRTCPServer


class CBRServer:
    def __init__(self):
        # TODO: permission system(happy lazy)
        self.logger = CBRLogger('CBR')
        if not os.path.exists('config'):
            os.mkdir('config')
        if not os.path.exists('plugins'):
            os.mkdir('plugins')
        self.compressor = Compressor(self.logger)
        self.config_checker = ConfigManager(self.logger)
        self.config = self.config_checker.read()
        self.logger.info(f"CBR is now starting at pid {os.getpid()}")
        self.logger.info(f'Version: {self.config.version}, Lib version: {self.config.lib_version}')
        self.logger.debug_config = self.config.debug
        logs_data = self.config.raw_data['log']
        split_log = logs_data['split_log']
        self.compressor.zip_log('latest.log', logs_data['size_to_zip'])
        self.logger.setup(split_log=split_log)
        if split_log:
            self.compressor.zip_log('chat.log', logs_data['size_to_zip_chat'])
            self.logger.setup(True)
        try:
            self.tcp_server = CBRTCPServer(self.logger, self.config)
        except ValueError:
            self.logger.bug()
            self.logger.warning('Please check config.yml carefully')
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
