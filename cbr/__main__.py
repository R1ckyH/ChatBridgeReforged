"""
Entry for CBR
"""
from cbr.cbr_server import CBRServer


def main():
    server = CBRServer()
    server.start()


if __name__ == "__main__":
    main()
