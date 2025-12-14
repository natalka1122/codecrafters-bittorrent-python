class NeedMoreBytesError(Exception):
    """NeedMoreBytesError"""


class WrongBencodeFormatError(Exception):
    """WrongBencodeFormatError"""


class ReaderClosedError(Exception):
    """ReaderClosedError"""


class WrongPacketFormatError(Exception):
    """WrongPacketFormatError"""


class PeerCommunicationError(Exception):
    """PeerCommunicationError"""
