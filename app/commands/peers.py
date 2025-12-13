from typing import Any

import requests

from app.bencode import Bencode, Dict, String
from app.const import MY_ID, PEER_SIZE
from app.logging_config import get_logger
from app.torrent_file import TorrentFile

logger = get_logger(__name__)


def _fetch(url: str, params: dict[str, Any]) -> bytes:
    r = requests.get(url, params=params, timeout=10)
    r.raise_for_status()
    return r.content


def _make_ip(raw_data: bytes) -> str:
    if len(raw_data) != 6:
        logger.error(f"raw_data = {len(raw_data)} {raw_data!r}")
        raise NotImplementedError
    result = ".".join(map(str, raw_data[:4]))
    return result + ":" + str(int.from_bytes(raw_data[4:]))


def show_peers(filename: str) -> str:
    with open(filename, "rb") as file:
        content_bytes = file.read()
    torrent_file = TorrentFile.from_bytes(content_bytes)
    params: dict[str, Any] = {
        "info_hash": torrent_file.info_hash,
        "peer_id": MY_ID,
        "port": 6881,
        "uploaded": 0,
        "downloaded": 0,
        "left": torrent_file.length,
        "compact": 1,
    }
    remainder, response = Bencode.from_bytes(_fetch(torrent_file.announce, params=params))
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
    result: list[str] = []
    index = 0
    while index < len(peers.data):
        current: str = _make_ip(peers.data[index : index + PEER_SIZE])
        result.append(current)
        index += PEER_SIZE
    return "\n".join(result)
