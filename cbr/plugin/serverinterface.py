'''
CBR ServerInterface
'''
import json
import trio
import logging

#from cbr.net.tcpserver import CBRTCPServer

class ServerInterface:
    def __init__(self, server):
        self._server = server
        self.logger : logging.Logger = server.logger
        self.__result_cache = None

    def is_client_online(self, client):
        """
            Check clients online or not
        """
        return self._server.clients[client]['online']
    
    def is_mc_client(self, client):
        if self._server.clients[client]['type'] == 'mc':
            return True
        else:
            return False

    def get_online_clients(self):
        """
            get online list of clients
        """
        clients = []
        for i in self._server.clients.keys():
            if self.is_client_online(i):
                clients.append(i)
        return clients
    
    def get_online_mc_clients(self):
        """
            get online list of minecraft clients
        """
        clients = []
        for i in self._server.clients.keys():
            if self.is_client_online(i) and self.is_mc_client(i):
                clients.append(i)
        return clients
    
    def send_msg(self, target, msg):
        """
            send message to target client
        """
        message = json.dumps(self._server.process.server_msg(msg))
        self.logger.debug(message)
        trio.from_thread.run(self._server.send_msg, self._server.clients[target]['stream'], message)

    def send_command(self, target, cmd) -> str:
        '''
            return None if timeout
        '''
        return trio.from_thread.run(self.__wait_cmd_result, target, cmd)
    
    def send_servers_command(self, targets, cmd) -> dict:
        '''
            targets is list of server to send

            targets can't be string

            return None in dict if timeout
            
            return False in dict if rcon error exist
        '''
        return trio.from_thread.run(self.__wait_servers_cmd_result, targets, cmd)

    async def __wait_servers_cmd_result(self, targets, cmd):
        self.__result_cache = {}
        async with trio.open_nursery() as nursery:
            for i in range(len(targets)):
                nursery.start_soon(self.__cache_cmds_result, targets[i], cmd)
        results = self.__result_cache
        self.__result_cache = None
        return results

    async def __cache_cmds_result(self, target, cmd):
        self.__result_cache.update({target : await self.__wait_cmd_result(target, cmd)})

    async def __wait_cmd_result(self, target, cmd):
        with trio.move_on_after(2) as self._server.clients[target]['cmdlock']:
            self._server.clients[target]['cmdresult'] = None
            await self._server.process.send_cmd(cmd, target)
            await trio.sleep(2)
        self.logger.debug(str(trio.current_time()) + "finish " + target)
        return self._server.clients[target]['cmdresult']