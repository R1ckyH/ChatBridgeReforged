"""
config here
"""
import os
import json

from chatbridgereforged_mc.lib.logger import CBRLogger
from chatbridgereforged_mc.resources import *


class AdvancedConfig:
    def __init__(self, logger: CBRLogger, server=None):
        self.logger = logger
        self.server: PluginServerInterface = server
        self.advanced_path = ADVANCED_CONFIG_PATH
        self.debug_mode = DEFAULT_ADVANCED_CONFIG['debug_mode']
        self.config_path = DEFAULT_ADVANCED_CONFIG['config_path']
        self.log_path = DEFAULT_ADVANCED_CONFIG['log_path']
        self.client_color = DEFAULT_ADVANCED_CONFIG['client_color']
        self.ping_time = DEFAULT_ADVANCED_CONFIG['ping_time']
        self.timeout = DEFAULT_ADVANCED_CONFIG['timeout']

    def load_advanced_config(self):
        if self.server is not None:
            with self.server.open_bundled_file(self.advanced_path) as config_file:
                data = dict(json.load(config_file))
        else:
            if not os.path.exists(self.advanced_path):
                os.makedirs(os.path.dirname(self.advanced_path), exist_ok=True)
                self.logger.error('Config not find')
                raise FileNotFoundError("Advanced_config not find")
            with open(self.advanced_path, 'r', encoding='utf-8') as config_file:
                data = dict(json.load(config_file))
        for keys in DEFAULT_ADVANCED_CONFIG.keys():
            if keys not in data.keys():
                self.logger.error(f"Config {keys} not found, use default value {DEFAULT_ADVANCED_CONFIG[keys]}")
                data.update({keys: DEFAULT_ADVANCED_CONFIG[keys]})
        return data

    def init_advanced_config(self):
        config_dict = self.load_advanced_config()
        self.debug_mode = config_dict['debug_mode']
        self.config_path = config_dict['config_path']
        self.log_path = config_dict['log_path']
        self.client_color = config_dict['client_color']
        self.ping_time = config_dict['ping_time']
        self.timeout = config_dict['timeout']


class Config(AdvancedConfig):
    def __init__(self, logger: CBRLogger, server=None):
        super().__init__(logger, server)
        self.logger = logger
        self.server: PluginServerInterface = server
        self.name = DEFAULT_CONFIG['name']
        self.password = DEFAULT_CONFIG['password']
        self.host_name = DEFAULT_CONFIG['host_name']
        self.host_port = DEFAULT_CONFIG['host_port']
        self.aes_key = DEFAULT_CONFIG['aes_key']

    def check_log_file(self):
        if not os.path.exists(self.log_path):
            os.makedirs(os.path.dirname(self.log_path), exist_ok=True)
            self.logger.error('Log file not find')
            self.logger.info('Generate new log file')

    def load_config(self):
        sync = False
        self.check_log_file()
        if not os.path.exists(self.config_path):
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
            self.logger.error('Config not find')
            self.logger.info('Generate default config')
            with open(self.config_path, 'w', encoding='utf-8') as config_file:
                json.dump(DEFAULT_CONFIG, config_file, indent=4)
            return DEFAULT_CONFIG
        with open(self.config_path, 'r', encoding='utf-8') as config_file:
            data = dict(json.load(config_file))
        for keys in DEFAULT_CONFIG.keys():
            if keys not in data.keys():
                self.logger.error(f"Config {keys} not found, use default value {DEFAULT_CONFIG[keys]}")
                data.update({keys: DEFAULT_CONFIG[keys]})
                sync = True
        if sync:
            with open(self.config_path, 'w', encoding='utf-8') as config_file:
                json.dump(data, config_file, indent=4)
        return data

    def init_config(self):
        config_dict = self.load_config()
        self.name = config_dict['name']
        self.password = config_dict['password']
        self.host_name = config_dict['host_name']
        self.host_port = config_dict['host_port']
        self.aes_key = config_dict['aes_key']

    def init_all_config(self):
        self.init_advanced_config()
        self.init_config()
