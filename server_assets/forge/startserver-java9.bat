rem don't forget to accept the EULA or it won't boot
java -Xms6G -Xmx6G -XX:+UseShenandoahGC -Dfml.readTimeout=180 @java9args.txt nogui
