from enum import StrEnum


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


MY_ID = b"natalka112natalka112"
STRING_DELIMITER = b":"
INTEGER_START = b"i"
LIST_START = b"l"
DICT_START = b"d"
BENCODE_END = b"e"

PIECE_SIZE = 20
PEER_SIZE = 6
