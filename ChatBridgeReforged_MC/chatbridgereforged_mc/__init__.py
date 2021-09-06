import threading
import time

from chatbridgereforged_mc.lib.config import Config
from chatbridgereforged_mc.lib.logger import CBRLogger
from chatbridgereforged_mc.net.tcpclient import CBRTCPClient
from chatbridgereforged_mc.resources import *

client: CBRTCPClient


@new_thread("CBRProcess")
def on_info(server: PluginServerInterface, info: Info):
    msg = info.content
    if msg.startswith(PREFIX) or msg.startswith(PREFIX2):
        info.cancel_send_to_server()
        # if msg.endswith('<--[HERE]'):
        #    msg = msg.replace('<--[HERE]', '')
        client.process.input_process(msg.replace(PREFIX + ' ', "").replace(PREFIX2 + ' ', ""), server, info)
    elif info.is_player:
        if client is None:
            return
        client.try_start()
        if client.connected:
            client.send_msg(client.socket, msg_json_formatter(client.name, info.player, info.content))


def on_player_joined(server, name, info=None):
    client.try_start()
    client.send_msg(client.socket, msg_json_formatter(client.name, '', name + ' joined ' + client.name))


def on_player_left(server, name, info=None):
    client.try_start()
    client.send_msg(client.socket, msg_json_formatter(client.name, '', name + ' left ' + client.name))


def on_unload(server):
    client.close_connection()


def main(server=None):
    global client
    logger = CBRLogger()
    config = Config(logger, server)
    config.init_all_config()
    client = CBRTCPClient(config, logger, server)
    client.try_start()
    if server is None:
        while True:
            input_message = input()
            client.process.input_process(input_message)


def on_load(server: PluginServerInterface, old):
    if old is not None:
        try:
            old.client.try_stop()
        except Exception:
            old.client.logger.bug_log(error=True)
    server.register_help_message(PREFIX, "ChatBridgeReforged")
    time.sleep(0.5)
    main(server)


if __name__ == '__main__':
    main()
