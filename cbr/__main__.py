"""
Entry for CBR
"""
import sys

from cbr.cbr_server import CBRServer


def main():
    server = CBRServer()
    server.start()


if __name__ == "__main__":
    sys.exit(main())
