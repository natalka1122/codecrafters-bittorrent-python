import re
from typing import Any
from urllib.parse import unquote

import requests

from app.bencode import Bencode, Dict, String
from app.const import MY_ID, PEER_ID_SIZE_BYTES
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


class MagnetLink:
    def __init__(self, magnet_link: str) -> None:
        match = re.match(
            r"magnet:\?xt=urn:btih:(?P<hash>[\w]{40})&dn=(?P<filename>[\w\.]+)&tr=(?P<tracker>[\w%-:\.]+)",
            magnet_link,
        )
        if match is None:
            raise NotImplementedError
        self.info_hash_hex = match.groupdict()["hash"]
        self.info_hash = bytes.fromhex(self.info_hash_hex)
        self.tracker_url = unquote(match.groupdict()["tracker"])
        logger.info(f"MagnetLink = {self.__dict__}")

    # no async since no parallel processes exist yet
    def get_peers(self) -> list[tuple[str, int]]:  # noqa: WPS210
        params: dict[str, Any] = {
            "info_hash": self.info_hash,
            "peer_id": MY_ID,
            "port": 6881,
            "uploaded": 0,
            "downloaded": 0,
            "left": 1,
            "compact": 1,
        }
        remainder, response = Bencode.from_bytes(
            _fetch(self.tracker_url, params=params)
        )
        if len(remainder) > 0:
            logger.error(f"remainder = {remainder!r}")
            raise NotImplementedError
        if not isinstance(response, Dict):
            logger.error(f"response = {type(response)} {response}")
            raise NotImplementedError
        logger.info(f"response = {response}")
        peers = response.data.get("peers")
        if not isinstance(peers, String):
            logger.error(f"type(peers) = {type(peers)}")
            raise NotImplementedError
        result: list[tuple[str, int]] = []
        index = 0
        for index in range(0, len(peers.data), PEER_ID_SIZE_BYTES):
            peer = _read_peer(peers.data[index : index + PEER_ID_SIZE_BYTES])
            result.append(peer)
        return result
