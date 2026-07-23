# DreamAssemblerXXL

A replacement for DreamMasterXXL, minus the nerfs.

* [gtnh-mods.json](gtnh-assets.json): All Mods that are part of the modpack, including license, versions, etc
* [releases](releases): Manifests for each officially released modpack version
* [repo-blacklist.json](repo-blacklist.json): GitHub repositories that are not part of the pack


### CLI - CLI Tools
* [assemble_daily.py](src/daxxl/cli/assemble_daily.py): Assemble a new daily build (needs the manifest to exist prior to run this)
* [assemble_experimental.py](src/daxxl/cli/assemble_daily.py): Assemble a new experimental build (needs the manifest to exist prior to run this)
* [assemble_release.py](src/daxxl/cli/assemble_release.py): Assemble a release ZIP (CLIENT/SERVER)
* [download_mod.py](src/daxxl/cli/download_mod.py): Download the given mod to the cache
* [download_release.py](src/daxxl/cli/download_release.py): Download an entire release to the cache
* [generate_daily.py](src/daxxl/cli/generate_daily.py): Generate a manifest for a daily release based on the latest non-pre version for all mods and config
* [generate_experimental.py](src/daxxl/cli/generate_experimental.py): Generate a manifest for a experimental release based on the latest version for all mods and config
* [update_check.py](src/daxxl/cli/update_check.py): Check for new releases on GitHub

### Assembler - Modpack Assemble!
* [assembler.py](src/daxxl/assembler/assembler.py) Assemble the client and server pack (ZIP)
* [curse.py](src/daxxl/assembler/curse.py) Maybe, at some point, assemble the pack for Curse
* [downloader.py](src/daxxl/assembler/downloader.py): Download and cache the pack's mods
* [modrinth.py](src/daxxl/assembler/modrinth.py) Hopefully in the near future assemble the pack for Modrinth
* [multi_poly.py](src/daxxl/assembler/multi_poly.py) Hopefully in the near future assemble the pack for MultiMC/PolyMC
* [technic.py](src/daxxl/assembler/technic.py) Assemble the pack for Technic

### GUI
* [gui.py](src/daxxl/gui/gui.py) GUI Frontend to the DreamAssemblerXXL

# Note to contributors
Code PRs should always be done against the master branch.

# Github Personal Access Token

A personal access token is required to hit the github API without getting rate limited, and to be able to view any private repositories.  
Create a github personal access token with the following permissions, and paste it into `~/.github_personal_token` on linux or `C:\users\<you>\.github_personal_token` 
on Windows, with a newline at the end.

![image](https://user-images.githubusercontent.com/1894689/162634764-7d343964-bdee-4e87-aa4a-8aa2fd90cd2c.png)

![image](https://user-images.githubusercontent.com/1894689/162634755-f625cdf8-6f1b-4f80-adef-b37f97a8301f.png)
