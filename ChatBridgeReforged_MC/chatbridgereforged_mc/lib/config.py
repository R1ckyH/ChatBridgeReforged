"""
config here
"""
import json
import os
import zipfile

from chatbridgereforged_mc.lib.logger import CBRLogger
from chatbridgereforged_mc.constants import *


class AdvancedConfig:
    def __init__(self, logger: CBRLogger, server=None):
        self.logger = logger
        self.server: PluginServerInterface = server
        self.wait_time = WAIT_TIME
        self.advanced_path = ADVANCED_CONFIG_PATH
        self.debug_mode = DEFAULT_ADVANCED_CONFIG["debug_mode"]
        self.config_path = DEFAULT_ADVANCED_CONFIG["config_path"]
        self.log_path = DEFAULT_ADVANCED_CONFIG["log_path"]
        self.chat_path = DEFAULT_ADVANCED_CONFIG["chat_path"]
        self.client_color = DEFAULT_ADVANCED_CONFIG["client_color"]
        self.ping_time = DEFAULT_ADVANCED_CONFIG["ping_time"]
        self.timeout = DEFAULT_ADVANCED_CONFIG["timeout"]
        self.size_to_zip = DEFAULT_ADVANCED_CONFIG["size_to_zip"]
        self.size_to_zip_path = DEFAULT_ADVANCED_CONFIG["size_to_zip_chat"]
        self.disable_chat_log = DEFAULT_ADVANCED_CONFIG["disable_chat_log"]
        self.split_chat_log = DEFAULT_ADVANCED_CONFIG["split_chat_log"]
        self.auto_restart = DEFAULT_ADVANCED_CONFIG["auto_restart"]

    def load_advanced_config(self):
        if self.server is not None:
            with self.server.open_bundled_file(self.advanced_path) as config_file:
                data = dict(json.load(config_file))
        else:
            try:
                with zipfile.ZipFile(sys.argv[0], "r") as zip:
                    if "advanced_config.json" in zip.namelist():
                        with zip.open("advanced_config.json", "r") as config_file:
                            data = dict(json.load(config_file))
                    else:
                        self.logger.error("Config not find")
                        raise FileNotFoundError("Advanced_config not find")
                    print("PYZ MODE START")
            except zipfile.BadZipFile:
                with open("advanced_config.json", "r") as config_file:
                    data = dict(json.load(config_file))
                    print("FILE MODE START")
        for keys in DEFAULT_ADVANCED_CONFIG.keys():
            if keys not in data.keys():
                self.logger.error(f"Advanced config {keys} not found, use default value {DEFAULT_ADVANCED_CONFIG[keys]}")
                data.update({keys: DEFAULT_ADVANCED_CONFIG[keys]})
        return data

    def init_advanced_config(self):
        config_dict = self.load_advanced_config()
        self.debug_mode = config_dict["debug_mode"]
        self.config_path = config_dict["config_path"]
        self.log_path = config_dict["log_path"]
        self.chat_path = config_dict["chat_path"]
        self.client_color = config_dict["client_color"]
        self.ping_time = config_dict["ping_time"]
        self.timeout = config_dict["timeout"]
        self.size_to_zip = config_dict["size_to_zip"]
        self.size_to_zip_path = config_dict["size_to_zip_chat"]
        self.disable_chat_log = config_dict["disable_chat_log"]
        self.split_chat_log = config_dict["split_chat_log"]


class Config(AdvancedConfig):
    def __init__(self, logger: "CBRLogger", server=None):
        super().__init__(logger, server)
        self.logger = logger
        self.server: PluginServerInterface = server
        self.name = DEFAULT_CONFIG["name"]
        self.password = DEFAULT_CONFIG["password"]
        self.host_name = DEFAULT_CONFIG["host_name"]
        self.host_port = DEFAULT_CONFIG["host_port"]
        self.aes_key = DEFAULT_CONFIG["aes_key"]

    def check_log_file(self):
        if not os.path.exists(self.log_path):
            os.makedirs(os.path.dirname(self.log_path), exist_ok=True)
            self.logger.error("Log file not find")
            self.logger.info("Generate new log file")

    def load_config(self):
        sync = False
        self.check_log_file()
        if not os.path.exists(self.config_path):
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
            self.logger.error("Config not find")
            self.logger.info("Generate default config")
            with open(self.config_path, "w", encoding="utf-8") as config_file:
                json.dump(DEFAULT_CONFIG, config_file, indent=4)
            return DEFAULT_CONFIG
        with open(self.config_path, "r", encoding="utf-8") as config_file:
            data = dict(json.load(config_file))
        for keys in DEFAULT_CONFIG.keys():
            if keys not in data.keys():
                self.logger.error(f"Config {keys} not found, use default value {DEFAULT_CONFIG[keys]}")
                data.update({keys: DEFAULT_CONFIG[keys]})
                sync = True
        if sync:
            with open(self.config_path, "w", encoding="utf-8") as config_file:
                json.dump(data, config_file, indent=4)
        return data

    def init_config(self):
        config_dict = self.load_config()
        self.name = config_dict["name"]
        self.password = config_dict["password"]
        self.host_name = config_dict["host_name"]
        self.host_port = config_dict["host_port"]
        self.aes_key = config_dict["aes_key"]

    def init_all_config(self):
        self.init_advanced_config()
        self.init_config()
