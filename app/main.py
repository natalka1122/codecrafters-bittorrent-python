import argparse
import sys

from app.const import Command
from app.logging_config import get_logger, setup_logging

setup_logging(level="DEBUG", console_logs_target=sys.stderr)

logger = get_logger(__name__)


def decode_bencode(bencoded_value: bytes) -> bytes:
    if bencoded_value[0] == ord("i"):
        result = b""
        index = 1
        while index < len(bencoded_value) and bencoded_value[index] != ord("e"):
            result += bencoded_value[index : index + 1]
            index += 1
        return result
    elif chr(bencoded_value[0]).isdigit():
        first_colon_index = bencoded_value.find(b":")
        if first_colon_index == -1:
            raise ValueError("Invalid encoded value")
        return b'"' + bencoded_value[first_colon_index + 1 :] + b'"'
    else:
        raise NotImplementedError("Only strings are supported at the moment")


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
            command = decode_bencode
        case _:
            logger.error(f"Not implemented command = {args.command}")
            return
    result = command(args.string.encode())
    sys.stdout.write(result.decode())
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
