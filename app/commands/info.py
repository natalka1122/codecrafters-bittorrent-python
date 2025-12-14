from app.logging_config import get_logger
from app.service_func import hex20
from app.torrent_file import TorrentFile

logger = get_logger(__name__)


def print_info(filename: str) -> str:
    with open(filename, "rb") as file:
        content_bytes = file.read()
    torrent_file = TorrentFile.from_bytes(content_bytes)
    result: list[str] = [
        f"Tracker URL: {torrent_file.announce}",
        f"Length: {torrent_file.length}",
        f"Info Hash: {torrent_file.info_hash_hex}",
        f"Piece Length: {torrent_file.piece_length}",
        "Piece Hashes:",
    ]
    result += list(map(hex20, torrent_file.piece_hashes))
    return "\n".join(result)
