"""
CBR config file stuffs
"""
import os
import shutil
from ruamel import yaml  # type: ignore
from typing import Any, List, Mapping, NoReturn

from cbr.lib.logger import CBRLogger
from cbr.lib.typeddicts import TypedConfig, TypedConfigStruct

# from ruamel.yaml.comments import CommentedMap


DEFAULT_CONFIG_PATH = "cbr/resources/default_config.yml"
CONFIG_PATH = "config.yml"
CONFIG_STRUCTURE: List[TypedConfigStruct] = [
    {"name": "server_setting",
     "sub_structure": [
         {"name": "host_name", "sub_structure": [], },
         {"name": "port", "sub_structure": [], },
         {"name": "aes_key", "sub_structure": [], },
     ]
     },
    {"name": "debug",
     "sub_structure": [
         {"name": "all", "sub_structure": [], },
         {"name": "CBR", "sub_structure": [], },
         {"name": "plugin", "sub_structure": [], },
     ]
     },
    {"name": "clients", "sub_structure": [], },
    {"name": "log",
     "sub_structure": [
         {"name": "size_to_zip", "sub_structure": [], },
         {"name": "split_log", "sub_structure": [], },
         {"name": "size_to_zip_chat", "sub_structure": [], },
     ]
     }
]


class ConfigManager:
    def __init__(self, logger: CBRLogger):
        self.logger = logger

    def __gen_config(self) -> NoReturn:
        if not os.path.exists(DEFAULT_CONFIG_PATH):
            self.logger.error("Default config not found, re-installing ChatBridgeReforged may fix the problem")
            exit(1)
        else:
            shutil.copyfile(DEFAULT_CONFIG_PATH, CONFIG_PATH)
            self.logger.warning("Default config is used now")
            self.logger.warning("Please configure the config and restart again")
            self.logger.warning("Exit now")
            exit(0)

    def __check_node(self, data: Mapping[str, Any], structure: List[TypedConfigStruct], prefix: str = "") -> bool:
        check_node_result = True
        for struct in structure:
            name = struct["name"]
            if name not in data:
                self.logger.error(f"Config '{prefix}{name}' is not exist in config.yml")
                check_node_result = False
                continue
            self.logger.debug(f"Checking for '{prefix}{name}'", "CBR")
            if "sub_structure" in struct and len(struct["sub_structure"]) != 0:
                flag = self.__check_node(data[name], struct["sub_structure"], f"{prefix}{name}.")
                check_node_result = check_node_result and flag
                continue
            if prefix == "" and name == "clients":
                values = ", ".join([f"'{d['name']}'" for d in data[name]])
                self.logger.debug(f"Clients are: {values}", "CBR")
            else:
                self.logger.debug(f"Config '{prefix}{name}' values '{data[name]}'", "CBR")
        return check_node_result

    def __check_config_contents(self, data: Mapping[str, Any]):
        self.logger.debug("Start checking config.yml", "CBR")
        if self.__check_node(data, CONFIG_STRUCTURE):
            self.logger.debug("Finished checking config.yml", "CBR")
        else:
            self.logger.error("Some config is missing in config.yml")
            exit(2)

    def read(self) -> TypedConfig:
        if not os.path.exists(CONFIG_PATH):
            self.logger.warning("Config file is missing, default config generated")
            self.__gen_config()
        with open(CONFIG_PATH, "r", encoding="utf-8") as config:
            data: TypedConfig = yaml.safe_load(config)  # type: ignore
        self.__check_config_contents(data)
        return data
