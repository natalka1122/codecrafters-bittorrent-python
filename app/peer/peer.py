from asyncio import (
    FIRST_COMPLETED,
    Event,
    Task,
    create_task,
    current_task,
    open_connection,
    wait,
)
from typing import Optional

from app.const import MAX_CONCURRENT_REQUESTS, MY_ID, MessageType
from app.exceptions import PeerCommunicationError
from app.logging_config import get_logger
from app.packets import (
    HandshakePacket,
    KeepAlivePacket,
    Packet,
    PeerPacket,
    PiecePeerPacket,
)
from app.peer.async_reader import AsyncReaderHandler
from app.peer.async_writer import AsyncWriterHandler
from app.pieces import ManyPieces, PieceBlock

logger = get_logger(__name__)


def peer_to_str(ip: str, port: int) -> str:
    return f"[{ip}:{port}]"


class Peer:
    def __init__(self, ip: str, port: int, info_hash: bytes) -> None:
        self.ip = ip
        self.port = port
        self.info_hash = info_hash
        self.peername = f"[{self.ip}:{self.port}]"
        self._reader: Optional[AsyncReaderHandler] = None
        self._writer: Optional[AsyncWriterHandler] = None
        self.closed: Event = Event()

    def __str__(self) -> str:
        return self.peername

    @property
    def writer(self) -> AsyncWriterHandler:
        if self._writer is None:
            raise NotImplementedError
        return self._writer

    @property
    def reader(self) -> AsyncReaderHandler:
        if self._reader is None:
            raise NotImplementedError
        return self._reader

    async def handshake(self) -> str:
        reader, writer = await open_connection(self.ip, self.port)
        self._writer = AsyncWriterHandler(
            writer, peername=self.peername, closed_event=self.closed
        )
        self._reader = AsyncReaderHandler(
            reader, peername=self.peername, closed_event=self.closed
        )

        await self._write(HandshakePacket(self.info_hash, MY_ID))
        result = await self._read_handshake()
        return result.peer_id

    # async def communicate_v2(self, many_pieces: ManyPieces) -> None:  # noqa: WPS217
    #     await self.handshake()
    #     logger.info(f"{self}: Handshake done")
    #     await self._bitfield_unchoke()
    #     logger.info(f"{self}: Unchoked")

    #     while not many_pieces.is_done:
    #         piece_block, request = await many_pieces.get_request_packet(self.peername)
    #         await self._write(request)
    #         message_response = await self._read_peer()
    #         logger.debug(f"message_response = {message_response}")
    #         if not isinstance(message_response, PiecePeerPacket):
    #             raise NotImplementedError
    #         many_pieces.put_processed(
    #             piece_block=piece_block,
    #             block_value=message_response.parsed_payload.block,
    #             peername=self.peername,
    #         )
    #     logger.info("DONE")

    async def communicate_v3(self, many_pieces: ManyPieces) -> None:  # noqa: WPS217
        await self.handshake()
        logger.info(f"{self}: Handshake done")
        await self._bitfield_unchoke()
        logger.info(f"{self}: Unchoked")

        read_task = create_task(self._read_peer(), name=f"{self} reader")
        tasks: set[Task[Optional[PeerPacket]]] = {  # noqa: WPS234
            create_task(self._write_from_queue(many_pieces), name=f"{self} writer")
            for _ in range(MAX_CONCURRENT_REQUESTS)
        }
        tasks.add(read_task)
        while not many_pieces.is_done:
            done_tasks, tasks = await wait(tasks, return_when=FIRST_COMPLETED)
            logger.info(f"done = {done_tasks}")
            logger.info(f"tasks = {tasks}")
            logger.info(f"many_pieces.done_blocks = {many_pieces.done_blocks}")
            for done_task in done_tasks:
                if done_task == read_task:
                    if done_task.exception() is None:
                        logger.info(f"done_task = {done_task}")
                        logger.info(f"done_task.result() = {done_task.result()}")
                        message_response = done_task.result()
                        if isinstance(message_response, PiecePeerPacket):
                            piece_block = PieceBlock(
                                piece_index=message_response.parsed_payload.piece_index,
                                block_index=message_response.parsed_payload.block_index,
                            )
                            many_pieces.put_processed(
                                piece_block=piece_block,
                                block_value=message_response.parsed_payload.block,
                                peername=self.peername,
                            )
                            logger.info(
                                f"many_pieces.done_blocks = {many_pieces.done_blocks}"
                            )
                        elif not isinstance(message_response, KeepAlivePacket):
                            logger.info(
                                f"message_response = {type(message_response)} {message_response}"
                            )
                            raise NotImplementedError
                    else:
                        many_pieces.return_in_queue(peername=self.peername)
                    tasks.add(create_task(self._read_peer(), name=f"{self} reader"))
            while many_pieces.count_peer_requests(self.peername) <= MAX_CONCURRENT_REQUESTS:
                tasks.add(
                    create_task(
                        self._write_from_queue(many_pieces),
                        name=f"{self} writer",
                    )
                )
                logger.info("Created new writer")
        logger.info("DONE")

    #     while not many_pieces.is_done:
    #         piece_block, request = await many_pieces.get_request_packet(self.peername)
    #         await self.write(request)
    #         message_response = await self.read_peer()
    #         logger.debug(f"message_response = {message_response}")
    #         if not isinstance(message_response, PiecePeerPacket):
    #             raise NotImplementedError
    #         many_pieces.put_processed(
    #             piece_block=piece_block,
    #             block_value=message_response.parsed_payload.block,
    #             peername=self.peername,
    #         )
    #     logger.info("DONE")

    # async def writer_loop(self, many_pieces: ManyPieces) -> None:
    #     pass

    async def _write(self, packet: Packet) -> None:
        await self.writer.write(packet.to_bytes)
        logger.debug(f"{self}: write {packet}")

    async def _read_handshake(self) -> HandshakePacket:
        return await self.reader.read_handshake()

    async def _read_peer(self) -> PeerPacket:
        return await self.reader.read_peer()

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

    async def _write_from_queue(self, many_pieces: ManyPieces) -> None:
        request = await many_pieces.get_request_packet_v2(self.peername)
        task = current_task()
        if task is None:
            raise NotImplementedError
        task.set_name(
            f"{task.get_name()}: ({request.parsed_payload.piece_index}, {request.parsed_payload.block_index})"
        )
        await self._write(request)
