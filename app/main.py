import argparse
import sys
from typing import Any, Optional

from app.bencode import Bencode, Dict, Integer, String
from app.const import Command
from app.logging_config import get_logger, setup_logging

setup_logging(level="DEBUG", console_logs_target=sys.stderr)

logger = get_logger(__name__)


def decode_bencode(bencode_bytes: bytes) -> str:
    remainder, bencode = Bencode.from_bytes(bencode_bytes)
    if len(remainder) > 0:
        logger.info(f"remainder = {remainder!r}")
        raise NotImplementedError
    return bencode.to_string


def show_info(filename: str) -> str:
    with open(filename, "rb") as file:
        remainder, content = Bencode.from_bytes(file.read())
    if len(remainder) > 0:
        logger.info(f"remainder = {remainder!r}")
        raise NotImplementedError
    logger.info(f"content = {content}")
    if not isinstance(content, Dict):
        logger.error(f"type(content) = {type(content)}")
        raise NotImplementedError
    announce: Optional[Bencode[Any]] = content.data.get("announce")
    if not isinstance(announce, String):
        logger.error(f"type(announce) = {type(announce)}")
        raise NotImplementedError
    info: Optional[Bencode[Any]] = content.data.get("info")
    if not isinstance(info, Dict):
        logger.error(f"type(info) = {type(info)}")
        raise NotImplementedError
    length: Optional[Bencode[Any]] = info.data.get("length")
    if not isinstance(length, Integer):
        logger.error(f"type(length) = {type(length)}")
        raise NotImplementedError
    result: list[str] = [f"Tracker URL: {announce.data.decode()}", f"Length: {length.data}"]
    return "\n".join(result)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparser = subparsers.add_parser(Command.DECODE, help="Decode a given string")
    subparser.add_argument("string", help="String to work with")
    subparser = subparsers.add_parser(
        Command.INFO, help=" print information about the torrent file"
    )
    subparser.add_argument("torrent_file", help="Torrent file to work with")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    match args.command:
        case Command.DECODE:
            result = decode_bencode(args.string.encode())
        case Command.INFO:
            result = show_info(args.torrent_file)
        case _:
            logger.error(f"Not implemented command = {args.command}")
            return
    sys.stdout.write(result)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
