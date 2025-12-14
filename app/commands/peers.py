from app.logging_config import get_logger
from app.torrent_file import TorrentFile

logger = get_logger(__name__)


def print_peers(filename: str) -> str:  # noqa: WPS210
    with open(filename, "rb") as file:
        content_bytes = file.read()
    torrent_file = TorrentFile.from_bytes(content_bytes)
    peers = torrent_file.get_peers()
    return "\n".join(f"{ip}:{port}" for ip, port in peers)
