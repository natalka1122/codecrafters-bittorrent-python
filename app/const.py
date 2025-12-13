from enum import StrEnum


class Command(StrEnum):
    DECODE = "decode"
    INFO = "info"
    PEERS = "peers"


STRING_DELIMITER = b":"
INTEGER_START = b"i"
LIST_START = b"l"
DICT_START = b"d"
BENCODE_END = b"e"

PIECE_SIZE = 20
PEER_SIZE = 6
