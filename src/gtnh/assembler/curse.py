from gtnh.utils import get_curse_token


def get_headers() -> dict[str, str]:
    return {"Accept": "application/json", "x-api-key": get_curse_token()}
