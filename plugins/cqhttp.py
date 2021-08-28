import json

from cbr.plugin.info import MessageInfo
from cbr.plugin.serverinterface import ServerInterface

PLUGIN_METADATA = {
    'id': 'cqhttp',
    'version': '0.0.1',
    'name': 'cqhttp',
    'description': 'communicate with cqhttp',
    'author': 'Ricky',
    'link': 'https://github.com/rickyhoho/ChatBridgeReforged',
    'dependencies': {
        'chatbridgereforged': '>=0.0.1'
    }
}  # just do it like MCDR

full_msg_group_client = ''
less_msg_group_client = ''
config_path = 'config/cqhttp.json'


def replace_message(msg):
    msg = msg.replace("##mc ", '').replace('##MC ', '').replace('mc ', '')
    msg = msg.replace('##qq ', '').replace('##QQ ', '').replace('qq ', '')
    return msg


def custom_check_send(target, msg, client, player, server: ServerInterface):
    if target == 'full' and full_msg_group_client != '':
        server.send_custom_message(full_msg_group_client, msg, client, player)
    elif target == 'less' and less_msg_group_client != '':
        server.send_custom_message(less_msg_group_client, msg, client, player)


def on_message(server: ServerInterface, info: MessageInfo):
    if info.client_type == 'cqhttp':
        if info.client == less_msg_group_client and less_msg_group_client != '':
            info.cancel_send_message()
            msg = info.content
            if msg.startswith('##mc ') or msg.startswith('##MC ') or msg.startswith('mc '):
                msg = replace_message(msg)
                servers = server.get_online_mc_clients()
                server.logger.info(f"[{info.client}] <{info.player}> {msg}")
                for i in servers:
                    server.send_custom_message(i, msg, info.client, info.player)
    else:
        if info.content.startswith('##qq ') or info.content.startswith('##QQ ') or info.content.startswith('qq '):
            msg = replace_message(info.content)
            custom_check_send('less', msg, info.client, info.player, server)
            custom_check_send('full', msg, info.client, info.player, server)
        else:
            custom_check_send('full', info.content, info.client, info.player, server)


def on_command(server: ServerInterface, info: MessageInfo):
    if info.content.startswith('##qq') or info.content.startswith('##QQ') or info.content.startswith('qq '):
        info.cancel_send_message()
        msg = replace_message(info.content)
        custom_check_send('less', msg, info.client, info.player, server)
        custom_check_send('full', msg, info.client, info.player, server)


def on_load(server: ServerInterface):
    global full_msg_group_client, less_msg_group_client
    server.register_help_message("##list", "list out the online players in servers")
    with open(config_path, 'r') as config:
        data = json.load(config)
    full_msg_group_client = data['full_msg_group_client']
    less_msg_group_client = data['less_msg_group_client']
