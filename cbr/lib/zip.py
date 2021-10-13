import os
import time
import zipfile

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from cbr.lib.logger import CBRLogger


class Compressor:
    def __init__(self, logger: 'CBRLogger'):
        self.logger = logger

    def zip_log(self, file_name, max_size):
        self.logger.debug(f"Start zip file: '{file_name}'", "CBR")
        path = f'logs/{file_name}'
        if os.path.isfile(path):
            file_size = (os.path.getsize(path)/1024)
            if file_size > max_size:
                if file_name == 'chat.log':
                    zip_name = 'logs/chat_'
                else:
                    zip_name = 'logs/'
                zip_name = zip_name + time.strftime('%Y-%m-%d_%H%M%S', time.localtime(os.path.getmtime(path))) + '.zip'
                with zipfile.ZipFile(zip_name, 'w') as zipper:
                    zipper.write(path, arcname=file_name, compress_type=zipfile.ZIP_DEFLATED)
                    os.remove(path)
                self.logger.debug("zipped old file")
            else:
                self.logger.debug("Not enough size to zip")
        else:
            self.logger.debug("Nothing to zip")
