import sys

# Config

PREFIX = "!!CBR"
PREFIX2 = "!!cbr"
VERSION = "0.2.5-dev030"
LIB_VERSION = "v20210915"
CLIENT_TYPE = "mc"

ADVANCED_CONFIG_PATH = "advanced_config.json"

WAIT_TIME = [5, 10, 30, 60, 120, 300, 600, 1200, 1800, 3600]

DEFAULT_ADVANCED_CONFIG = {
    "debug_mode": False,
    "config_path": "config/ChatBridgeReforged_MC.json",
    "log_path": "logs/ChatBridgeReforged_MC.log",
    "chat_path": "logs/ChatBridgeReforged_MC_chat.log",
    "client_color": "6",
    "ping_time": 60,
    "timeout": 120,
    "size_to_zip": 512,  # kb
    "size_to_zip_chat": 512,  # kb
    "disable_chat_log": True,
    "split_chat_log": False,
    "auto_restart": True  # not recommend to change
}

DEFAULT_CONFIG = {
    "name": "survival",
    "password": "survival",
    "host_name": "127.0.0.1",
    "host_port": 30001,
    "aes_key": "ThisIsTheSecret"
}

if __name__ == "__main__":
    sys.exit()
