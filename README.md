# DreamAssemblerXXL

A replacement for DreamMasterXXL, minus the nerfs.

* [gtnh-mods.json](gtnh-assets.json): All Mods that are part of the modpack, including license, versions, etc
* [releases](releases): Manifests for each officially released modpack version
* [repo-blacklist.json](repo-blacklist.json): GitHub repositories that are not part of the pack


### CLI - CLI Tools
* [add_mod.py](src/gtnh/cli/add_mod.py): Add a new (github) mod to the pack
* [assemble_release.py](src/gtnh/cli/assemble_release.py): Assemble a release ZIP (CLIENT/SERVER)
* [download_mod.py](src/gtnh/cli/download_mod.py): Download a mod to the cache
* [download_release.py](src/gtnh/cli/download_release.py): Download an entire release to the cache
* [generate_nightly.py](src/gtnh/cli/generate_nightly.py): Generate a manifest for a nightly release based on the latest version for all mods and config
* [update_check.py](src/gtnh/cli/update_check.py): Check for new releases on GitHub
* [update_deps.py](src/gtnh/cli/update_deps.py): Update dependencies.gradle & repositories.gradle (run in the project directory)

### Assembler - Modpack Assemble!
* [assembler.py](src/gtnh/assembler/assembler.py) Assemble the client and server pack (ZIP)
* [curse.py](src/gtnh/assembler/curse.py) Maybe, at some point, assemble the pack for Curse
* [downloader.py](src/gtnh/assembler/downloader.py): Download and cache the pack's mods
* [modrinth.py](src/gtnh/assembler/modrinth.py) Hopefully in the near future assemble the pack for Modrinth
* [multi_poly.py](src/gtnh/assembler/multi_poly.py) Hopefully in the near future assemble the pack for MultiMC/PolyMC
* [technic.py](src/gtnh/assembler/technic.py) Assemble the pack for Technic

### Scripts
* [black.sh](scripts/black.sh): Format things using the Black Formatter
* [isort.sh](scripts/isort.sh): Sort all the includes
* [lint.sh](scripts/lint.sh): Lint everything
* [mypy.sh](scripts/mypy.sh): Typing the untypable 
* [update_buildscript.sh](scripts/update_buildscript.sh): Script to add CODEOWNERS for maven publication

### GUI
* [gui.py](src/gtnh/gui/gui.py) GUI Frontend to the DreamAssemblerXXL

# Note to contributors
Code PRs should always be done against the master branch.

# Github Personal Access Token

A personal access token is required to hit the github API without getting rate limited, and to be able to view any private repositories.  
Create a github personal access token with the following permissions, and paste it into `~/.github_personal_token` on linux or `C:\users\<you>\.github_personal_token` 
on Windows, with a newline at the end.

![image](https://user-images.githubusercontent.com/1894689/162634764-7d343964-bdee-4e87-aa4a-8aa2fd90cd2c.png)

![image](https://user-images.githubusercontent.com/1894689/162634755-f625cdf8-6f1b-4f80-adef-b37f97a8301f.png)
