rem don't forget to accept the EULA or it won't boot
java -Xms6G -Xmx6G -XX:+UseStringDeduplication -XX:+UseCompressedOops -XX:+UseCodeCacheFlushing -Dfml.readTimeout=180 -jar forge-1.7.10-10.13.4.1614-1.7.10-universal.jar nogui
pause
