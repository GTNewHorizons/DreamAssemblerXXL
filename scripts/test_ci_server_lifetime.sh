#!/usr/bin/env bash
set -euo pipefail

# Taken from https://github.com/MalTeeez/packscripts-auto-builds/blob/gtnh-daily/packaging/scripts/entrypoint.sh

WORKDIR="${WORKDIR:?WORKDIR must be set}"
JAVA_ARGS="${JAVA_ARGS:?JAVA_ARGS must be set}"
STARTUP_TIMEOUT="${STARTUP_TIMEOUT:-240}"
SETTLE_TIMEOUT="${SETTLE_TIMEOUT:-60}"

cd $WORKDIR

echo "Agreeing to eula"
sed -i "s|eula=false|eula=true|g" eula.txt

echo "Starting server with 'java $JAVA_ARGS > server.log 2>&1 &'"
java $JAVA_ARGS > server.log 2>&1 &
SERVER_PID=$!

tail -f server.log &
TAIL_PID=$!

echo "Waiting for startup..."
i=0
while [ $i -lt $STARTUP_TIMEOUT ]; do
    if ! kill -0 $SERVER_PID 2>/dev/null; then
        echo "Server exited unexpectedly during startup"
        wait $SERVER_PID
        exit 1
    fi
    if grep -q "Done.*For help, type \"help\" or \"\?\"" server.log; then
        echo "Server started after ${i}s"
        break
    fi
    i=$((i + 5))
    sleep 5
done

if [ $i -ge $STARTUP_TIMEOUT ]; then
    echo "Startup timed out after waiting $STARTUP_TIMEOUT seconds"
    kill $SERVER_PID || true
    exit 1
fi

echo "Waiting ${SETTLE_TIMEOUT}s for server to settle..."
sleep $SETTLE_TIMEOUT

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