import os
import zipfile
from datetime import datetime

from cbr.lib.logger import CBRLogger


class Compressor:

    def __init__(
        self,
        logger: CBRLogger,
        path: str,
        max_size: int,
        prefix: str = ""
    ) -> None:
        self.logger = logger
        self.prefix = prefix
        self.path = path
        self.max_size = max_size

    def zip_log(self) -> None:
        self.logger.debug(f"Start zip file: '{self.path}'", "CBR")
        path = f'logs/{self.path}'
        if os.path.isfile(path):
            file_size = (os.path.getsize(path) / 1024)
            if file_size > self.max_size:
                tm_str = datetime.fromtimestamp(
                    os.path.getmtime(path)
                ).strftime('%Y-%m-%d_%H%M%S')
                zip_name = f'logs/{self.prefix}{tm_str}.zip'
                with zipfile.ZipFile(zip_name, 'w') as zipper:
                    zipper.write(
                        path,
                        arcname=self.path,
                        compress_type=zipfile.ZIP_DEFLATED
                    )
                os.remove(path)
                self.logger.debug(f"Zipped {path} to {zip_name}", "CBR")
            else:
                self.logger.debug("Not enough size to zip", "CBR")
        else:
            self.logger.debug("Nothing to zip", "CBR")
