# -*- coding: utf-8 -*-
import os
import sys
from chatbridgereforged_mc.__init__ import main

if __name__ == '__main__':
    if os.path.isdir(sys.argv[0]):
        os.chdir(sys.argv[0])
    main()
