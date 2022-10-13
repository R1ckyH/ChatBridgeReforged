import json


def info_formatter(client, player, msg):
    if player != "":
        message = f"[{client}] <{player}> {msg}"  # chat message
    else:
        message = f"[{client}] {msg}"
    return message


def message_formatter(client, player, msg, receiver=""):
    message = {
        "action": "message",
        "client": client,
        "player": player,
        "message": msg
       }
    if receiver != "":
        message.update({"receiver": receiver})
    return json.dumps(message)


def ping_formatter(pong=False):
    if pong:
        action_type = "pong"
    else:
        action_type = "ping"
    message = {
        "action": "keepAlive",
        "type": action_type
    }
    return json.dumps(message)


def login_formatter(success=True):
    if success:
        action_result = "login success"
    else:
        action_result = "login fail"
    message = {
        "action": "result",
        "result": action_result
    }
    return json.dumps(message)


def command_formatter(cmd, receiver):
    message = {
        "action": "command",
        "sender": "CBR",
        "receiver": receiver,
        "command": cmd,
        "result":
        {
            "responded": False
        }
    }
    return json.dumps(message)


def api_formatter(receiver, plugin_id, function_name, keys: dict):
    message = {
        "action": "api",
        "sender": "CBR",
        "receiver": receiver,
        "plugin": plugin_id,
        "function": function_name,
        "keys": keys,
        "result":
        {
            "responded": False
        }
    }
    return json.dumps(message)


def no_color_formatter(msg):
    for i in range(6):
        msg = msg.replace("§" + str(i), "").replace("§" + chr(97 + i), "")
    msg = msg.replace("§6", "").replace("§7", "").replace("§8", "").replace("§9", "").replace("§r", "")
    return msg
