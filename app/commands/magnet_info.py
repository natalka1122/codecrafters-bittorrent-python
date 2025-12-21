from app.magnet_link import MagnetLink


def print_magnet_info(magnet: str) -> str:
    magnet_link = MagnetLink(magnet)
    result = [
        f"Tracker URL: {magnet_link.tracker_url}",
        f"Info Hash: {magnet_link.info_hash_hex}",
    ]
    return "\n".join(result)
