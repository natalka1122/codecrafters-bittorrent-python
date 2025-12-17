import asyncio
from typing import Optional

from app.logging_config import get_logger
from app.peer.peer import Peer, peer_to_str
from app.pieces import ManyPieces
from app.torrent_file import TorrentFile

logger = get_logger(__name__)


def download_piece(output: str, torrent_filename: str, piece_index: int) -> str:
    with open(torrent_filename, "rb") as file:
        content_bytes = file.read()
    torrent_file = TorrentFile.from_bytes(content_bytes)
    asyncio.run(_download(output, torrent_file=torrent_file, piece_index=piece_index))
    return ""


def download(output: str, torrent_filename: str) -> str:
    with open(torrent_filename, "rb") as file:
        content_bytes = file.read()
    torrent_file = TorrentFile.from_bytes(content_bytes)
    asyncio.run(_download(output, torrent_file=torrent_file))
    return ""


async def _download(
    output_file: str, torrent_file: TorrentFile, piece_index: Optional[int] = None
) -> None:
    peers = {
        peer_to_str(ip, port): Peer(ip, port, torrent_file.info_hash)
        for ip, port in torrent_file.get_peers()  # noqa: WPS221
    }
    many_pieces = ManyPieces(torrent_file=torrent_file, piece_index=piece_index)
    tasks: set[asyncio.Task[None]] = set(
        [
            # asyncio.create_task(peer.communicate_v2(many_pieces), name=peername)
            asyncio.create_task(peer.communicate_v3(many_pieces), name=peername)
            for peername, peer in peers.items()
        ]
    )
    while not many_pieces.is_done:
        done_tasks, tasks = await asyncio.wait(
            tasks, return_when=asyncio.FIRST_COMPLETED
        )
        logger.info(f"done = {done_tasks}")
        logger.info(f"tasks = {tasks}")
        logger.info(f"many_pieces.done_blocks = {many_pieces.done_blocks}")
        for done_task in done_tasks:
            peername = done_task.get_name()
            if done_task.exception() is not None:
                logger.error(f"done_task = {done_task}")
                logger.error(
                    f"done_task.exception() = {type(done_task.exception())} {done_task.exception()}",
                    exc_info=done_task.exception(),
                )
                raise NotImplementedError
            many_pieces.return_in_queue(peername)
            peer = peers[peername]
            tasks.add(
                asyncio.create_task(peer.communicate_v3(many_pieces), name=peername)
            )
    logger.info("DONE DONE")
    with open(output_file, "wb") as file:
        for block in many_pieces.blocks():
            file.write(block)
