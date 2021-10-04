import json
import os

from cbr.plugin.info import MessageInfo
from cbr.plugin.cbrinterface import CBRInterface

METADATA = {
    'id': 'cqhttp',
    'version': '0.0.1',
    'name': 'cqhttp',
    'description': 'communicate with cqhttp',
    'author': 'Ricky',
    'link': 'https://github.com/rickyhoho/ChatBridgeReforged'
}

DEFAULT_CONFIG = {
    'full_msg_group_client': 'cqhttp1',
    'less_msg_group_client': 'cqhttp'
}

full_msg_group_client = ''
less_msg_group_client = ''
disable_join_left = True
config_path = 'config/cqhttp.json'


def replace_message(msg):
    msg = msg.replace("##mc ", '').replace('##MC ', '').replace('mc ', '')
    msg = msg.replace('##qq ', '').replace('##QQ ', '').replace('qq ', '')
    return msg


def custom_check_send(target, msg, client, player, server: CBRInterface):
    if target == 'full' and full_msg_group_client != '':
        if server.is_client_online(full_msg_group_client):
            server.send_custom_message(full_msg_group_client, msg, client, player)
    elif target == 'less' and less_msg_group_client != '':
        if server.is_client_online(less_msg_group_client):
            server.send_custom_message(less_msg_group_client, msg, client, player)


def on_message(server: CBRInterface, info: MessageInfo):
    if info.client_type == 'cqhttp':
        if info.source_client == less_msg_group_client and less_msg_group_client != '':
            info.cancel_send_message()
            msg = info.content
            if msg.startswith('##mc ') or msg.startswith('##MC ') or msg.startswith('mc '):
                msg = replace_message(msg)
                servers = server.get_online_mc_clients()
                server.logger.info(f"[{info.source_client}] <{info.sender}> {msg}")
                for i in servers:
                    server.send_custom_message(i, msg, info.source_client, info.sender)
    else:
        args = info.content.split(' ')
        if disable_join_left and len(args) == 3 and (args[1] == 'joined' or args[1] == 'left'):
            return
        if info.content.startswith('##qq ') or info.content.startswith('##QQ ') or info.content.startswith('qq '):
            msg = replace_message(info.content)
            custom_check_send('less', msg, info.source_client, info.sender, server)
            custom_check_send('full', msg, info.source_client, info.sender, server)
        else:
            custom_check_send('full', info.content, info.source_client, info.sender, server)


def on_command(server: CBRInterface, info: MessageInfo):
    if info.content.startswith('##qq') or info.content.startswith('##QQ') or info.content.startswith('qq '):
        info.cancel_send_message()
        msg = replace_message(info.content)
        custom_check_send('less', msg, info.source_client, info.sender, server)
        custom_check_send('full', msg, info.source_client, info.sender, server)


def on_load(server: CBRInterface):
    global full_msg_group_client, less_msg_group_client
    if os.path.exists(config_path):
        with open(config_path, 'r', encoding='utf-8') as config:
            data = json.load(config)
    else:
        with open(config_path, 'w', encoding='utf-8') as config:
            json.dump(DEFAULT_CONFIG, config, indent=4)
        data = DEFAULT_CONFIG
    full_msg_group_client = data['full_msg_group_client']
    less_msg_group_client = data['less_msg_group_client']
