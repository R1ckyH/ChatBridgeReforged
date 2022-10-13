"""
CBR config file stuffs
"""
import os
import shutil

from os import path
from ruamel import yaml
from typing import TYPE_CHECKING
# from ruamel.yaml.comments import CommentedMap

from cbr.lib.zip import Compressor

if TYPE_CHECKING:
    from cbr.lib.logger import CBRLogger

CHATBRIDGEREFORGED_VERSION = "0.2.5-dev030"
LIB_VERSION = "v20210915"
DEFAULT_CONFIG_PATH = "cbr/resources/default_config.yml"
CONFIG_PATH = "config.yml"
CONFIG_STRUCTURE = [
    {"name": "server_setting",
     "sub_structure": [
         {"name": "host_name", },
         {"name": "port", },
         {"name": "aes_key", },
     ]
     },
    {"name": "debug",
     "sub_structure": [
         {"name": "all", },
         {"name": "CBR", },
         {"name": "plugin", },
     ]
     },
    {"name": "clients", },
    {"name": "log",
     "sub_structure": [
         {"name": "size_to_zip", },
         {"name": "split_log", },
         {"name": "size_to_zip_chat", },
     ]
     }
]


class ConfigChecker:
    def __init__(self, logger: "CBRLogger"):
        self.logger = logger

    def check_all(self):
        if not path.exists("config"):
            os.mkdir("config")
        if not path.exists("plugins"):
            os.mkdir("plugins")
        if not path.exists(CONFIG_PATH):
            self.logger.error("Config file is missing, default config generated")
            self.__gen_config()
        else:
            with open(CONFIG_PATH, "r", encoding="utf-8") as config:
                data = yaml.safe_load(config)
            try:
                self.logger.debug_config = data["debug"]
                self.logger.debug_all = self.logger.debug_config["all"]
                logs_data = data["log"]
                split_log = logs_data["split_log"]
                compressor = Compressor(self.logger)
                compressor.zip_log("latest.log", logs_data["size_to_zip"])
                self.logger.setup(split_log=split_log)
                if split_log:
                    compressor.zip_log("chat.log", logs_data["size_to_zip_chat"])
                    self.logger.setup(True)
            except KeyError:
                self.logger.setup()
                raise ValueError("Some config is missing in config.yml")
        self.logger.debug("Checking config ......", "CBR")
        self.__check_config_info(data)
        return data

    def __gen_config(self):
        if not path.exists(DEFAULT_CONFIG_PATH):
            raise FileNotFoundError("Default config not found, re-installing ChatBridgeReforged may fix the problem")
            # self.logger.bug()
        else:
            shutil.copyfile(DEFAULT_CONFIG_PATH, CONFIG_PATH)
            self.logger.info("Default config is used now")
            self.logger.info("Please configure the config and restart again")
            self.logger.info("Exit now")
            exit(0)  # exit here

    def __check_config_info(self, data):
        self.logger.debug("Checking config.yml", "CBR")
        if not self.__check_node(data, CONFIG_STRUCTURE):
            self.logger.setup()
            raise ValueError("Some config is missing in config.yml")
        else:
            self.logger.debug("Finish config check", "CBR")

    def __check_node(self, data, structure):
        check_node_result = True
        for i in range(len(structure)):
            struct = structure[i]
            if struct["name"] not in data.keys():
                check_node_result = False
                self.logger.error("Config " + struct["name"] + " not exist in config.yml")
                break
            elif "sub_structure" in struct.keys():
                self.logger.debug(f"Checking for '{structure[i]['name']}'", "CBR")
                if not self.__check_node(data[struct["name"]], struct["sub_structure"]):
                    check_node_result = False
                    self.logger.error("Config " + struct["name"] + " not exist in config.yml")
                    break
            else:
                if struct["name"] == "clients":
                    msg = "Clients are:"
                    for j in range(len(data[struct["name"]])):
                        msg = msg + f" '{data[struct['name']][j]['name']}'"
                    self.logger.debug(msg, "CBR")
                else:
                    self.logger.debug(f"Config '{struct['name']}' values '{data[struct['name']]}'", "CBR")
        return check_node_result


class Config:
    def __init__(self):
        self.logger = None
        self.config_checker = None
        self.ip = "127.0.0.1"
        self.port = 30001
        self.aes_key = "ThisIsTheSecret"
        self.debug = {"all": True, "CBR": False, "plugin": False}
        self.version = CHATBRIDGEREFORGED_VERSION
        self.lib_version = LIB_VERSION
        self.raw_data = {}
        self.clients = []

    def __init_data(self):
        try:
            self.ip = self.raw_data["server_setting"]["host_name"]
            self.port = self.raw_data["server_setting"]["port"]
            self.aes_key = self.raw_data["server_setting"]["aes_key"]
            self.debug = self.raw_data["debug"]
            self.clients = self.raw_data["clients"]
            self.logger.debug_all = self.raw_data["debug"]["all"]
        except AttributeError:
            exit(0)

    def init_config(self, logger: "CBRLogger"):
        self.logger = logger
        self.config_checker = ConfigChecker(self.logger)
        self.raw_data = self.config_checker.check_all()
        self.__init_data()
        self.logger.info(f"CBR is now starting at pid {os.getpid()}")
        self.logger.info(f"version : {self.version}, lib version : {self.lib_version}")
