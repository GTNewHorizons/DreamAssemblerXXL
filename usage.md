To setup DreamAssemblerXXL do the following steps:
1. Install python 3.10 or higher
3. Add a personal token, as described in [README.md](https://github.com/GTNewHorizons/DreamAssemblerXXL/blob/master/README.md)
4. clone the repository
5. open terminal/console in the root of the repository and type the following commands:
- `python -m pip install poetry`
- `poetry install`

To run DreamAssemblerXXL do type the following commands in a terminal/console at the root of the repository:
- (only if you are on windows) `chcp 65001`
- `poetry run python -m gtnh.gui.gui`

DreamAssemblerXXL can be splitted up in 3 categories: Modpack management (in green), Mod management (in red) and File exclusion management (in yellow)

![image](https://user-images.githubusercontent.com/12850933/187891144-e9cd9402-eaea-4a10-a658-a46094884f8b.png)

The modpack management section is used to manage the pack version: you can load a version in memory, add or update a version and delete a version. It can also build the pack for various plateforms. It also allows you to update the data about mod versions and allows you to do a experimental or daily build.

![image](https://user-images.githubusercontent.com/12850933/187900736-eb3fa793-f994-48c3-ad98-cff9cb3c0810.png)

The mod management section is used to chose mod versions and sides for the version loaded in memory.

![image](https://user-images.githubusercontent.com/12850933/187900515-b1592f86-8c35-4b6b-974c-e3ec1c220299.png)

The file exclusion management section allows you to remove certains files from GT-New-Horizons releases based on the side of the archive: server side or client side.

![image](https://user-images.githubusercontent.com/12850933/187896905-1bb63b0e-fad0-43fc-aa9f-21ebd37d7cd8.png)
