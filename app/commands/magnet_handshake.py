import asyncio

from app.logging_config import get_logger
from app.magnet_link import MagnetLink
from app.peer.peer import Peer

logger = get_logger(__name__)


def print_magnet_peer_id(magnet: str) -> str:  # noqa: WPS210
    magnet_link = MagnetLink(magnet)
    peers = magnet_link.get_peers()
    logger.info(f"peers = {peers}")
    result: list[str] = []
    for ip, port in peers:
        peer = Peer(
            ip=ip,
            port=int(port),
            info_hash=magnet_link.info_hash,
            extension_enabled=True,
        )
        peer_id = asyncio.run(peer.handshake())
        result.append(f"Peer ID: {peer_id}")
    return "\n".join(result)
