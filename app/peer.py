from asyncio import (
    Event,
    StreamWriter,
    open_connection,
)
from dataclasses import dataclass
from typing import Optional

from app.async_reader import AsyncReaderHandler
from app.const import MY_ID, MessageType
from app.exceptions import PeerCommunicationError
from app.logging_config import get_logger
from app.packets import (
    HandshakePacket,
    Packet,
    PeerPacket,
    PiecePeerPacket,
)
from app.pieces import Pieces

logger = get_logger(__name__)


def peer_to_str(ip: str, port: int) -> str:
    return f"[{ip}:{port}]"


@dataclass
class Peer:
    ip: str
    port: int
    info_hash: bytes
    reader: Optional[AsyncReaderHandler] = None
    writer: Optional[StreamWriter] = None

    def __repr__(self) -> str:
        return peer_to_str(self.ip, self.port)

    async def handshake(self) -> str:
        reader, writer = await open_connection(self.ip, self.port)
        self.writer = writer
        peername = str(writer.get_extra_info("peername"))
        self.reader = AsyncReaderHandler(
            reader, peername=peername, rw_closing_event=Event()
        )

        await self.write(HandshakePacket(self.info_hash, MY_ID))
        result = await self.read_handshake()
        return result.peer_id

    async def communicate(self, pieces: Pieces) -> None:  # noqa: WPS217
        await self.handshake()
        logger.info(f"{self}: Handshake done")
        peer_response = await self.read_peer()
        if peer_response.message_type != MessageType.BITFIELD:
            logger.error(f"peer_response = {peer_response}")
            raise PeerCommunicationError
        await self.write(PeerPacket(message_type=MessageType.INTERESTED))

        peer_response = await self.read_peer()
        if peer_response.message_type != MessageType.UNCHOKE:
            logger.error(f"peer_response = {peer_response}")
            raise PeerCommunicationError
        logger.info(f"{self}: Unchoked")

        while not pieces.is_done:
            block_index, request = await pieces.get_request_packet(str(self))
            await self.write(request)
            message_response = await self.read_peer()
            logger.debug(f"message_response = {message_response}")
            if not isinstance(message_response, PiecePeerPacket):
                raise NotImplementedError
            pieces.put_processed(
                block_index=block_index,
                block_value=message_response.parsed_payload.block,
                peer_name=str(self),
            )

    async def write(self, packet: Packet) -> None:
        if self.writer is None:
            raise NotImplementedError
        self.writer.write(packet.to_bytes)
        await self.writer.drain()
        logger.debug(f"{self}: write {packet}")

    async def read_handshake(self) -> HandshakePacket:
        if self.reader is None:
            raise NotImplementedError
        return await self.reader.read_handshake()

    async def read_peer(self) -> PeerPacket:
        if self.reader is None:
            raise NotImplementedError
        result: Optional[PeerPacket] = None
        while result is None:
            result = await self.reader.read_peer()
        return result
