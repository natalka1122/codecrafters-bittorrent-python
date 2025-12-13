def _hex(number: int) -> str:
    result = hex(number)[2:]
    return "0" * (2 - len(result)) + result


def hex20(raw_data: bytes) -> str:
    return "".join(map(_hex, raw_data))
