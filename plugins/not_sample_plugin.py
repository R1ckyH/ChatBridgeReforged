# test-plugin
# similar with MCDR

from cbr.plugin.info import MessageInfo
from cbr.plugin.serverinterface import ServerInterface

PLUGIN_METADATA = {
    'id': 'not_sample_plugin',
    'version': '0.0.1',
    'name': 'not_sample_plugin_xd',
    'description': '##list.',
    'author': 'Ricky',
    'link': 'https://github.com/rickyhoho/ChatBridgeReforged',
    'dependencies': {
        'chatbridgereforged': '>=0.0.1'
    }
}  # just do it like MCDR


def players_no_bot(player_list):
    player_string = ''
    for i in range(len(player_list)):
        if not player_list[i].startswith("bot_") or player_list[i].startswith('Bot_'):
            player_string += ', ' + player_list[i]
    if player_string.startswith(", "):
        return player_string[2:]
    return player_string


def on_message(server: ServerInterface, info: MessageInfo):
    if info.content == '##list' or info.content == "##online":
        info.cancel_send_message()
        online_mc_client = server.get_online_mc_clients()
        players = {}
        results = server.send_servers_command(online_mc_client, 'list')
        if results is None:
            server.send_msg(info.client, "No information")
            return
        for i in results.keys():
            if results[i] is not None:
                if results[i].startswith("Unknown command"):
                    players.update({i: "Command Error"})
                else:
                    playerstring = players_no_bot(results[i].split('online: ')[1].split(', '))
                    players.update({i: playerstring})
            else:
                players.update({i: "Command Failed"})
        message = "- Online players:"
        for i in range(len(online_mc_client)):
            message += f"\n[{online_mc_client[i]}]: {players[online_mc_client[i]]}"
        server.send_msg(info.client, message)
