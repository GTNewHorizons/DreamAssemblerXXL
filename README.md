# DreamAssemblerXXL

Scripts to update dependencies and add GTNH maven

* [gtnh-modpack.json](gtnh-modpack.json): Modpack Manifest: Mods, licenses, version, etc
* [repo-blacklist.json](repo-blacklist.json): GitHub repositories that are not part of the pack
* [update_deps.py](src/gtnh/update_deps.py): Update dependencies.gradle & repositories.gradle (run in the project directory)
* [pack_downloader.py](src/gtnh/pack_downloader.py): Download the pack
* [add_mod.py](src/gtnh/add_mod.py): Add a new mod to the pack
* [update_check.py](src/gtnh/update_check.py): Check for new releases on GitHub
* [update_buildscript.sh](update_buildscript.sh): Script to add CODEOWNERS for maven publication
* [requirements.txt](requirements.txt): Python modules you'll need to run - Python 3.9+ is required
