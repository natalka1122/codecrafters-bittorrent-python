from asyncio import Queue, StreamReader, StreamWriter, open_connection
from dataclasses import dataclass
from typing import Callable, Optional

from app.const import BLOCK_SIZE, MY_ID, MessageType
from app.logging_config import get_logger
from app.packets import (
    HandshakePacket,
    Packet,
    PeerPacket,
    RequestPeerPacket,
)

logger = get_logger(__name__)


@dataclass
class Peer:
    ip: str
    port: int
    info_hash: bytes
    reader: Optional[StreamReader] = None
    writer: Optional[StreamWriter] = None

    def __repr__(self) -> str:
        return f"[{self.ip}:{self.port}]"

    async def handshake(self, requests: Queue[RequestPeerPacket]) -> bool:  # noqa: WPS217
        try:
            reader, writer = await open_connection(self.ip, self.port)
        except OSError:
            return False
        self.reader = reader
        self.writer = writer

        await self.write(HandshakePacket(self.info_hash, MY_ID))
        await self.read_handshake()

        logger.info(f"{self}: Handshake done")
        peer_response = await self.read_peer()
        if peer_response.message_type != MessageType.BITFIELD:
            logger.error(f"peer_response = {peer_response}")
            return False
        await self.write(PeerPacket(message_type=MessageType.INTERESTED))

        peer_response = await self.read_peer()
        if peer_response.message_type != MessageType.UNCHOKE:
            logger.error(f"peer_response = {peer_response}")
            return False
        logger.info(f"{self}: Unchoked")
        request = await requests.get()
        await self.write(request)
        message_response = await self.read_peer()
        return True

    async def write(self, packet: Packet) -> None:
        if self.writer is None:
            raise NotImplementedError
        self.writer.write(packet.to_bytes)
        await self.writer.drain()
        logger.debug(f"{self}: write {packet}")

    async def read_handshake(self) -> HandshakePacket:
        if self.reader is None:
            raise NotImplementedError
        result = await self._read(parser=HandshakePacket.from_bytes)
        if not isinstance(result, HandshakePacket):
            raise NotImplementedError
        return result

    async def read_peer(self) -> PeerPacket:
        if self.reader is None:
            raise NotImplementedError
        result = await self._read(parser=PeerPacket.from_bytes)
        if not isinstance(result, PeerPacket):
            raise NotImplementedError
        return result

    async def _read(self, parser: Callable[[bytes], Packet]) -> Packet:
        if self.reader is None:
            raise NotImplementedError
        result = parser(await self.reader.read(BLOCK_SIZE))
        logger.debug(f"{self}: read {result}")
        return result
