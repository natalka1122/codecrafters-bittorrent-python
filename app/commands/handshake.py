import socket

from app.const import MY_ID
from app.logging_config import get_logger
from app.packets import HandshakePacket
from app.torrent_file import TorrentFile

logger = get_logger(__name__)


def print_peer_id(filename: str, peer: str) -> str:  # noqa: WPS210
    with open(filename, "rb") as file:
        content_bytes = file.read()
    torrent_file = TorrentFile.from_bytes(content_bytes)
    logger.debug(f"torrent_file = {torrent_file}")

    # No need for async, single process
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    host, port = peer.split(":")
    s.connect((host, int(port)))
    handshake = HandshakePacket(torrent_file.info_hash, MY_ID)
    s.sendall(handshake.to_bytes)
    response = s.recv(1024)
    logger.info(f"response = {response!r}")
    s.close()
    peer_id = HandshakePacket.from_bytes(response).peer_id
    return f"Peer ID: {peer_id}"
