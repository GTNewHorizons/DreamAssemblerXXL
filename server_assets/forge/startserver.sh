#!/bin/bash
 
# don't forget to accept the EULA or it won't boot
while true
do
   java -Xms6G -Xmx6G -XX:+UseStringDeduplication -XX:+UseCompressedOops -XX:+UseCodeCacheFlushing -Dfml.readTimeout=180 -jar forge-1.7.10-10.13.4.1614-1.7.10-universal.jar nogui
    echo "If you want to completely stop the server process now, press Ctrl+C before the time is up!"
    echo "Rebooting in:"
    for i in 12 11 10 9 8 7 6 5 4 3 2 1
    do
        echo "$i..."
        sleep 1
    done
    echo "Rebooting now!"
done
