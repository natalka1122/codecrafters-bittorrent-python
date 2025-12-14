from app.bencode import Bencode
from app.logging_config import get_logger

logger = get_logger(__name__)


def print_decode(bencode_bytes: bytes) -> str:
    remainder, bencode = Bencode.from_bytes(bencode_bytes)
    if len(remainder) > 0:
        logger.error(f"remainder = {remainder!r}")
        raise NotImplementedError
    return bencode.to_string
