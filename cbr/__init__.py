__version__ = "v20220908"

import os

if not os.path.exists('config'):
    os.mkdir('config')
if not os.path.exists('plugins'):
    os.mkdir('plugins')
