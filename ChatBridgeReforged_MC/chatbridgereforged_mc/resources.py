import sys

from chatbridgereforged_mc.utils import *

# Config

PREFIX = '!!CBR'
PREFIX2 = '!!cbr'
VERSION = '0.0.1-dev021'
LIB_VERSION = "v20210915"
CLIENT_TYPE = "mc"

ADVANCED_CONFIG_PATH = 'advanced_config.json'

WAIT_TIME = [5, 10, 30, 60, 120, 300, 600, 1200, 1800, 3600]

DEFAULT_ADVANCED_CONFIG = {
    "debug_mode": False,
    "config_path": "config/ChatBridgeReforged_MC.json",
    "log_path": "logs/ChatBridgeReforged_MC.log",
    'chat_path': "logs/ChatBridgeReforged_MC_chat.log",
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

help_msg = '''§b-----------§fChatBridgeReforged_Client§b-----------§r
''' + help_formatter(PREFIX, 'help', 'show help message§r', 'show help message') + '''
''' + help_formatter(PREFIX, 'start', 'start ChatBridgeReforged client§r', 'start') + '''
''' + help_formatter(PREFIX, 'stop', 'stop ChatBridgeReforged client§r', 'stop') + '''
''' + help_formatter(PREFIX, 'status', 'show status of ChatBridgeReforged client§r', 'show status') + '''
''' + help_formatter(PREFIX, 'reload', 'reload ChatBridgeReforged client§r', 'reload') + '''
''' + help_formatter(PREFIX, 'restart', 'restart ChatBridgeReforged client§r', 'restart') + '''
''' + help_formatter(PREFIX, 'ping', 'ping ChatBridgeReforged server§r', 'ping') + '''
§b-----------------------------------------------§r'''


if __name__ == '__main__':
    sys.exit()
