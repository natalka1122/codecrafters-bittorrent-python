import socket

from app.const import MY_ID
from app.logging_config import get_logger
from app.service_func import hex20
from app.torrent_file import TorrentFile

logger = get_logger(__name__)


def show_handshake(filename: str, peer: str) -> str:
    with open(filename, "rb") as file:
        content_bytes = file.read()
    torrent_file = TorrentFile.from_bytes(content_bytes)
    logger.debug(f"torrent_file = {torrent_file}")

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    host, port = peer.split(":")
    s.connect((host, int(port)))
    handshake = bytes([19]) + b"BitTorrent protocol" + bytes(8) + torrent_file.info_hash + MY_ID
    s.sendall(handshake)
    response = s.recv(1024)
    logger.info(f"response = {response!r}")
    s.close()
    peer_id_bytes = response[-20:]
    peer_id = hex20(peer_id_bytes)
    return f"Peer ID: {peer_id}"
