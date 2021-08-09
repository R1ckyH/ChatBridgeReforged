import logging
import sys
import traceback

from os import path, mkdir

log_file = 'logs'
log_path = log_file + "/lastest.log"

logger_black_list = ['ping', 'Result of', '- ', 'Client ', 'Ping client', 'Send Command', 'Unknown ']#for filehandler
logger_black_arg2 = ['joined', 'left']#for filehandler


class StdoutFilter(logging.Filter):
    def filter(self, record : logging.LogRecord):
        msg = record.getMessage()
        args = msg.split(' ')
        #print(record.levelname)
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
    def __init__(self, name, config):
        super().__init__(name)
        if config.getdata():
            self.debug_all = bool(config.data['debug']['all'])
        else:
            self.debug_all = True

    def formatter(self, datefmt = None):
        return logging.Formatter('[%(name)s] [%(asctime)s] [%(threadName)s/%(levelname)s]: %(message)s', datefmt=datefmt)

    def setup(self):
        self.checkfile()
        self.stdout_handler = logging.StreamHandler(sys.stdout)
        self.file_handler = logging.FileHandler(log_path, encoding = 'utf-8')
        self.stdout_handler.setFormatter(self.formatter('%H:%M:%S'))
        self.file_handler.setFormatter(self.formatter('%Y-%m-%d %H:%M:%S'))
        self.file_handler.addFilter(StdoutFilter())
        self.addHandler(self.stdout_handler)
        self.addHandler(self.file_handler)
        self.setLevel(logging.DEBUG)

    def checkfile(self):
        if not path.exists(log_file):
            mkdir(log_file)

    def bug(self, exit_now = True, error = False):
        for line in traceback.format_exc().splitlines():
            if error == True:
                self.error(line, exc_info = False)
            else:
                self.debug(line)
        if exit_now:
            if self.level > logging.DEBUG and not error:
                self.error('ERROR exist, use debug mode for more information')
            exit(0)

    def debug(self, msg) -> None:#thx xd
        if self.debug_all:
            super().debug(msg)
    
    #no use
    '''def restartall(self):
        self.removeHandler(self.stdout_handler)
        self.removeHandler(self.file_handler)
        print(self.hasHandlers())
        self.addHandler(self.stdout_handler)
        self.addHandler(self.file_handler)'''

    def forcedebug(self):
        self.debug_all = not self.debug_all
        self.info(f'- Forcedebug mode: {self.debug_all}')
        self.debug('test')


if __name__ == '__main__':
    logging.setLoggerClass(CBRLogger)
    b = CBRLogger("CBR")
    logging.basicConfig(level = logging.INFO, format = '[%(asctime)s]  - %(name)s - %(levelname)s - %(message)s')
    b.setLevel(20)
    b.info("testing")