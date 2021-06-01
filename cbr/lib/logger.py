import logging
import traceback

from os import path, mkdir

log_file = 'logs'
log_path = log_file + "/lastest.log"


class CBRLogger(logging.getLoggerClass()):
    def __init__(self, name, config):
        super().__init__(name)
        if config.getdata():
            self.debug_all = bool(config.data['debug']['all'])
        else:
            self.debug_all = True
        self.setup()

    def formatter(self):
        return logging.Formatter('[%(name)s] [%(asctime)s] [%(threadName)s/%(levelname)s]: %(message)s', datefmt='%H:%M:%S')

    def setup(self):
        self.checkfile()
        self.stdout_handler = logging.StreamHandler()
        self.file_handler = logging.FileHandler(log_path)
        self.stdout_handler.setFormatter(self.formatter())
        self.file_handler.setFormatter(self.formatter())
        self.addHandler(self.stdout_handler)
        self.addHandler(self.file_handler)
        if self.debug_all == True:
            self.setLevel(logging.DEBUG)
        else:
            self.setLevel(logging.INFO)
    
    def checkfile(self):
        if not path.exists(log_file):
            mkdir(log_file)

    def bug(self, exit_now = True, error = False):
        for line in traceback.format_exc().splitlines():
            if error == True:
                self.error(line, exc_info = False)
            else:
                self.debug(line, exc_info = False)
        if exit_now:
            if self.level > logging.DEBUG and not error:
                self.error('ERROR exist, use debug mode for more information')
            exit(0)


if __name__ == '__main__':
    logging.setLoggerClass(CBRLogger)
    b = CBRLogger("CBR")
    logging.basicConfig(level = logging.INFO, format = '[%(asctime)s]  - %(name)s - %(levelname)s - %(message)s')
    b.setLevel(20)
    b.info("testing")
