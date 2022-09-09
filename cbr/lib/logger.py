import logging
import sys
import traceback
from typing import Optional

from cbr.lib.typeddicts import TypedDebugConfig

DEFAULT_LOG_PATH = "logs"
LOG_FILE = "/latest.log"
CHAT_LOG_FILE = "/chat.log"
DEFAULT_DEBUG_CONFIG: TypedDebugConfig = {
    "all": False, "CBR": False, "plugin": False
}

logger_black_list = ["ping", "Result of", "- ", "Client ", "Ping client", "Send Command", "Unknown "]  # File handler
logger_black_arg2 = ["joined", "left"]  # File handler


class StdoutFilter(logging.Filter):
    def __init__(self, chat: bool, split_log: bool):
        super().__init__()
        self.chat = chat
        self.split_log = split_log

    def filter(self, record: logging.LogRecord):
        msg = record.getMessage()
        if self.split_log:
            if self.chat ^ (record.levelname != "CHAT"):
                return False
        args = msg.split(" ")
        # print(record.levelname)
        if len(args) == 4:
            if args[2] in logger_black_arg2:
                return False
        for i in logger_black_list:
            if msg.startswith(i):
                return False
        return True


class CBRLogger(logging.getLoggerClass()):
    def __init__(self, name: str):
        super().__init__(name)
        self.path = DEFAULT_LOG_PATH
        self.debug_config = DEFAULT_DEBUG_CONFIG
        logging.addLevelName(21, "CHAT")
        sh = logging.StreamHandler(sys.stdout)
        sh.setFormatter(self.__formatter("%H:%M:%S"))
        sh.setLevel(logging.DEBUG)
        self.addHandler(sh)

    @staticmethod
    def __formatter(self, datefmt: Optional[str] = None) -> logging.Formatter:
        return logging.Formatter(
            "[%(name)s] [%(asctime)s] [%(threadName)s/%(levelname)s]: %(message)s",
            datefmt=datefmt
        )

    def __file_handler(self, chat: bool, split_log: bool) -> logging.FileHandler:
        if chat:
            path = self.path + CHAT_LOG_FILE
        else:
            path = self.path + LOG_FILE
        fh = logging.FileHandler(path, encoding="utf-8")
        fh.setFormatter(self.__formatter("%d-%m-%Y %H:%M:%S"))
        fh.addFilter(StdoutFilter(chat, split_log))
        fh.setLevel(logging.DEBUG)
        return fh

    def setup(self, debug_config: TypedDebugConfig, split_log: bool, path=DEFAULT_LOG_PATH) -> None:
        self.path = path
        self.debug_config = debug_config
        self.addHandler(self.__file_handler(False, split_log))
        if split_log:
            self.addHandler(self.__file_handler(True, split_log))

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
    logging.basicConfig(level=logging.DEBUG, format="[%(asctime)s]  - %(name)s - %(levelname)s - %(message)s")
    b.setLevel(logging.DEBUG)
    b.info("testing")
