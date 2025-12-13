import hashlib
from dataclasses import dataclass
from typing import Any, Optional

from app.bencode import Bencode, Dict, Integer, String
from app.logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class TorrentFile:
    announce: str
    info: Dict
    length: int
    piece_length: int
    pieces: bytes

    @property
    def info_hash_hex(self) -> str:
        return hashlib.sha1(self.info.to_bytes).hexdigest()

    @property
    def info_hash(self) -> bytes:
        return hashlib.sha1(self.info.to_bytes).digest()

    @classmethod
    def from_bytes(cls, raw_data: bytes) -> "TorrentFile":
        remainder, content = Bencode.from_bytes(raw_data)
        if len(remainder) > 0:
            logger.info(f"remainder = {remainder!r}")
            raise NotImplementedError
        logger.info(f"content = {content}")
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
        piece_length: Optional[Bencode[Any]] = info.data.get("piece length")
        if not isinstance(piece_length, Integer):
            logger.error(f"type(piece_length) = {type(piece_length)}")
            raise NotImplementedError
        pieces: Optional[Bencode[Any]] = info.data.get("pieces")
        if not isinstance(pieces, String):
            logger.error(f"type(piece_length) = {type(pieces)}")
            raise NotImplementedError
        return TorrentFile(
            announce=announce.data.decode(),
            info=info,
            length=length.data,
            piece_length=piece_length.data,
            pieces=pieces.data,
        )
