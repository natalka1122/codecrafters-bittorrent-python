import argparse
import sys
from typing import Any

import requests

from app.bencode import Bencode, Dict, String
from app.const import PEER_SIZE, PIECE_SIZE, Command
from app.logging_config import get_logger, setup_logging
from app.torrent_file import TorrentFile

setup_logging(level="DEBUG", console_logs_target=sys.stderr)

logger = get_logger(__name__)


def _hex(number: int) -> str:
    result = hex(number)[2:]
    return "0" * (2 - len(result)) + result


def _fetch(url: str, params: dict[str, Any]) -> bytes:
    r = requests.get(url, params=params, timeout=10)
    r.raise_for_status()
    return r.content


def _make_ip(raw_data: bytes) -> str:
    if len(raw_data) != 6:
        logger.error(f"raw_data = {len(raw_data)} {raw_data!r}")
        raise NotImplementedError
    result = ".".join(map(str, raw_data[:4]))
    return result + ":" + str(int.from_bytes(raw_data[4:]))


def decode_bencode(bencode_bytes: bytes) -> str:
    remainder, bencode = Bencode.from_bytes(bencode_bytes)
    if len(remainder) > 0:
        logger.error(f"remainder = {remainder!r}")
        raise NotImplementedError
    return bencode.to_string


def show_info(filename: str) -> str:
    with open(filename, "rb") as file:
        content_bytes = file.read()
    torrent_file = TorrentFile.from_bytes(content_bytes)
    result: list[str] = [
        f"Tracker URL: {torrent_file.announce}",
        f"Length: {torrent_file.length}",
        f"Info Hash: {torrent_file.info_hash_hex}",
        f"Piece Length: {torrent_file.piece_length}",
        "Piece Hashes:",
    ]
    pieces: bytes = torrent_file.pieces
    index = 0
    logger.debug(pieces)
    while index < len(pieces):
        current: str = "".join(map(_hex, pieces[index : index + PIECE_SIZE]))
        result.append(current)
        index += PIECE_SIZE
    return "\n".join(result)


def show_peers(filename: str) -> str:
    with open(filename, "rb") as file:
        content_bytes = file.read()
    torrent_file = TorrentFile.from_bytes(content_bytes)
    params: dict[str, Any] = {
        "info_hash": torrent_file.info_hash,
        "peer_id": b"natalka112natalka112",
        "port": 6881,
        "uploaded": 0,
        "downloaded": 0,
        "left": torrent_file.length,
        "compact": 1,
    }
    remainder, response = Bencode.from_bytes(_fetch(torrent_file.announce, params=params))
    if len(remainder) > 0:
        logger.info(f"remainder = {remainder!r}")
        raise NotImplementedError
    logger.info(f"response = {response}")
    if not isinstance(response, Dict):
        logger.error(f"type(response) = {type(response)}")
        raise NotImplementedError
    peers = response.data.get("peers")
    if not isinstance(peers, String):
        logger.error(f"type(peers) = {type(peers)}")
        raise NotImplementedError
    result: list[str] = []
    index = 0
    while index < len(peers.data):
        current: str = _make_ip(peers.data[index : index + PEER_SIZE])
        result.append(current)
        index += PEER_SIZE
    return "\n".join(result)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparser = subparsers.add_parser(Command.DECODE, help="Decode a given string")
    subparser.add_argument("string", help="String to work with")
    subparser = subparsers.add_parser(Command.INFO, help="Print information about the torrent file")
    subparser.add_argument("torrent_file", help="Torrent file to work with")
    subparser = subparsers.add_parser(Command.PEERS, help="Discover peers")
    subparser.add_argument("torrent_file", help="Torrent file to work with")
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
        case _:
            logger.error(f"Not implemented command = {args.command}")
            return
    sys.stdout.write(result)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
