from asyncio import (
    FIRST_COMPLETED,
    CancelledError,
    Event,
    Lock,
    StreamReader,
    Task,
    create_task,
    gather,
    wait,
)
from typing import Any, Callable, Coroutine

from app.const import StreamExactly
from app.exceptions import ReaderClosedError
from app.logging_config import get_logger
from app.packets import HandshakePacket, Packet, PeerPacket

logger = get_logger(__name__)


class AsyncReaderHandler:
    def __init__(
        self,
        reader: StreamReader,
        peername: str,
        closed_event: Event,
    ):
        self.closed: Event = closed_event
        self._reader: StreamReader = reader
        self._peername: str = peername
        self._lock = Lock()
        self._closure_task: Task[None] = create_task(
            self._closure_loop(), name=f"{peername}: AsyncReaderHandler._closure_loop"
        )

    def __str__(self) -> str:
        return self._peername

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

    async def _read(  # noqa: WPS238
        self, parser: Callable[[StreamExactly], Coroutine[Any, Any, Packet]]
    ) -> Packet:
        if self.closed.is_set():
            raise ReaderClosedError

        async with self._lock:
            try:
                result = await self._read_actually(parser)
            except CancelledError:
                self.closed.set()
                logger.debug(f"{self}: Read cancelled")
                raise
            except ReaderClosedError:
                raise
            except Exception as e:
                logger.debug(f"{self}: Reader error: {e}")
                self.closed.set()
                raise ReaderClosedError(f"Read failed: {e}") from e
        logger.debug(f"{self}: Read {result}")
        return result

    async def _read_actually(  # noqa: WPS210
        self, parser: Callable[[StreamExactly], Coroutine[Any, Any, Packet]]
    ) -> Packet:
        read_task: Task[Packet] = create_task(parser(self._reader.readexactly))
        closed_task: Task[bool] = create_task(self.closed.wait())

        tasks: set[Task[Any]] = {read_task, closed_task}
        done, pending = await wait(tasks, return_when=FIRST_COMPLETED)

        for task in pending:
            task.cancel()
        await gather(*pending, return_exceptions=True)

        if closed_task in done:
            logger.debug(f"{self}: Read cancelled due to closed event")
            raise ReaderClosedError("Reader closed")

        return await read_task  # This will raise if there was an error

    async def _closure_loop(self) -> None:
        await self.closed.wait()
        logger.debug(f"{self}: Reader closed")
