'''
plugin run here
'''
import trio

from plugins.testplugin import on_message

from cbr.plugin.info import MessageInfo
from cbr.plugin.serverinterface import ServerInterface

class plugins:
    def __init__(self, server):
        self.server = ServerInterface(server)
    
    async def plugin_on_msg(self, client, player, msg):
        info = MessageInfo(client, msg, player)
        await trio.to_thread.run_sync(self.__on_message, self.server, info)
    
    def __on_message(self, server, info):
        try:
            on_message(server, info)
        except:
            self.server._server.logger.bug(exit_now = False, error = True)