# test-plugin
# similar with MCDR

from cbr.plugin.info import MessageInfo
from cbr.plugin.cbrinterface import CBRInterface

METADATA = {
    'id': 'not_sample_plugin',
    'version': '0.0.1',
    'name': 'not_sample_plugin_xd',
    'description': '##list, it is not a sample plugin',
    'author': 'Ricky',
    'link': 'https://github.com/R1ckyH/ChatBridgeReforged'
}


def players_no_bot(player_list):
    player_string = ''
    for i in range(len(player_list)):
        if not player_list[i].startswith("bot_") or player_list[i].startswith('Bot_'):
            player_string += ', ' + player_list[i]
    if player_string.startswith(", "):
        return player_string[2:]
    return player_string


def list_player(server, info):
    if info.content == '##list' or info.content == "##online":
        info.cancel_send_message()
        online_mc_client = server.get_online_mc_clients()
        players = {}
        results = server.servers_command_query(online_mc_client, 'list')
        if results is None:
            server.reply(info, "No information")
            return
        for i in results.keys():
            if results[i] is not None:
                if results[i].startswith("Unknown command"):
                    players.update({i: "Command Error"})
                else:
                    player_string = players_no_bot(results[i].split('online: ')[1].split(', '))
                    players.update({i: player_string})
            else:
                players.update({i: "Command Failed"})
        message = "- Online players:"
        for i in range(len(online_mc_client)):
            message += f"\n[{online_mc_client[i]}]: {players[online_mc_client[i]]}"
        server.reply(message, info)


def on_message(server: CBRInterface, info: MessageInfo):
    list_player(server, info)


def on_command(server, info):  # not recommend to do, but you can do it
    list_player(server, info)


def on_load(server: CBRInterface):
    server.register_help_message("##list", "list out the online players in servers")
