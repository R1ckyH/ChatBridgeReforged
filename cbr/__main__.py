"""
Entry for CBR
"""
import trio

from cbr import cbr_server


def main():
    trio.run(cbr_server.start)  # type: ignore


if __name__ == '__main__':
    main()
