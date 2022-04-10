# DreamAssemblerXXL

Scripts to update dependencies and add GTNH maven

* [gtnh-modpack.json](gtnh-modpack.json): Modpack Manifest: Mods, licenses, version, etc
* [releases](releases): Manifests for each officially released modpack version
* [repo-blacklist.json](repo-blacklist.json): GitHub repositories that are not part of the pack
* [update_deps.py](src/gtnh/update_deps.py): Update dependencies.gradle & repositories.gradle (run in the project directory)
* [pack_downloader.py](src/gtnh/pack_downloader.py): Download the pack
* [add_mod.py](src/gtnh/add_mod.py): Add a new mod to the pack
* [update_check.py](src/gtnh/update_check.py): Check for new releases on GitHub
* [update_buildscript.sh](update_buildscript.sh): Script to add CODEOWNERS for maven publication
* [requirements.txt](requirements.txt): Python modules you'll need to run - Python 3.9+ is required


# Github Personal Access Token

A personal access token is required to hit the github API without getting rate limited, and to be able to view any private repositories.  Create a github personal access token with the following permissions, and place it into `~/.github_personal_token` on linux or `C:\users\<you>\.github_personal_token` on Windows

![image](https://user-images.githubusercontent.com/1894689/162634764-7d343964-bdee-4e87-aa4a-8aa2fd90cd2c.png)

![image](https://user-images.githubusercontent.com/1894689/162634755-f625cdf8-6f1b-4f80-adef-b37f97a8301f.png)
