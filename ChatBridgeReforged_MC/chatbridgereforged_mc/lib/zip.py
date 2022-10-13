import os
import time
import zipfile

from typing import  TYPE_CHECKING


if TYPE_CHECKING:
    from chatbridgereforged_mc.lib.config import Config
    from chatbridgereforged_mc.lib.logger import CBRLogger


class Compressor:
    def __init__(self, logger: "CBRLogger", config: "Config"):
        self.logger = logger
        self.config = config

    def zip_log(self, file_path, max_size):
        self.logger.debug(f"Start zip file: '{os.path.basename(file_path)}'")
        if os.path.isfile(file_path):
            file_size = (os.path.getsize(file_path)/1024)
            if file_size > max_size:
                if file_path == self.config.chat_path:
                    zip_name = "logs/CBR_chat"
                else:
                    zip_name = "logs/CBR_"
                zip_name += time.strftime("%Y-%m-%d_%H%M%S", time.localtime(os.path.getmtime(file_path))) + ".zip"
                with zipfile.ZipFile(zip_name, "w") as zipper:
                    zipper.write(file_path, arcname=os.path.basename(file_path), compress_type=zipfile.ZIP_DEFLATED)
                    os.remove(file_path)
                self.logger.debug("zipped old file")
            else:
                self.logger.debug("Not enough size to zip")
        else:
            self.logger.debug("Nothing to zip")
