"""
CBR Info
"""
from cbr.lib.logger import CBRLogger


class MessageInfo:
    def __init__(self, client, message, sender=None, client_type="", logger: CBRLogger = None):
        self.source_client: str = client  # TODO: split client and source client
        self.content = message
        self.sender: str = sender
        self._logger = logger
        self.client_type = client_type
        self._send_to_servers = True

    def is_send_message(self):
        """
            check msg cancel send to server or not
        """
        return self._send_to_servers

    def cancel_send_message(self):
        """
            cancel message send to server
        """
        self._send_to_servers = False
        self._logger.debug(f"Cancel to send out {self.content}", module="plugin")

    def should_send_message(self):
        """
            enable message send to server
        """
        self._send_to_servers = True
        self._logger.debug(f"Continue to send out {self.content}", module="plugin")

    def is_player(self):
        """
            Check message send by player or not
        """
        if self.sender is not None:
            return True
        else:
            return False
