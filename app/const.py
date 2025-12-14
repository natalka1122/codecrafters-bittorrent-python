from enum import IntEnum, StrEnum, auto
from typing import Awaitable, Callable


class Command(StrEnum):
    DECODE = "decode"
    INFO = "info"
    PEERS = "peers"
    HANDSHAKE = "handshake"
    DOWNLOAD_PIECE = "download_piece"
    DOWNLOAD = "download"
    MAGNET_PARSE = "magnet_parse"
    MAGNET_HANDSHAKE = "magnet_handshake"
    MAGNET_INFO = "magnet_info"
    MAGNET_DOWNLOAD_PIECE = "magnet_download_piece"
    MAGNET_DOWNLOADE = "magnet_download"


class MessageType(IntEnum):
    KEEPALIVE = auto()
    CHOKE = 0
    UNCHOKE = 1
    INTERESTED = 2
    NOT_INTERESTED = 3
    HAVE = 4
    BITFIELD = 5
    REQUEST = 6
    PIECE = 7
    CANCEL = 8


MY_ID = b"natalka112natalka112"
BITTORENT_PROTOCOL = b"BitTorrent protocol"
STRING_DELIMITER = b":"
INTEGER_START = b"i"
LIST_START = b"l"
DICT_START = b"d"
BENCODE_END = b"e"

PIECE_SIZE = 20
PEER_SIZE = 6
BLOCK_SIZE = 16 * 1024
WINDOW_SIZE = 10

StreamExactly = Callable[[int], Awaitable[bytes]]
