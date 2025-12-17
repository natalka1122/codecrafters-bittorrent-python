from asyncio import (
    FIRST_COMPLETED,
    CancelledError,
    Event,
    Lock,
    StreamWriter,
    Task,
    create_task,
    gather,
    wait,
)
from typing import Any

from app.exceptions import WriterClosedError
from app.logging_config import get_logger

logger = get_logger(__name__)


class AsyncWriterHandler:
    def __init__(self, writer: StreamWriter, peername: str, closed_event: Event):
        self.closed: Event = closed_event
        self._writer = writer
        self.peername = peername
        self._lock = Lock()
        self._closure_task: Task[None] = create_task(
            self._closure_loop(), name=f"{peername}: AsyncWriterHandler._closure_loop"
        )

    def __str__(self) -> str:
        return self.peername

    async def write(self, data: bytes) -> None:  # noqa: WPS238
        if self.closed.is_set():
            raise WriterClosedError("Writer is closed")
        async with self._lock:
            try:
                await self._write_actually(data)
            except CancelledError:
                self.closed.set()
                logger.debug(f"{self}: Write cancelled")
                raise
            except WriterClosedError:
                raise
            except Exception as e:
                logger.error(f"{self}: Writer error: {e}")
                self.closed.set()
                raise WriterClosedError(f"Write failed: {e}") from e

    async def _write_actually(self, data: bytes) -> None:  # noqa: WPS210
        self._writer.write(data)
        write_task: Task[None] = create_task(self._writer.drain())
        closed_task: Task[bool] = create_task(self.closed.wait())

        tasks: set[Task[Any]] = {write_task, closed_task}
        done, pending = await wait(tasks, return_when=FIRST_COMPLETED)

        for task in pending:
            task.cancel()
        await gather(*pending, return_exceptions=True)

        if closed_task in done:
            logger.debug(f"{self}: Write cancelled due to closed event")
            raise WriterClosedError("Writer closed")

        return await write_task  # This will raise if there was an error

    async def _closure_loop(self) -> None:
        await self.closed.wait()

        if not self._writer.is_closing():
            self._writer.close()

        try:
            await self._writer.wait_closed()
        except CancelledError:
            logger.debug(f"{self}: Cancellation during closure")
            raise

        logger.info(f"{self}: Writer closed")
