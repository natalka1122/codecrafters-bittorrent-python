import argparse
import sys

from app.commands.decode import decode_bencode
from app.commands.handshake import show_handshake
from app.commands.info import show_info
from app.commands.peers import show_peers
from app.const import Command
from app.logging_config import get_logger, setup_logging

setup_logging(level="DEBUG", console_logs_target=sys.stderr)

logger = get_logger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparser = subparsers.add_parser(Command.DECODE, help="Decode a given string")
    subparser.add_argument("string", help="String to work with")
    subparser = subparsers.add_parser(Command.INFO, help="Print information about the torrent file")
    subparser.add_argument("torrent_file", help="Torrent file to work with")
    subparser = subparsers.add_parser(Command.PEERS, help="Discover peers")
    subparser.add_argument("torrent_file", help="Torrent file to work with")
    subparser = subparsers.add_parser(Command.HANDSHAKE, help="Peer handshake")
    subparser.add_argument("torrent_file", help="Torrent file to work with")
    subparser.add_argument("peer", help="PeerIP:Port")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    match args.command:
        case Command.DECODE:
            result = decode_bencode(args.string.encode())
        case Command.INFO:
            result = show_info(args.torrent_file)
        case Command.PEERS:
            result = show_peers(args.torrent_file)
        case Command.HANDSHAKE:
            result = show_handshake(args.torrent_file, args.peer)
        case _:
            logger.error(f"Not implemented command = {args.command}")
            return
    sys.stdout.write(result)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
