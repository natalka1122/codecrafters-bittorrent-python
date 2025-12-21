import asyncio
from dataclasses import dataclass
from typing import Iterable, Optional

from app.const import BLOCK_SIZE_BYTES
from app.logging_config import get_logger
from app.packets import RequestPayload, RequestPeerPacket
from app.torrent_file import TorrentFile

logger = get_logger(__name__)

PeerAndPiece = tuple[str, int]


@dataclass(frozen=True)
class PieceBlock:
    piece_index: int
    block_index: int


class Pieces:  # noqa: WPS214
    def __init__(
        self, torrent_file: TorrentFile, piece_index: Optional[int] = None
    ) -> None:
        self._length = torrent_file.length
        self._request_packets: dict[PieceBlock, RequestPeerPacket] = dict()
        self._queue: asyncio.Queue[PieceBlock] = asyncio.Queue()
        self._ready_blocks: dict[PieceBlock, bytes] = dict()
        self._in_progress: dict[str, set[PieceBlock]] = dict()
        self._piece_count = len(torrent_file.piece_hashes)
        if piece_index is None:
            piece_range: Iterable[int] = range(self._piece_count)
        else:
            piece_range = [piece_index]
        for piece_index in piece_range:
            if piece_index == self._piece_count - 1:
                piece_length = torrent_file.length % torrent_file.piece_length
            else:
                piece_length = torrent_file.piece_length
            blocks_count = piece_length // BLOCK_SIZE_BYTES
            for block_index in range(blocks_count):
                self._add_to_queue(piece_index=piece_index, block_index=block_index)
            if piece_length % BLOCK_SIZE_BYTES > 0:
                self._add_to_queue(
                    piece_index=piece_index,
                    block_index=blocks_count,
                    length=piece_length % BLOCK_SIZE_BYTES,
                )

    @property
    def is_done(self) -> bool:
        return len(self._ready_blocks) == len(self._request_packets)

    @property
    def done_blocks(self) -> set[PieceBlock]:
        return set(self._ready_blocks.keys())

    def return_in_queue(self, peername: str) -> None:
        block_index_set = self._in_progress.pop(peername, None)
        if block_index_set is None:
            logger.error(
                f"peername = {peername} self._in_progress = {self._in_progress}"
            )
            raise NotImplementedError
        for block_index in block_index_set:
            self._queue.put_nowait(block_index)

    async def get_request_packet(self, peername: str) -> RequestPeerPacket:
        piece_block = await self._queue.get()
        if piece_block in self._ready_blocks:
            logger.error(f"Got {piece_block} that is in self._ready_blocks")
            raise NotImplementedError
        if peername not in self._in_progress:
            self._in_progress[peername] = set()
        self._in_progress[peername].add(piece_block)
        return self._request_packets[piece_block]

    def put_processed(
        self, piece_block: PieceBlock, block_value: bytes, peername: str
    ) -> None:
        stored_block_value = self._ready_blocks.get(piece_block, None)
        if stored_block_value is not None:
            logger.error(f"Already received {piece_block}")
            if stored_block_value != block_value:
                logger.error("And this one has different content")
            raise NotImplementedError
        allocated = self._in_progress.get(peername)
        if allocated is None:
            logger.error(f"There is no {peername} in {self._in_progress}")
            logger.error(f"self._in_progress = {self._in_progress}")
            raise NotImplementedError
        if piece_block not in allocated:
            logger.error(f"There is no {piece_block} in allocated = {allocated}")
            raise NotImplementedError
        allocated.remove(piece_block)
        self._ready_blocks[piece_block] = block_value

    def blocks(self) -> Iterable[bytes]:
        if not self.is_done:
            raise NotImplementedError
        ready_blocks = sorted(
            self._ready_blocks.keys(), key=lambda x: (x.piece_index, x.block_index)
        )
        for index in ready_blocks:
            yield self._ready_blocks[index]

    def _add_to_queue(
        self, block_index: int, piece_index: int, length: int = BLOCK_SIZE_BYTES
    ) -> None:
        piece_block = PieceBlock(piece_index=piece_index, block_index=block_index)
        if piece_block in self._request_packets:
            raise NotImplementedError
        self._request_packets[piece_block] = RequestPeerPacket(
            payload=RequestPayload(
                piece_index=piece_index,
                offset=block_index * BLOCK_SIZE_BYTES,
                length=length,
            ).to_bytes
        )
        self._queue.put_nowait(piece_block)
