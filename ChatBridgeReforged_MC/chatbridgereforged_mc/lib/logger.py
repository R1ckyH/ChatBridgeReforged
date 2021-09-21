import traceback

from datetime import datetime
from mcdreforged.api.all import *
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from chatbridgereforged_mc.lib.config import Config
    from chatbridgereforged_mc.net.tcpclient import CBRTCPClient


class CBRLogger:
    def __init__(self):
        self._debug_mode = False
        self.log_path = ''
        self.client = None

    def load(self, config: 'Config', client_class=None):
        self.client: 'CBRTCPClient' = client_class
        self._debug_mode = config.debug_mode
        self.log_path = config.log_path

    def info(self, msg):
        self.out_log(msg)

    def error(self, msg):
        self.out_log(msg, error=True)

    def debug(self, msg):
        self.out_log(msg, debug=True)

    def out_log(self, msg: str, error=False, debug=False, not_spam=False):
        for i in range(6):
            msg = msg.replace('§' + str(i), '').replace('§' + chr(97 + i), '')
        msg = msg.replace('§6', '').replace('§7', '').replace('§8', '').replace('§9', '')
        heading = '[CBR] ' + datetime.now().strftime("[%Y-%m-%d %H:%M:%S] ")
        if error:
            msg = heading + '[ERROR]: ' + msg
        elif debug:
            if not self._debug_mode:
                return
            msg = heading + '[DEBUG]: ' + msg
        else:
            msg = heading + '[INFO]: ' + msg
        if not not_spam:
            print(msg + '\n', end='')
            if self.log_path != '':
                with open(self.log_path, 'a+', encoding='utf-8') as log:
                    log.write(msg + '\n')

    def bug_log(self, error=False):
        self.error('bug exist')
        for line in traceback.format_exc().splitlines():
            if error is True:
                self.error(line)
            else:
                self.debug(line)

    def print_msg(self, msg, num, info=None, server: ServerInterface = None, player='', error=False, debug=False, not_spam=False):
        if num == 0:
            if self.client.server is not None:
                if server is not None:
                    if player == '':
                        server.say(msg)
                    else:
                        server.tell(player, msg)
            else:
                not_spam = False
            self.out_log(str(msg), not_spam=not_spam)
        elif num == 1:
            server.reply(info, msg)
            self.info(str(msg))
        elif num == 2:
            if info is None or not info.is_player:
                self.out_log(msg, error, debug)
            else:
                server.reply(info, msg)

    def force_debug(self, info=None, server=None):
        self._debug_mode = not self._debug_mode
        self.print_msg(f'force debug: {self._debug_mode}', 2, info, server=server)
