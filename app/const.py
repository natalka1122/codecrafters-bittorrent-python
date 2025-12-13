from enum import StrEnum


class Command(StrEnum):
    DECODE = "decode"
    INFO = "info"
    PEERS = "peers"


STRING_DELIMITER = b":"
INTEGER_START = b"i"
LIST_START = b"l"
BENCODE_END = b"e"
