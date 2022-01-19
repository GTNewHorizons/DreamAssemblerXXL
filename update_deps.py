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
    'CodeChickenLib': '1.1.5.1',
    'CodeChickenCore': '1.1.3',
    'NotEnoughItems': '2.1.22-GTNH',
    'ForgeMultipart': '1.2.7',
    'EnderCore': '0.2.6',
    'waila': '1.5.18',
    'inventory-tweaks': '1.5.13',
    'ForestryMC': '4.4.4',
    'Railcraft': '9.13.5',
    'Jabba': '1.2.13',
    'TinkersConstruct': '1.9.0.10-GTNH',
    'Natura': '2.4.8',
    'Mantle': '0.3.4',
    'harvestcraft': '1.0.10-GTNH',
    'AppleCore': '3.1.6',
    'Applied-Energistics-2-Unofficial': 'rv3-beta-70-GTNH',
    'GT5-Unofficial': '5.09.40.18',
    'Chisel': '2.10.6-GTNH',
    'StorageDrawers': '1.11.11-GTNH',
    'Baubles': '1.0.1.14',
    'EnderIO': '2.3.1.27',
    'Translocators': '1.1.2.19',
    'StructureLib': '1.0.14',
    'ironchest': '6.0.68',
    'EnderStorage': '1.4.11',
    'TinkersMechworks': '0.2.16.2',
    'BloodMagic': '1.3.5',
    'Avaritia': '1.22',
    'CraftTweaker': '3.2.5',
    'WanionLib': '1.8.2',
    'Avaritiaddons': '1.5.2-GTNH',
    'bdlib': '1.9.6',
    'gendustry': '1.6.5.3-GTNH',
    'WirelessRedstone-CBE': '1.4.4',
    'ProjectRed': '4.7.4',
    'ThaumicEnergistics': '1.3.16-GTNH',
    'Galacticraft': '3.0.36-GTNH',
    'WirelessCraftingTerminal': '1.8.8.3',
    'OpenComputers': '1.7.5.20-GTNH',
    'ExtraCells2': '2.5.4',
    'Nuclear-Control': '2.4.8',
    'Yamcl': '0.5.82',
    'SC2': '2.0.1',
    'GTplusplus': '1.7.24',
    'TecTech': '4.10.15',
    'GalacticGregGT5': '1.0.7',
    'ThaumicTinkerer': '2.6.0',
    'Botania': '1.9.1-GTNH',
}

DEP_FILE = 'dependencies.gradle'
REPO_FILE = 'repositories.gradle'
MOD_AND_VERSION = re.compile(r'"com\.github\.GTNewHorizons:([^:]+):([^:^)]+)')
MOD_VERSION_REPLACE = '"com.github.GTNewHorizons:{mod_name}:{version}'
GTNH_MAVEN = """
    maven {
        name = "GTNH Maven"
        url = "http://jenkins.usrv.eu:8081/nexus/content/groups/public/"
    }
"""


def find_and_update_deps() -> None:
    if not os.path.exists('dependencies.gradle'):
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
