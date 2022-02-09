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

import os.path
import re

from in_place import InPlace
from utils import load_gtnh_manifest

DEP_FILE = "dependencies.gradle"
REPO_FILE = "repositories.gradle"
MOD_AND_VERSION = re.compile(r"[\"\']com\.github\.GTNewHorizons:([^:]+):([^:^)]+)")
MOD_VERSION_REPLACE = "com.github.GTNewHorizons:{mod_name}:{version}"
GTNH_MAVEN = """
    maven {
        name = 'GTNH Maven'
        url = 'http://jenkins.usrv.eu:8081/nexus/content/groups/public/'
        allowInsecureProtocol
    }
"""


def find_and_update_deps() -> None:
    if not os.path.exists(DEP_FILE):
        print(f"ERROR: Unable to locate {DEP_FILE} in the current directory")
        return
    gtnh_mod_info = load_gtnh_manifest()

    with InPlace(DEP_FILE) as fp:
        for line in fp:
            match = MOD_AND_VERSION.search(line)
            if match is not None:
                mod_name, mod_version = match[1], match[2]
                if gtnh_mod_info.has_github_mod(mod_name):
                    mod_info = gtnh_mod_info.get_github_mod(mod_name)
                    latest_version = mod_info.version
                    if mod_version != latest_version:
                        print(f"Updating {mod_name} from `{mod_version}` to '{latest_version}'")
                        line = line.replace(
                            MOD_VERSION_REPLACE.format(mod_name=mod_name, version=mod_version),
                            MOD_VERSION_REPLACE.format(mod_name=mod_name, version=latest_version),
                        )
                        fp.write(line)
                        continue
                    else:
                        print(f"{mod_name} is already at the latest version '{latest_version}'")
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


if __name__ == "__main__":
    find_and_update_deps()
    verify_gtnh_maven()
