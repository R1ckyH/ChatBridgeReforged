'''
CBR Info
'''

class MessageInfo:
    def __init__(self, client : str, message : str, player : str = None):
        self.client = client
        self.content = message
        self.player = player
        self._send_to_servers = True

    def cancel_send_message(self):
        self._send_to_servers = False

    def should_send_message(self):
        self._send_to_servers = True
        
    def is_player(self):
        """
            Check message send by player or not
        """
        if self.player != None:
            return True
        else:
            return False