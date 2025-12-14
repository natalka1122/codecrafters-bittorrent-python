import asyncio
from typing import Iterable

from app.const import BLOCK_SIZE
from app.logging_config import get_logger
from app.packets import RequestPayload, RequestPeerPacket

logger = get_logger(__name__)


class Pieces:  # noqa: WPS214
    def __init__(self, piece_length: int, piece_index: int) -> None:
        blocks_count = piece_length // BLOCK_SIZE
        logger.info(f"blocks_count = {blocks_count}")
        self._request_packets: list[RequestPeerPacket] = []
        self._queue: asyncio.Queue[int] = asyncio.Queue()
        self._blocks: dict[int, bytes] = dict()
        self._in_progress: dict[str, int] = dict()
        for i in range(blocks_count):
            self._add_task(piece_index=piece_index, block_index=i)
        if piece_length % BLOCK_SIZE > 0:
            self._add_task(
                piece_index=piece_index,
                block_index=blocks_count,
                length=piece_length % BLOCK_SIZE,
            )

    @property
    def is_done(self) -> bool:
        return len(self._blocks) == len(self._request_packets)

    @property
    def done_blocks(self) -> set[int]:
        return set(self._blocks.keys())

    async def get_request_packet(self, peer_name: str) -> tuple[int, RequestPeerPacket]:
        block_index = await self._queue.get()
        if block_index in self._blocks or peer_name in self._in_progress:
            raise NotImplementedError
        self._in_progress[peer_name] = block_index
        return block_index, self._request_packets[block_index]

    def put_processed(
        self, block_index: int, block_value: bytes, peer_name: str
    ) -> None:
        if (
            block_index in self._blocks
            or self._in_progress.get(peer_name) != block_index
        ):
            raise NotImplementedError
        self._in_progress.pop(peer_name)
        self._blocks[block_index] = block_value

    def return_in_queue(self, peer_name: str) -> None:
        block_index = self._in_progress.get(peer_name)
        if block_index is None:
            raise NotImplementedError
        self._in_progress.pop(peer_name)
        self._queue.put_nowait(block_index)

    def blocks(self) -> Iterable[bytes]:
        if not self.is_done:
            raise NotImplementedError
        for index in sorted(self._blocks):
            yield self._blocks[index]

    def _add_task(
        self, block_index: int, piece_index: int, length: int = BLOCK_SIZE
    ) -> None:
        self._request_packets.append(
            RequestPeerPacket(
                payload=RequestPayload(
                    piece_index=piece_index,
                    offset=block_index * BLOCK_SIZE,
                    length=length,
                ).to_bytes
            )
        )
        self._queue.put_nowait(block_index)
