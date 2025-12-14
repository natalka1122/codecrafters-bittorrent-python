import argparse
import sys

from app.commands.decode import print_decode
from app.commands.download import download, download_piece
from app.commands.handshake import print_peer_id
from app.commands.info import print_info
from app.commands.peers import print_peers
from app.const import Command
from app.logging_config import get_logger, setup_logging

setup_logging(level="DEBUG", console_logs_target=sys.stderr)

logger = get_logger(__name__)


def parse_args() -> argparse.Namespace:  # noqa: WPS213
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparser = subparsers.add_parser(Command.DECODE, help="Decode a given string")
    subparser.add_argument("string", help="String to work with")

    subparser = subparsers.add_parser(Command.INFO, help="Print information about the torrent file")
    subparser.add_argument("torrent_file", help="Torrent file to work with")  # noqa: WPS204, WPS226

    subparser = subparsers.add_parser(Command.PEERS, help="Discover peers")
    subparser.add_argument("torrent_file", help="Torrent file to work with")  # noqa: WPS226

    subparser = subparsers.add_parser(Command.HANDSHAKE, help="Peer handshake")
    subparser.add_argument("torrent_file", help="Torrent file to work with")
    subparser.add_argument("peer", help="PeerIP:Port")

    subparser = subparsers.add_parser(Command.DOWNLOAD_PIECE, help="Download a piece")
    subparser.add_argument("-o", "--output", required=True, help="Output piece path")
    subparser.add_argument("torrent_file", help="Torrent file to work with")
    subparser.add_argument("piece_index", type=int, help="Piece index")

    subparser = subparsers.add_parser(Command.DOWNLOAD, help="Download the whole file")
    subparser.add_argument("-o", "--output", required=True, help="Output file path")
    subparser.add_argument("torrent_file", help="Torrent file to work with")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    match args.command:
        case Command.DECODE:
            result = print_decode(args.string.encode())
        case Command.INFO:
            result = print_info(args.torrent_file)
        case Command.PEERS:
            result = print_peers(args.torrent_file)
        case Command.HANDSHAKE:
            result = print_peer_id(args.torrent_file, args.peer)
        case Command.DOWNLOAD_PIECE:
            download_piece(args.output, args.torrent_file, args.piece_index)
            result = ""
        case Command.DOWNLOAD:
            download(args.output, args.torrent_file)
            result = ""
        case _:
            logger.error(f"Not implemented command = {args.command}")
            return
    sys.stdout.write(result)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
