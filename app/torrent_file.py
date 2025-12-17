import hashlib
from dataclasses import dataclass
from typing import Any, Optional

import requests

from app.bencode import Bencode, BencodeAny, Dict, Integer, String
from app.const import MY_ID, PEER_SIZE, PIECE_SIZE
from app.logging_config import get_logger

logger = get_logger(__name__)


def _fetch(url: str, params: dict[str, Any]) -> bytes:
    r = requests.get(url, params=params, timeout=10)  # type: ignore
    r.raise_for_status()
    return bytes(r.content)


def _read_peer(raw_data: bytes) -> tuple[str, int]:
    if len(raw_data) != 6:
        logger.error(f"raw_data = {len(raw_data)} {raw_data!r}")
        raise NotImplementedError
    host = ".".join(map(str, raw_data[:4]))
    port = int.from_bytes(raw_data[4:])
    return host, port


@dataclass
class TorrentFile:
    announce: str
    info: Dict
    length: int
    piece_length: int
    piece_hashes: list[bytes]

    # no async since no parallel processes exist yet
    def get_peers(self) -> list[tuple[str, int]]:  # noqa: WPS210
        params: dict[str, Any] = {
            "info_hash": self.info_hash,
            "peer_id": MY_ID,
            "port": 6881,
            "uploaded": 0,
            "downloaded": 0,
            "left": self.length,
            "compact": 1,
        }
        remainder, response = Bencode.from_bytes(_fetch(self.announce, params=params))
        if len(remainder) > 0:
            logger.info(f"remainder = {remainder!r}")
            raise NotImplementedError
        logger.info(f"response = {response}")
        if not isinstance(response, Dict):
            logger.error(f"type(response) = {type(response)}")
            raise NotImplementedError
        peers = response.data.get("peers")
        if not isinstance(peers, String):
            logger.error(f"type(peers) = {type(peers)}")
            raise NotImplementedError
        result: list[tuple[str, int]] = []
        index = 0
        while index < len(peers.data):
            peer = _read_peer(peers.data[index : index + PEER_SIZE])
            result.append(peer)
            index += PEER_SIZE
        # return result
        return [result[0]]

    @property
    def info_hash_hex(self) -> str:
        return hashlib.sha1(self.info.to_bytes).hexdigest()  # noqa: DUO130

    @property
    def info_hash(self) -> bytes:
        return hashlib.sha1(self.info.to_bytes).digest()  # noqa: DUO130

    @classmethod
    def from_bytes(cls, raw_data: bytes) -> "TorrentFile":  # noqa: WPS210, WPS238
        remainder, content = Bencode.from_bytes(raw_data)
        if len(remainder) > 0:
            logger.info(f"remainder = {remainder!r}")
            raise NotImplementedError
        logger.info(f"content = {content}")
        announce: Optional[BencodeAny] = content.data.get("announce")
        if not isinstance(announce, String):
            logger.error(f"type(announce) = {type(announce)}")
            raise NotImplementedError
        info: Optional[BencodeAny] = content.data.get("info")
        if not isinstance(info, Dict):
            logger.error(f"type(info) = {type(info)}")
            raise NotImplementedError
        length: Optional[BencodeAny] = info.data.get("length")
        if not isinstance(length, Integer):
            logger.error(f"type(length) = {type(length)}")
            raise NotImplementedError
        piece_length: Optional[BencodeAny] = info.data.get("piece length")
        if not isinstance(piece_length, Integer):
            logger.error(f"type(piece_length) = {type(piece_length)}")
            raise NotImplementedError
        pieces_bencode: Optional[BencodeAny] = info.data.get("pieces")
        if not isinstance(pieces_bencode, String):
            logger.error(f"type(piece_length) = {type(pieces_bencode)}")
            raise NotImplementedError
        pieces_bytes = pieces_bencode.data
        piece_hashes: list[bytes] = [
            pieces_bytes[i : i + PIECE_SIZE]
            for i in range(0, len(pieces_bytes), PIECE_SIZE)  # noqa: WPS221
        ]
        return TorrentFile(
            announce=announce.data.decode(),
            info=info,
            length=length.data,
            piece_length=piece_length.data,
            piece_hashes=piece_hashes,
        )
