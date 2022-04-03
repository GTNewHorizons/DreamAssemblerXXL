from typing import Dict, List, Union

from gtnh.utils import load_gtnh_manifest


def generate_deploader_data() -> List[Dict[str, Union[str, bool]]]:
    """
    Generates the data needed for the deploader.json used in curse instances.

    :return:
    """
    gtnh_metadata = load_gtnh_manifest()

    data: List[Dict[str, Union[str, bool]]] = []
    # processing external mods not on curse:
    data.extend([])

    for mod in gtnh_metadata.external_mods:
        if mod.download_url is None:
            raise TypeError(f"{mod.name} has no download url. Check its attributes and retry.")

        if mod.download_url.startswith("https://media.forgecdn.net") or mod.side not in ["CLIENT", "BOTH"]:
            continue

        mod_data: Dict[str, Union[str, bool]] = {"url": mod.download_url, "path": f"/mods/{mod.filename}", "disabled": False}

        data.append(mod_data)

    # processing github mods
    # warning: boubou mixed up download_url and browser_download_url fields between external and github mods

    for mod in gtnh_metadata.github_mods:
        if mod.browser_download_url is None:
            raise TypeError(f"{mod.name} has no browser download url. Check its attributes and retry.")

        if mod.side not in ["CLIENT", "BOTH"]:
            continue

        mod_data = {"url": mod.browser_download_url, "path": f"/mods/{mod.filename}", "disabled": False}

        data.append(mod_data)

    return data
