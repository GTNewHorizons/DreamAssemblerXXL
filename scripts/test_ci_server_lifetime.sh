#!/usr/bin/env bash
set -euo pipefail

# Taken from https://github.com/MalTeeez/packscripts-auto-builds/blob/gtnh-daily/packaging/scripts/entrypoint.sh

WORKDIR=$1
cd $WORKDIR

echo "Agreeing to eula"
sed -i "s|eula=false|eula=true|g" eula.txt

echo "Starting server..."
java -Xms1G -Xmx2G -Dfml.readTimeout=5 @java9args.txt -jar lwjgl3ify-forgePatches.jar nogui > server.log 2>&1 &
SERVER_PID=$!

tail -f server.log &
TAIL_PID=$!

echo "Waiting for startup..."
i=0
while [ $i -lt 24 ]; do
    if ! kill -0 $SERVER_PID 2>/dev/null; then
        echo "Server exited unexpectedly during startup"
        wait $SERVER_PID
        exit 1
    fi
    if grep -q "Done.*For help, type \"help\" or \"\?\"" server.log; then
        echo "Server started after $((i * 5))s"
        break
    fi
    i=$((i + 1))
    sleep 5
done

if [ $i -eq 24 ]; then
    echo "Startup timed out"
    kill $SERVER_PID || true
    exit 1
fi

echo "Waiting 60s for server to settle..."
sleep 60

if ! kill -0 $SERVER_PID 2>/dev/null; then
    echo "Server crashed during settling"
    wait $SERVER_PID
    exit 1
fi

echo "Stopping server..."
rcon-cli --host localhost --port 25575 --password whoahaplaintextpassword stop

if wait $SERVER_PID; then
    EXIT_CODE=0
else
    EXIT_CODE=$?
fi
kill $TAIL_PID 2>/dev/null || true

if [ $EXIT_CODE -ne 0 ]; then
    echo "Server exited with non-zero code: $EXIT_CODE"
    if [ -d crash-reports ] && [ -n "$(ls -A crash-reports 2>/dev/null)" ]; then
        echo "=== Crash Reports ==="
        for f in crash-reports/*; do
            echo "--- $f ---"
            cat "$f"
        done
    fi
fi

echo "Checking for no errors reported during server run"
bash /tmp/check_server_errors.sh $WORKDIR

exit $EXIT_CODE