"""
CBR Info
"""
from cbr.lib.logger import CBRLogger


class MessageInfo:
    def __init__(self, client: str, message: str, player: str = None, logger: CBRLogger = None):
        self.client = client
        self.content = message
        self.player = player
        self._logger = logger
        self._send_to_servers = True

    def is_send_message(self):
        return self._send_to_servers

    def cancel_send_message(self):
        self._send_to_servers = False
        self._logger.debug(f"Cancel to send out {self.content}", module='plugin')

    def should_send_message(self):
        self._send_to_servers = True
        self._logger.debug(f"Continue to send out {self.content}", module='plugin')

    def is_player(self):
        """
            Check message send by player or not
        """
        if self.player is not None:
            return True
        else:
            return False
