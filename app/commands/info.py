from app.const import PIECE_SIZE
from app.logging_config import get_logger
from app.service_func import hex20
from app.torrent_file import TorrentFile

logger = get_logger(__name__)


def show_info(filename: str) -> str:
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
    pieces: bytes = torrent_file.pieces
    index = 0
    logger.debug(pieces)
    while index < len(pieces):
        current: str = hex20(pieces[index : index + PIECE_SIZE])
        result.append(current)
        index += PIECE_SIZE
    return "\n".join(result)
