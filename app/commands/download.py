import asyncio

from app.logging_config import get_logger
from app.peer import Peer, peer_to_str
from app.pieces import Pieces
from app.torrent_file import TorrentFile

logger = get_logger(__name__)


def download_piece(output: str, torrent_filename: str, piece_index: int) -> str:
    with open(torrent_filename, "rb") as file:
        content_bytes = file.read()
    torrent_file = TorrentFile.from_bytes(content_bytes)
    asyncio.run(
        _download_piece(output, torrent_file=torrent_file, piece_index=piece_index)
    )
    return ""


def download(output: str, torrent_filename: str) -> str:
    return "NotImplementedError"


async def _download_piece(
    output: str, torrent_file: TorrentFile, piece_index: int
) -> None:
    peers = {
        peer_to_str(ip, port): Peer(ip, port, torrent_file.info_hash)
        for ip, port in torrent_file.get_peers()  # noqa: WPS221
    }
    if piece_index == len(torrent_file.piece_hashes) - 1:
        piece_length = torrent_file.length % torrent_file.piece_length
    else:
        piece_length = torrent_file.piece_length
    pieces: Pieces = Pieces(piece_length=piece_length, piece_index=piece_index)
    tasks: set[asyncio.Task[None]] = set(
        [
            asyncio.create_task(peer.communicate(pieces), name=name)
            for name, peer in peers.items()
        ]
    )
    while not pieces.is_done:
        done_tasks, tasks = await asyncio.wait(
            tasks, return_when=asyncio.FIRST_COMPLETED
        )
        logger.info(f"done = {done_tasks}")
        logger.info(f"tasks = {tasks}")
        logger.info(f"pieces.done_blocks = {pieces.done_blocks}")
        for done_task in done_tasks:
            name = done_task.get_name()
            if done_task.exception() is not None:
                logger.error(
                    f"done_task.exception() = {type(done_task.exception())} {done_task.exception()}",
                    exc_info=done_task.exception(),
                )
                pieces.return_in_queue(name)
                # continue
            peer = peers[name]
            tasks.add(asyncio.create_task(peer.communicate(pieces), name=name))
    with open(output, "wb") as file:
        for block in pieces.blocks():
            file.write(block)
