import asyncio

from app.logging_config import get_logger
from app.peer.peer import Peer
from app.torrent_file import TorrentFile

logger = get_logger(__name__)


def print_peer_id(filename: str, peer_str: str) -> str:  # noqa: WPS210
    with open(filename, "rb") as file:
        content_bytes = file.read()
    torrent_file = TorrentFile.from_bytes(content_bytes)
    logger.debug(f"torrent_file = {torrent_file}")

    ip, port = peer_str.split(":")
    peer = Peer(ip=ip, port=int(port), info_hash=torrent_file.info_hash)
    peer_id = asyncio.run(peer.handshake())
    return f"Peer ID: {peer_id}"
