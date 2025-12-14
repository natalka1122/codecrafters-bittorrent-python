import asyncio

from app.const import BLOCK_SIZE
from app.logging_config import get_logger
from app.packets import RequestPayload, RequestPeerPacket
from app.peer import Peer
from app.torrent_file import TorrentFile

logger = get_logger(__name__)


def download_piece(output: str, torrent_filename: str, piece_index: int) -> str:
    with open(torrent_filename, "rb") as file:
        content_bytes = file.read()
    torrent_file = TorrentFile.from_bytes(content_bytes)
    asyncio.run(_download_piece(output, torrent_file=torrent_file, piece_index=piece_index))
    return ""


def download(output: str, torrent_filename: str) -> str:
    return "NotImplementedError"


async def _download_piece(output: str, torrent_file: TorrentFile, piece_index: int) -> None:
    peers = [
        Peer(ip, port, torrent_file.info_hash)
        for ip, port in torrent_file.get_peers()  # noqa: WPS221
    ]
    blocks_count = torrent_file.piece_length // BLOCK_SIZE
    logger.info(f"blocks_count = {blocks_count}")
    requests: asyncio.Queue[RequestPeerPacket] = asyncio.Queue()
    for i in range(blocks_count):
        requests.put_nowait(
            RequestPeerPacket(
                payload=RequestPayload(
                    index=piece_index, offset=i * BLOCK_SIZE, length=BLOCK_SIZE
                ).to_bytes
            )
        )
    if torrent_file.piece_length % BLOCK_SIZE > 0:
        requests.put_nowait(
            RequestPeerPacket(
                payload=RequestPayload(
                    index=blocks_count, offset=blocks_count * BLOCK_SIZE, length=BLOCK_SIZE
                ).to_bytes
            )
        )
    logger.info(f"requests = {requests}")
    tasks = [asyncio.create_task(peer.handshake(requests)) for peer in peers]
    result = await asyncio.gather(*tasks)
    logger.info(f"result = {result}")
