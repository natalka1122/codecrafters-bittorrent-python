import re
from urllib.parse import unquote


def print_magnet_info(magnet: str) -> str:
    match = re.match(
        r"magnet:\?xt=urn:btih:(?P<hash>[\w]{40})&dn=(?P<filename>[\w\.]+)&tr=(?P<tracker>[\w%-\.]+)",
        magnet,
    )
    if match is None:
        raise NotImplementedError
    info_hash = match.groupdict()["hash"]
    tracker_url = unquote(match.groupdict()["tracker"])
    result = [
        f"Tracker URL: {tracker_url}",
        f"Info Hash: {info_hash}",
    ]
    return "\n".join(result)
