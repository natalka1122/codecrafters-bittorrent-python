import argparse
import sys

from app.bencode import Bencode
from app.const import Command
from app.logging_config import get_logger, setup_logging

setup_logging(level="DEBUG", console_logs_target=sys.stderr)

logger = get_logger(__name__)


def decode_bencode(bencode_bytes: bytes) -> str:
    remainder, bencode = Bencode.from_bytes(bencode_bytes)
    logger.debug(f"bencode = {bencode} remainder = {remainder!r}")
    return bencode.to_string


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    for cmd in Command:
        subparser = subparsers.add_parser(cmd, help=f"{cmd.capitalize()} a given string")
        subparser.add_argument("string", help="String to work with")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    match args.command:
        case Command.DECODE:
            result = decode_bencode(args.string.encode())
        case _:
            logger.error(f"Not implemented command = {args.command}")
            return
    sys.stdout.write(result)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
