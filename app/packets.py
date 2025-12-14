from abc import abstractmethod
from dataclasses import dataclass

from app.const import MessageType
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
    def from_bytes(cls, raw_data: bytes) -> "Packet": ...


@dataclass
class HandshakePacket(Packet):
    info_hash: bytes
    peer_id_bytes: bytes

    def __repr__(self) -> str:
        return f"HandshakePacket(info_hash={self.info_hash!r}, peer_id={self.peer_id})"

    @property
    def to_bytes(self) -> bytes:
        return b"".join(
            [bytes([19]), b"BitTorrent protocol", bytes(8), self.info_hash, self.peer_id_bytes]
        )

    @property
    def peer_id(self) -> str:
        return hex20(self.peer_id_bytes)

    @classmethod
    def from_bytes(cls, raw_data: bytes) -> "HandshakePacket":
        info_hash = raw_data[-40:-20]
        peer_id_bytes = raw_data[-20:]
        return HandshakePacket(info_hash=info_hash, peer_id_bytes=peer_id_bytes)


@dataclass
class PeerPacket(Packet):
    message_type: MessageType
    payload: bytes = b""

    @property
    def to_bytes(self) -> bytes:
        result = self.message_type.to_bytes(1) + self.payload
        return len(result).to_bytes(4) + result

    @classmethod
    def from_bytes(cls, raw_data: bytes) -> "PeerPacket":
        length = int.from_bytes(raw_data[:4])
        logger.info(f"length = {length} len(raw_data) = {len(raw_data)}")
        try:
            message_type = MessageType(raw_data[4])
        except IndexError:
            logger.error(f"message_type: raw_data[4] = {raw_data[4]}")
            raise NotImplementedError
        if message_type == MessageType.REQUEST:
            return RequestPeerPacket.from_bytes(raw_data)
        if message_type == MessageType.PIECE:
            return PiecePeerPacket.from_bytes(raw_data)
        return PeerPacket(message_type=message_type, payload=raw_data[5:])


@dataclass
class RequestPayload(Packet):
    index: int
    offset: int
    length: int

    @property
    def to_bytes(self) -> bytes:
        index_bytes = self.index.to_bytes(4)
        offset_bytes = self.offset.to_bytes(4)
        length_bytes = self.length.to_bytes(4)
        return index_bytes + offset_bytes + length_bytes

    @classmethod
    def from_bytes(cls, raw_data: bytes) -> "RequestPayload":
        if len(raw_data) != 12:
            raise NotImplementedError
        index = int.from_bytes(raw_data[:4])
        offset = int.from_bytes(raw_data[4:8])
        length = int.from_bytes(raw_data[8:12])
        return RequestPayload(index=index, offset=offset, length=length)


@dataclass
class RequestPeerPacket(PeerPacket):
    message_type: MessageType = MessageType.REQUEST

    @property
    def parsed_payload(self) -> RequestPayload:
        return RequestPayload.from_bytes(self.payload)

    def __repr__(self) -> str:
        return f"RequestPeerPacket(message_type={self.message_type}, parsed_payload={self.parsed_payload})"


@dataclass
class PiecePayload(Packet):
    index: int
    begin: int
    block: bytes

    def __repr__(self) -> str:
        return (
            f"PiecePayload(index={self.index}, begin={self.begin}, len(block) = {len(self.block)}"
        )

    @property
    def to_bytes(self) -> bytes:
        index_bytes = self.index.to_bytes(4)
        begin = self.begin.to_bytes(4)
        return index_bytes + begin + self.block

    @classmethod
    def from_bytes(cls, raw_data: bytes) -> "PiecePayload":
        index = int.from_bytes(raw_data[:4])
        begin = int.from_bytes(raw_data[4:8])
        return PiecePayload(index=index, begin=begin, block=raw_data[8:])


@dataclass
class PiecePeerPacket(PeerPacket):
    message_type: MessageType = MessageType.PIECE

    @property
    def parsed_payload(self) -> PiecePayload:
        return PiecePayload.from_bytes(self.payload)

    def __repr__(self) -> str:
        return f"PiecePeerPacket(message_type={self.message_type}, parsed_payload={self.parsed_payload})"
