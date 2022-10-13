import json

from mcdreforged.api.all import *

from chatbridgereforged_mc.constants import LIB_VERSION, CLIENT_TYPE


def rtext_cmd(txt, msg, cmd):
    return RText(txt).h(msg).c(RAction.run_command, cmd)


def help_formatter(mcdr_prefix, command, first_msg, click_msg, use_command=None):
    if use_command is None:
        use_command = command
    msg = f"{mcdr_prefix} {command} §a{first_msg}"
    return rtext_cmd(msg, f"Click me to {click_msg}", f"{mcdr_prefix} {use_command}")


def msg_json_formatter(client_name, player, msg):
    message = {
        "action": "message",
        "client": client_name,
        "player": player,
        "message": msg
    }
    return json.dumps(message)


def ping_formatter(pong=False):
    message = {
        "action": "keepAlive",
    }
    if pong:
        message.update({"type": "pong"})
    else:
        message.update({"type": "ping"})
    return json.dumps(message)


def login_formatter(name, password):
    message = {
        "action": "login",
        "name": name,
        "password": password,
        "lib_version": LIB_VERSION,
        "type": CLIENT_TYPE
    }
    return json.dumps(message)


def stop_formatter():
    message = {"action": "stop"}
    return json.dumps(message)
