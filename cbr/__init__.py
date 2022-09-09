__version__ = "v20220909"

import os

if not os.path.exists('config'):
    os.mkdir('config')
if not os.path.exists('logs'):
    os.mkdir('logs')
if not os.path.exists('plugins'):
    os.mkdir('plugins')
