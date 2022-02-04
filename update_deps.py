#!/usr/bin/env python3

#
# update_deps.py
#
# Run in a directory with `dependencies.gradle`.
#
# It will :
# 1) look for any deps of the format "com.github.GTNewHorizons:{mod_name}:{version}'[:qualifier]" and update them to the latest in this file
# 2) Ensure `repositories.gradle` has the GTNH maven
#
# Requires python3 and the `in_place` package
#

import re
import os.path
from in_place import InPlace

LATEST_VERSIONS = {
    'AdventureBackpack2': '1.0.4-GTNH',
    'AMDIForge': '1.0.3',
    'AppleCore': '3.1.9',
    'Applied-Energistics-2-Unofficial': 'rv3-beta-74-GTNH',
    'AsieLib': '0.5.2',
    'Avaritia': '1.22',
    'Avaritiaddons': '1.5.3-GTNH',
    'bartworks': '0.5.36',
    'Battlegear2': '1.1.1.8',
    'Baubles': '1.0.1.14',
    'bdlib': '1.9.6',
    'BloodMagic': '1.3.5',
    'Botania': '1.9.1-GTNH',
    'BuildCraft': '7.1.24',
    'BuildCraftCompat': '7.1.9',
    'Chisel': '2.10.6-GTNH',
    'CodeChickenCore': '1.1.3',
    'CodeChickenLib': '1.1.5.3',
    'CookingForBlockheads': '1.2.7-GNTH',
    'CraftTweaker': '3.2.6',
    'Computronics': '1.6.10-GTNH',
    'CropLoadCore': '0.1.8',
    'Crops-plus-plus': '1.3.5.9',
    'EnderCore': '0.2.6',
    'EnderIO': '2.3.1.27',
    'EnderStorage': '1.4.11',
    'ExtraCells2': '2.5.6',
    'ForestryMC': '4.4.5',
    'ForgeMultipart': '1.2.7',
    'GalacticGregGT5': '1.0.7',
    'Galacticraft': '3.0.37-GTNH',
    'GalaxySpace': '1.1.13-GTNH',
    'gendustry': '1.6.5.3-GTNH',
    'GT5-Unofficial': '5.09.40.31',
    'GTplusplus': '1.7.27',
    'harvestcraft': '1.0.12-GTNH',
    'HoloInventory': '2.1.7-GTNH',
    'inventory-tweaks': '1.5.13',
    'ironchest': '6.0.68',
    'Jabba': '1.2.13',
    'Mantle': '0.3.4',
    'Natura': '2.4.9',
    'NewHorizonsCoreMod': '1.9.19',
    'NotEnoughEnergistics': '1.3.9',
    'NotEnoughItems': '2.2.5-GTNH',
    'Nuclear-Control': '2.4.8',
    'OpenComputers': '1.7.5.20-GTNH',
    'ProjectRed': '4.7.4',
    'QmunityLib': '0.1.115',
    'Railcraft': '9.13.5',
    'SC2': '2.0.1',
    'SleepingBags': '0.1.2',
    'StorageDrawers': '1.11.11-GTNH',
    'StructureLib': '1.0.15',
    'TecTech': '4.10.18',
    'ThaumicEnergistics': '1.3.16-GTNH',
    'ThaumicTinkerer': '2.6.0',
    'TinkersConstruct': '1.9.0.13-GTNH',
    'TinkersMechworks': '0.2.16.3',
    'Translocators': '1.1.2.19',
    'waila': '1.5.18',
    'WanionLib': '1.8.2',
    'WirelessCraftingTerminal': '1.8.8.3',
    'WirelessRedstone-CBE': '1.4.4',
    'Yamcl': '0.5.82',
}

DEP_FILE = 'dependencies.gradle'
REPO_FILE = 'repositories.gradle'
MOD_AND_VERSION = re.compile(r'[\"\']com\.github\.GTNewHorizons:([^:]+):([^:^)]+)')
MOD_VERSION_REPLACE = 'com.github.GTNewHorizons:{mod_name}:{version}'
GTNH_MAVEN = """
    maven {
        name = "GTNH Maven"
        url = "http://jenkins.usrv.eu:8081/nexus/content/groups/public/"
    }
"""


def find_and_update_deps() -> None:
    if not os.path.exists(DEP_FILE):
        print(f"ERROR: Unable to locate {DEP_FILE} in the current directory")
        return

    with InPlace(DEP_FILE) as fp:
        for line in fp:
            match = MOD_AND_VERSION.search(line)
            if match is not None:
                mod_name, mod_version = match[1], match[2]
                if mod_name in LATEST_VERSIONS:
                    new_version = LATEST_VERSIONS.get(mod_name)
                    if mod_version != new_version:
                        print(f"Updating {mod_name} from `{mod_version}` to '{new_version}'")
                        line = line.replace(MOD_VERSION_REPLACE.format(mod_name=mod_name, version=mod_version), MOD_VERSION_REPLACE.format(mod_name=mod_name, version=new_version))
                        fp.write(line)
                        continue
                    else:
                        print(f"{mod_name} is already at the latest version '{new_version}'")
                else:
                    print(f"No latest version info for mod {mod_name}")

            # No match
            fp.write(line)


def verify_gtnh_maven() -> None:
    if not os.path.exists(REPO_FILE):
        print(f"ERROR: Unable to locate {REPO_FILE} in the current directory")
        return

    with open(REPO_FILE) as fp:
        repos = fp.read()
        if repos.find("http://jenkins.usrv.eu:8081/nexus/content/groups/public/") != -1:
            print("GTNH Maven already found")
            return

    with InPlace(REPO_FILE) as fp:
        print("Adding GTNH Maven")
        repos = fp.read()
        repos = repos.replace("repositories {\n", "repositories {" + GTNH_MAVEN)
        fp.write(repos)


if __name__ == '__main__':
    find_and_update_deps()
    verify_gtnh_maven()
