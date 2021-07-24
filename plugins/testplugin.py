#test-plugin
#similar with MCDR

from cbr.plugin.info import MessageInfo
from cbr.plugin.serverinterface import ServerInterface

def players_no_bot(player_list):
    player_string = ''
    for i in range(len(player_list)):
        if not player_list[i].startswith("bot_"):
            player_string += player_list[i]
    return player_string

def on_message(server : ServerInterface, info : MessageInfo):
    if info.content.startswith('##list') or info.content.startswith("##online"):
        online_mc_client = server.get_online_mc_clients()
        players = {}
        results = server.send_servers_command(online_mc_client, 'list')
        for i in results.keys():
            if results[i] != None:
                if results[i].startswith("Unknown command"):
                    players.update({i : "Command Error"})
                else:
                    playerstring = players_no_bot(results[i].split('online: ')[1].split(', '))
                    players.update({i : playerstring})
            else:
                players.update({online_mc_client[i] : "Command Failed"})
        message = "- Online players:"
        for i in range(len(online_mc_client)):
            message += f"\n[{online_mc_client[i]}]: {players[online_mc_client[i]]}"
        server.send_msg(info.client, message)