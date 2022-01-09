import time
import threading

from chatbridgereforged_mc.lib.config import Config
from chatbridgereforged_mc.lib.logger import CBRLogger
from chatbridgereforged_mc.net.tcpclient import CBRTCPClient
from chatbridgereforged_mc.resources import *

client: CBRTCPClient
end = False


@new_thread("CBRProcess")
def on_info(server: PluginServerInterface, info: Info):
    msg = info.content
    if msg.startswith(PREFIX) or msg.startswith(PREFIX2):
        info.cancel_send_to_server()
        # if msg.endswith('<--[HERE]'):
        #    msg = msg.replace('<--[HERE]', '')
        client.process.input_process(msg.replace(PREFIX + ' ', "").replace(PREFIX2 + ' ', ""), server, info)
    else:
        if client is None:
            return
        if not client.connecting and info.is_player:
            client.try_start()
        if info.is_player and client.connected:
            client.send_msg(client.socket, msg_json_formatter(client.name, info.player, info.content))


def on_player_joined(server, name, info=None):
    client.try_start()
    client.send_msg(client.socket, msg_json_formatter(client.name, '', name + ' joined ' + client.name))


def on_player_left(server, name, info=None):
    client.try_start()
    client.send_msg(client.socket, msg_json_formatter(client.name, '', name + ' left ' + client.name))


def on_unload(server):
    global end
    end = True
    client.close_connection()


def main(server=None):
    global client, end
    end = False
    logger = CBRLogger()
    config = Config(logger, server)
    config.init_all_config()
    client = CBRTCPClient(config, logger, server)
    logger.load(config, client)
    client.try_start()
    if config.auto_restart:
        threading.Thread(target=restart_loop, name="auto_restart", daemon=True).start()
    if server is None:
        while True:
            input_message = input()
            try:
                client.process.input_process(input_message)
            except Exception:
                client.logger.bug_log()


def on_load(server: PluginServerInterface, old):
    if old is not None:
        try:
            old.client.try_stop()
        except Exception:
            old.client.logger.bug_log(error=True)
    server.register_help_message(PREFIX, "ChatBridgeReforged")
    time.sleep(0.5)
    main(server)


def wait_restart():
    client.success_connect = False
    for i in client.config.wait_time:
        time.sleep(i)
        if not client.success_connect and not client.connected:
            client.logger.debug(f"Try start")
            client.try_start(auto_connect=True)
        else:
            client.logger.debug(f"Auto_restart reset after 5 sec")
            time.sleep(5)
            return
    while True:
        if not client.success_connect and not client.connected:
            time.sleep(3600)
            client.logger.debug(f"Try start")
            client.try_start(auto_connect=True)
        else:
            client.logger.debug(f"Auto_restart reset after 5 sec")
            time.sleep(5)
            return


def restart_loop():
    while not end:
        wait_restart()


if __name__ == '__main__':
    main()
