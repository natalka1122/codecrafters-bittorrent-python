from asyncio import (
    FIRST_COMPLETED,
    Event,
    Task,
    create_task,
    current_task,
    open_connection,
    sleep,
    wait,
)
from typing import Optional

from app.const import MAX_CONCURRENT_REQUESTS, MY_ID, MessageType
from app.exceptions import PeerCommunicationError
from app.logging_config import get_logger
from app.packets import (
    ExtendedPacket,
    ExtendedPayload,
    HandshakePacket,
    KeepAlivePacket,
    Packet,
    PeerPacket,
    PiecePeerPacket,
)
from app.peer.async_reader import AsyncReaderHandler
from app.peer.async_writer import AsyncWriterHandler
from app.pieces import PieceBlock, Pieces

logger = get_logger(__name__)


def peer_to_str(ip: str, port: int) -> str:
    return f"[{ip}:{port}]"


OptionalPeerPacket = Optional[PeerPacket]


class Peer:  # noqa: WPS214
    def __init__(
        self, ip: str, port: int, info_hash: bytes, extension_enabled: bool = False
    ) -> None:
        self._ip = ip
        self._port = port
        self._info_hash = info_hash
        self._peername = f"[{self._ip}:{self._port}]"
        self._reader: Optional[AsyncReaderHandler] = None
        self._writer: Optional[AsyncWriterHandler] = None
        self._tasks: set[Task[OptionalPeerPacket]] = set()
        self._read_task: Optional[Task[PeerPacket]] = None
        self._in_flight = 0
        self._extension_enabled = extension_enabled
        self.closed: Event = Event()

    def __str__(self) -> str:
        return self._peername

    async def handshake(self) -> str:
        reader, writer = await open_connection(self._ip, self._port)
        self._writer = AsyncWriterHandler(
            writer, peername=self._peername, closed_event=self.closed
        )
        self._reader = AsyncReaderHandler(
            reader, peername=self._peername, closed_event=self.closed
        )
        await self._write(
            HandshakePacket(
                info_hash=self._info_hash,
                peer_id_bytes=MY_ID,
                extension_enabled=self._extension_enabled,
            )
        )
        result = await self._read_handshake()
        if self._extension_enabled:
            self._extension_enabled = result.extension_enabled
            await self._write(ExtendedPacket(payload=ExtendedPayload(1).to_bytes))
        return result.peer_id

    async def communicate(self, pieces: Pieces) -> None:  # noqa: WPS217
        await self.handshake()
        await self._bitfield_unchoke()
        logger.info(f"{self}: Unchoked")
        self.pieces = pieces

        await self._fill_writers()
        self.read_task = create_task(self._read_peer(), name=f"{self} reader")
        self._tasks.add(self.read_task)

        while not pieces.is_done:
            done_tasks, tasks = await wait(self._tasks, return_when=FIRST_COMPLETED)
            self._tasks = tasks
            for done_task in done_tasks:
                self._process_done_task(done_task)
            await self._fill_writers()

    async def _write(self, packet: Packet) -> None:
        if self._writer is None:
            raise NotImplementedError
        await self._writer.write(packet.to_bytes)

    async def _read_handshake(self) -> HandshakePacket:
        if self._reader is None:
            raise NotImplementedError
        return await self._reader.read_handshake()

    async def _read_peer(self) -> PeerPacket:
        if self._reader is None:
            raise NotImplementedError
        return await self._reader.read_peer()

    async def _bitfield_unchoke(self) -> None:
        peer_response = await self._read_peer()
        if peer_response.message_type != MessageType.BITFIELD:
            logger.error(f"peer_response = {peer_response}")
            raise PeerCommunicationError
        await self._write(PeerPacket(message_type=MessageType.INTERESTED))

        peer_response = await self._read_peer()
        if peer_response.message_type != MessageType.UNCHOKE:
            logger.error(f"peer_response = {peer_response}")
            raise PeerCommunicationError

    async def _write_from_queue(self, pieces: Pieces) -> None:
        request = await pieces.get_request_packet(self._peername)
        task = current_task()
        if task is None:
            raise NotImplementedError
        task.set_name(f"{task.get_name()}: {request}")
        await self._write(request)

    async def _fill_writers(self) -> None:
        while self._in_flight < MAX_CONCURRENT_REQUESTS:
            self._tasks.add(
                create_task(
                    self._write_from_queue(self.pieces),
                    name=f"{self} writer",
                )
            )
            self._in_flight += 1
            logger.info(f"{self} Created new writer")
            await sleep(0)

    def _process_done_task(self, task: Task[OptionalPeerPacket]) -> None:
        if not task.done():
            raise NotImplementedError
        if task != self.read_task:
            return
        self._in_flight -= 1
        if task.exception() is None:
            message_response = task.result()
            message_response = task.result()
            if isinstance(message_response, PiecePeerPacket):
                piece_block = PieceBlock(
                    piece_index=message_response.parsed_payload.piece_index,
                    block_index=message_response.parsed_payload.block_index,
                )
                self.pieces.put_processed(
                    piece_block=piece_block,
                    block_value=message_response.parsed_payload.block,
                    peername=self._peername,
                )
            elif not isinstance(message_response, KeepAlivePacket):
                logger.error(
                    f"message_response = {type(message_response)} {message_response}"
                )
                raise NotImplementedError
        else:
            self.pieces.return_in_queue(peername=self._peername)
        self.read_task = create_task(self._read_peer(), name=f"{self} reader")
        self._tasks.add(self.read_task)
