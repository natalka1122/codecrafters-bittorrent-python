from asyncio import Event, IncompleteReadError, Lock, StreamReader
from typing import Awaitable, Callable

from app.const import StreamExactly
from app.exceptions import ReaderClosedError
from app.logging_config import get_logger
from app.packets import HandshakePacket, Packet, PeerPacket

logger = get_logger(__name__)


class AsyncReaderHandler:
    """Handles async read operations with proper error handling and queuing."""

    def __init__(
        self,
        reader: StreamReader,
        peername: str,
        rw_closing_event: Event,
    ):
        self.closed: Event = rw_closing_event
        self._reader = reader
        self.peername = peername
        self._lock = Lock()

    def __repr__(self) -> str:
        return f"[{self.peername}]"

    async def read_handshake(self) -> HandshakePacket:
        result = await self._read(HandshakePacket.from_stream)
        if not isinstance(result, HandshakePacket):
            raise NotImplementedError
        return result

    async def read_peer(self) -> PeerPacket:
        result = await self._read(PeerPacket.from_stream)
        if not isinstance(result, PeerPacket):
            raise NotImplementedError
        return result

    async def _read(
        self, parser: Callable[[StreamExactly], Awaitable[Packet]]
    ) -> Packet:
        if self.closed.is_set():
            raise ReaderClosedError
        try:
            async with self._lock:
                result = await parser(self._reader.readexactly)
        except IncompleteReadError:
            self.closed.set()
            raise ReaderClosedError
        logger.debug(f"{self}: Read {result}")
        return result
