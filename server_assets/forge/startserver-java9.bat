rem don't forget to accept the EULA or it won't boot
rem add this argument behind the other "-Dfml..." to silently migrate your world during startup, a backup will be created: Dfml.queryResult=confirm
java -Xms6G -Xmx6G -Dfml.readTimeout=180 @java9args.txt -jar lwjgl3ify-forgePatches.jar nogui
pause
