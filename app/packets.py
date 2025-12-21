from abc import abstractmethod
from dataclasses import dataclass
from typing import final

from app.bencode import Dict, Integer
from app.const import (
    BITTORRENT_PROTOCOL,
    BLOCK_SIZE_BYTES,
    MessageType,
    StreamExactly,
)
from app.exceptions import NeedMoreBytesError, WrongPacketFormatError
from app.logging_config import get_logger
from app.service_func import hex20

logger = get_logger(__name__)


@dataclass
class Packet:
    @property
    @abstractmethod
    def to_bytes(self) -> bytes: ...

    @classmethod
    @abstractmethod
    async def from_stream(cls, reader: StreamExactly) -> "Packet": ...


@dataclass
class Payload:
    @property
    @abstractmethod
    def to_bytes(self) -> bytes: ...

    @classmethod
    @abstractmethod
    def from_bytes(cls, raw_data: bytes) -> "Payload": ...


@dataclass
@final
class HandshakePacket(Packet):
    info_hash: bytes
    peer_id_bytes: bytes
    extension_enabled: bool

    def __repr__(self) -> str:
        return ", ".join(
            [
                f"HandshakePacket(info_hash={self.info_hash!r}",
                f"peer_id={self.peer_id}",
                f"extension_enabled={self.extension_enabled})",  # noqa: WPS226
            ]
        )

    @property
    def to_bytes(self) -> bytes:
        reserved = bytearray(8)
        if self.extension_enabled:
            reserved[5] |= 0x10
        return b"".join(
            [
                bytes([len(BITTORRENT_PROTOCOL)]),
                BITTORRENT_PROTOCOL,
                bytes(reserved),
                self.info_hash,
                self.peer_id_bytes,
            ]
        )

    @property
    def peer_id(self) -> str:
        return hex20(self.peer_id_bytes)

    @classmethod
    async def from_stream(  # noqa: WPS210
        cls, reader: StreamExactly
    ) -> "HandshakePacket":
        protocol_str_length: int = (await reader(1))[0]
        if protocol_str_length != len(BITTORRENT_PROTOCOL):
            raise WrongPacketFormatError
        protocol_str = await reader(protocol_str_length)
        if protocol_str != BITTORRENT_PROTOCOL:
            raise WrongPacketFormatError
        reserved_bytes = await reader(8)
        extension_enabled = (reserved_bytes[5] & 0x10) != 0
        info_hash = await reader(20)
        peer_id_bytes = await reader(20)
        return HandshakePacket(
            info_hash=info_hash,
            peer_id_bytes=peer_id_bytes,
            extension_enabled=extension_enabled,
        )


@dataclass
class PeerPacket(Packet):
    message_type: MessageType
    payload: bytes = b""

    @property
    def to_bytes(self) -> bytes:
        result = self.message_type.to_bytes(1) + self.payload
        return len(result).to_bytes(4) + result

    @classmethod
    async def from_stream(cls, reader: StreamExactly) -> "PeerPacket":  # noqa: WPS231
        length = int.from_bytes(await reader(4))
        if length == 0:
            return KeepAlivePacket()
        message_type_int = (await reader(1))[0]
        try:
            message_type = MessageType(message_type_int)
        except ValueError:
            logger.error(f"message_type_int = {message_type_int}")
            raise WrongPacketFormatError
        if message_type == MessageType.REQUEST:
            result_type: type[PeerPacket] = RequestPeerPacket
        elif message_type == MessageType.PIECE:
            result_type = PiecePeerPacket
        elif message_type == MessageType.KEEPALIVE:
            result_type = KeepAlivePacket
        elif message_type == MessageType.EXTENDED:
            result_type = ExtendedPacket
        else:
            result_type = PeerPacket
        payload = await reader(length - 1)
        return result_type(message_type=message_type, payload=payload)


@dataclass
@final
class KeepAlivePacket(PeerPacket):
    message_type: MessageType = MessageType.KEEPALIVE

    @classmethod
    async def from_stream(cls, reader: StreamExactly) -> "KeepAlivePacket":
        return KeepAlivePacket()


@dataclass
@final
class RequestPayload(Payload):
    piece_index: int
    offset: int
    length: int

    def __repr__(self) -> str:
        return f"RequestPayload(piece_index={self.piece_index}, block_index={self.block_index}, length = {self.length}"

    @property
    def to_bytes(self) -> bytes:
        piece_index_bytes = self.piece_index.to_bytes(4)
        offset_bytes = self.offset.to_bytes(4)
        length_bytes = self.length.to_bytes(4)
        return piece_index_bytes + offset_bytes + length_bytes

    @property
    def block_index(self) -> int:
        remainder = self.offset % BLOCK_SIZE_BYTES
        if remainder != 0:
            logger.error(
                f"self.offset = {self.offset} self.offset % BLOCK_SIZE_BYTES = {remainder}"
            )
        return self.offset // BLOCK_SIZE_BYTES

    @classmethod
    def from_bytes(cls, raw_data: bytes) -> "RequestPayload":
        if len(raw_data) != 12:
            raise NeedMoreBytesError
        piece_index = int.from_bytes(raw_data[:4])
        offset = int.from_bytes(raw_data[4:8])
        length = int.from_bytes(raw_data[8:12])
        return RequestPayload(piece_index=piece_index, offset=offset, length=length)


@dataclass
@final
class RequestPeerPacket(PeerPacket):
    message_type: MessageType = MessageType.REQUEST

    @property
    def parsed_payload(self) -> RequestPayload:
        return RequestPayload.from_bytes(self.payload)

    def __repr__(self) -> str:
        return f"RequestPeerPacket(message_type={self.message_type}, parsed_payload={self.parsed_payload})"


@dataclass
@final
class PiecePayload(Payload):
    piece_index: int
    offset: int
    block: bytes

    def __repr__(self) -> str:
        return f"PiecePayload(piece_index={self.piece_index}, block_index={self.block_index}, len = {len(self.block)}"

    @property
    def block_index(self) -> int:
        remainder = self.offset % BLOCK_SIZE_BYTES
        if remainder != 0:
            logger.error(
                f"self.offset = {self.offset} self.offset % BLOCK_SIZE_BYTES = {remainder}"
            )
        return self.offset // BLOCK_SIZE_BYTES

    @property
    def to_bytes(self) -> bytes:
        piece_index_bytes = self.piece_index.to_bytes(4)
        offset_bytes = self.offset.to_bytes(4)
        return piece_index_bytes + offset_bytes + self.block

    @classmethod
    def from_bytes(cls, raw_data: bytes) -> "PiecePayload":
        piece_index = int.from_bytes(raw_data[:4])
        offset = int.from_bytes(raw_data[4:8])
        return PiecePayload(piece_index=piece_index, offset=offset, block=raw_data[8:])


@dataclass
@final
class PiecePeerPacket(PeerPacket):
    message_type: MessageType = MessageType.PIECE

    @property
    def parsed_payload(self) -> PiecePayload:
        return PiecePayload.from_bytes(self.payload)

    def __repr__(self) -> str:
        return f"PiecePeerPacket(message_type={self.message_type}, parsed_payload={self.parsed_payload})"


@dataclass
@final
class ExtendedPayload(Payload):
    ut_metadata: int

    @property
    def to_bytes(self) -> bytes:
        result = Dict({"m": Dict({"ut_metadata": Integer(1)})})
        return b"".join([b"\x00", result.to_bytes])

    @classmethod
    def from_bytes(cls, raw_data: bytes) -> "ExtendedPayload":  # noqa: WPS238
        logger.error(f"raw_data = {raw_data!r}")
        if raw_data[0] != 0:
            logger.error(f"raw_data = {raw_data!r}")
            raise NotImplementedError
        remainder, m_dict = Dict.from_bytes(raw_data[1:])
        if len(remainder) > 0:
            logger.error(f"raw_data = {raw_data!r}")
            raise NotImplementedError
        m_dict_value = m_dict["m"]
        if not isinstance(m_dict_value, Dict):
            logger.error(f"m_dict = {m_dict}")
            raise NotImplementedError
        ut_metadata = m_dict_value["ut_metadata"]
        if not isinstance(ut_metadata, Integer):
            logger.error(f"m_dict = {m_dict}")
            raise NotImplementedError
        return ExtendedPayload(ut_metadata=ut_metadata.data)


@dataclass
@final
class ExtendedPacket(PeerPacket):
    message_type: MessageType = MessageType.EXTENDED

    @property
    def parsed_payload(self) -> ExtendedPayload:
        return ExtendedPayload.from_bytes(self.payload)

    def __repr__(self) -> str:
        return f"ExtendedPacket(message_type={self.message_type}, parsed_payload={self.parsed_payload})"
