import os
import zipfile

from datetime import datetime

from cbr.lib.logger import CBRLogger
from cbr.lib.typeddicts import TypedLogConfig, TypedDebugConfig


class CompressManager:
    def __init__(self, logger: CBRLogger, path: str):
        self.logger = logger
        self.path = path

    def compress_setup_log(self, log_config: TypedLogConfig, debug_config: TypedDebugConfig):
        self.zip_log("latest.log", log_config["size_to_zip"])
        self.logger.setup(debug_config, split_log=log_config["split_log"])
        if log_config["split_log"]:
            self.zip_log("latest.log", log_config["size_to_zip_chat"], "chat_")
            self.logger.setup(debug_config, True)

    def zip_log(self, file_name, max_size, prefix=""):
        self.logger.debug(f"Start zip file: '{file_name}'", "CBR")
        path = f"{self.path}/{file_name}"
        if os.path.isfile(path):
            file_size = (os.path.getsize(path) / 1024)
            if file_size > max_size:
                tm_str = datetime.fromtimestamp(os.path.getmtime(path)).strftime("%Y-%m-%d_%H%M%S")
                zip_name = f"{self.path}/{prefix}{tm_str}.zip"
                with zipfile.ZipFile(zip_name, "w") as zipper:
                    zipper.write(path, arcname=file_name, compress_type=zipfile.ZIP_DEFLATED)
                os.remove(path)
                self.logger.debug(f"Zipped {path} to {zip_name}", "CBR")
            else:
                self.logger.debug("Not enough size to zip", "CBR")
        else:
            self.logger.debug("Nothing to zip", "CBR")
