"""
Entry for CBR
"""
import trio

from cbr.cbr_server import CBRServer


def main():
    server = CBRServer()
    trio.run(server.start)


if __name__ == "__main__":
    main()
