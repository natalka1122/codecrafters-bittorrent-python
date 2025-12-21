import asyncio
from typing import Optional

from app.logging_config import get_logger
from app.peer.peer import Peer, peer_to_str
from app.pieces import Pieces
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


async def _download(  # noqa: WPS210
    output_file: str, torrent_file: TorrentFile, piece_index: Optional[int] = None
) -> None:
    peers = {
        peer_to_str(ip, port): Peer(ip, port, torrent_file.info_hash)
        for ip, port in torrent_file.get_peers()  # noqa: WPS221
    }
    pieces = Pieces(torrent_file=torrent_file, piece_index=piece_index)
    tasks: set[asyncio.Task[None]] = set(
        [
            asyncio.create_task(peer.communicate(pieces), name=peername)
            for peername, peer in peers.items()
        ]
    )
    while not pieces.is_done:
        done_tasks, tasks = await asyncio.wait(
            tasks, return_when=asyncio.FIRST_COMPLETED
        )
        for done_task in done_tasks:
            peername = done_task.get_name()
            if done_task.exception() is not None:
                logger.error(f"done_task = {done_task}")
                logger.error(
                    f"done_task.exception() = {type(done_task.exception())} {done_task.exception()}",
                    exc_info=done_task.exception(),
                )
                raise NotImplementedError
            pieces.return_in_queue(peername)
            peer = peers[peername]
            tasks.add(asyncio.create_task(peer.communicate(pieces), name=peername))
            logger.info(f"Recreated peer-task {peername}")
        await asyncio.sleep(0)
    with open(output_file, "wb") as file:
        for block in pieces.blocks():
            file.write(block)
