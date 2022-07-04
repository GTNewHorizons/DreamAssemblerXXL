from typing import Any

from httpx import AsyncClient
from structlog import get_logger

from gtnh.defs import CURSE_BASE_URL, CURSE_FORGE_MODLOADER_ID, CURSE_GAME_VERSION_TYPE_ID, CURSE_MINECRAFT_ID
from gtnh.models.mod_info import ExternalModInfo
from gtnh.utils import get_curse_token, grouper

log = get_logger(__name__)


def get_headers() -> dict[str, str]:
    return {"Accept": "application/json", "x-api-key": get_curse_token()}


async def slug_to_project_id(slug: str, client: AsyncClient) -> str:
    response = await client.get(
        url=CURSE_BASE_URL + "/v1/mods/search",
        headers=get_headers(),
        params={
            "gameId": CURSE_MINECRAFT_ID,
            "gameVersionTypeId": CURSE_GAME_VERSION_TYPE_ID,
            "modLoaderType": CURSE_FORGE_MODLOADER_ID,
            "slug": slug,
        },
    )
    if response.status_code != 200:
        log.error(f"Cannot find mod by slug {slug}!")
        return "<unknown>"

    curse_info = response.json()
    data = curse_info["data"]
    if len(data) == 1:
        return data[0]["id"]
    elif len(data) == 0:
        log.error(f"Could not find by slug {slug}")
    else:
        log.error(f"Found too many mods ({len(data)}) for slug {slug}")

    return "<unknown>"


async def get_mods(mods: list[ExternalModInfo], client: AsyncClient) -> list[dict[str, Any]]:
    mod_ids = [m.project_id for m in mods]

    curse_info = []
    for id_chunk in grouper(50, mod_ids):
        response = await client.post(
            url=CURSE_BASE_URL + "/v1/mods",
            headers=get_headers() | {"Content-Type": "application/json"},
            json={"modIds": id_chunk},
        )
        if response.status_code != 200:
            log.exception(f"Error getting mods! {response.status_code}")
            return []

        curse_info.extend(response.json()["data"])

    return curse_info


async def get_mod_files(mod: ExternalModInfo, client: AsyncClient):
    params = {
        "gameVersionTypeId": CURSE_GAME_VERSION_TYPE_ID,
        "modLoaderType": CURSE_FORGE_MODLOADER_ID,
    }
    index = 0
    has_more = True
    mod_files = []
    while has_more:
        response = await client.get(
            url=CURSE_BASE_URL + f"/v1/mods/{mod.project_id}/files",
            headers=get_headers(),
            params=params | {"index": index},
        )
        if response.status_code != 200:
            log.exception(f"Error getting mod files! {response.status_code}")
            return mod_files
        response_json = response.json()
        if "pagnation" not in response_json:
            has_more = False
        else:
            pagnation = response_json["pagnation"]
            result_count = pagnation.get("resultCount", 0)
            total_count = pagnation.get("totalCount", 0)
            page_size = pagnation.get("pageSize", 50)
            if total_count < 50 or result_count < page_size or index + page_size >= total_count:
                has_more = False
            index += page_size
        mod_files.extend(response_json.get("data", []))

    return mod_files
