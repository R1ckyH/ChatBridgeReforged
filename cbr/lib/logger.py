import logging
import sys
import traceback

from os import path, mkdir

from cbr.lib.config import Config

log_file = 'logs'
log_path = log_file + "/latest.log"

logger_black_list = ['ping', 'Result of', '- ', 'Client ', 'Ping client', 'Send Command', 'Unknown ']  # File handler
logger_black_arg2 = ['joined', 'left']  # File handler


class StdoutFilter(logging.Filter):
    def filter(self, record: logging.LogRecord):
        msg = record.getMessage()
        args = msg.split(' ')
        # print(record.levelname)
        if len(args) == 4:
            for i in range(len(logger_black_arg2)):
                if args[2] == logger_black_arg2[i]:
                    return False
        for i in range(len(logger_black_list)):
            if msg.startswith(logger_black_list[i]):
                return False
        if record.funcName == 'help_msg':
            return False
        return True


class CBRLogger(logging.getLoggerClass()):
    def __init__(self, name, config: Config):
        if not path.exists(log_file):
            mkdir(log_file)
        super().__init__(name)
        self.file_handler = logging.FileHandler(log_path, encoding='utf-8')
        self.stdout_handler = logging.StreamHandler(sys.stdout)
        self.debug_config = config.debug

    def formatter(self, date=None):
        return logging.Formatter('[%(name)s] [%(asctime)s] [%(threadName)s/%(levelname)s]: %(message)s', datefmt=date)

    def setup(self):
        if not path.exists(log_file):
            mkdir(log_file)
        self.stdout_handler.setFormatter(self.formatter('%H:%M:%S'))
        self.file_handler.setFormatter(self.formatter('%Y-%m-%d %H:%M:%S'))
        self.file_handler.addFilter(StdoutFilter())
        self.addHandler(self.stdout_handler)
        self.addHandler(self.file_handler)
        self.setLevel(logging.DEBUG)

    def bug(self, exit_now=True, error=False):
        for line in traceback.format_exc().splitlines():
            if error:
                self.error(line, exc_info=False)
            else:
                self.debug(line, "CBR")
        if exit_now:
            if self.level > logging.DEBUG and not error:
                self.error('ERROR exist, use debug mode for more information')
            exit(0)

    def debug(self, msg, module='all', *args) -> None:  # thx xd
        if self.debug_config[module] or self.debug_config['all']:
            super().debug(msg, *args)

    # no use
    '''def restart_all(self):
        self.removeHandler(self.stdout_handler)
        self.removeHandler(self.file_handler)
        print(self.hasHandlers())
        self.addHandler(self.stdout_handler)
        self.addHandler(self.file_handler)'''

    def force_debug(self, module='all'):
        self.debug_config[module] = not self.debug_config[module]
        self.info(f'- Force debug mode of {module}: {self.debug_config[module]}')
        self.debug('test', "CBR")


if __name__ == '__main__':
    logging.setLoggerClass(CBRLogger)
    b = CBRLogger("CBR", Config())
    logging.basicConfig(level=logging.INFO, format='[%(asctime)s]  - %(name)s - %(levelname)s - %(message)s')
    b.setLevel(20)
    b.info("testing")
