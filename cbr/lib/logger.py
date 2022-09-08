import logging
import sys
import traceback

from os import path, mkdir

from cbr.lib.typeddicts import TypedDebugConfig

LOG_FILE = "logs"
LOG_PATH = LOG_FILE + "/latest.log"
CHAT_LOG_PATH = LOG_FILE + "/chat.log"
DEFAULT_DEBUG_CONFIG: TypedDebugConfig = {"all": False, "CBR": False, "plugin": False}

logger_black_list = ["ping", "Result of", "- ", "Client ", "Ping client", "Send Command", "Unknown "]  # File handler
logger_black_arg2 = ["joined", "left"]  # File handler


class StdoutFilter(logging.Filter):
    def __init__(self, chat=False, split_log=True):
        super().__init__()
        self.chat = chat
        self.split_log = split_log

    def filter(self, record: logging.LogRecord):
        msg = record.getMessage()
        if self.split_log:
            if self.chat:
                if record.levelname != "CHAT":
                    return False
            elif record.levelname == "CHAT":
                return False
        args = msg.split(" ")
        # print(record.levelname)
        if len(args) == 4:
            for i in range(len(logger_black_arg2)):
                if args[2] == logger_black_arg2[i]:
                    return False
        for i in range(len(logger_black_list)):
            if msg.startswith(logger_black_list[i]):
                return False
        return True


class CBRLogger(logging.getLoggerClass()):
    def __init__(self, name):
        if not path.exists(LOG_FILE):
            mkdir(LOG_FILE)
        super().__init__(name)
        self.file_handler = None
        self.stdout_handler = logging.StreamHandler(sys.stdout)
        self.debug_config = DEFAULT_DEBUG_CONFIG
        self.stdout_handler.setFormatter(self.formatter("%H:%M:%S"))
        self.addHandler(self.stdout_handler)
        logging.addLevelName(21, "CHAT")
        self.setLevel(logging.DEBUG)

    @staticmethod
    def formatter(date=None):
        return logging.Formatter("[%(name)s] [%(asctime)s] [%(threadName)s/%(levelname)s]: %(message)s", datefmt=date)

    def setup(self, chat=False, split_log=True):
        if chat:
            path_name = CHAT_LOG_PATH
        else:
            path_name = LOG_PATH
        self.file_handler = logging.FileHandler(path_name, encoding="utf-8")
        self.file_handler.setFormatter(self.formatter("%d-%m-%Y %H:%M:%S"))
        self.file_handler.addFilter(StdoutFilter(chat, split_log))
        self.addHandler(self.file_handler)
        self.setLevel(logging.DEBUG)

    def bug(self, error=True, exit_now=False):
        for line in traceback.format_exc().splitlines():
            if error:
                self.error(line, exc_info=False)
            else:
                self.debug(line, "CBR")
        if exit_now:
            if self.level > logging.DEBUG and not error:
                self.error("ERROR exist, use debug mode for more information")
            exit(0)

    def debug(self, msg, module="all", *args) -> None:
        if self.debug_config[module] or self.debug_config["all"]:
            super().debug(msg, *args)

    def chat(self, msg):
        self.log(21, msg)

    # no use
    """def restart_all(self):
        self.removeHandler(self.stdout_handler)
        self.removeHandler(self.file_handler)
        print(self.hasHandlers())
        self.addHandler(self.stdout_handler)
        self.addHandler(self.file_handler)"""

    def force_debug(self, module="all"):
        self.debug_config[module] = not self.debug_config[module]
        self.info(f"- Force debug mode of {module}: {self.debug_config[module]}")
        self.debug("test", "CBR")


if __name__ == "__main__":
    logging.setLoggerClass(CBRLogger)
    b = CBRLogger("CBR")
    logging.basicConfig(level=logging.INFO, format="[%(asctime)s]  - %(name)s - %(levelname)s - %(message)s")
    b.setLevel(20)
    b.info("testing")
