#!/usr/bin/env bash
# Server side of the integration run, should get started first and stopped when tests are done.
#
# This script does not decide whether a run was good. That should be verified later.

# Base logic from https://github.com/MalTeeez/packscripts-auto-builds/blob/gtnh-daily/packaging/scripts/entrypoint.sh

set -euo pipefail

RUN_DIR="${RUN_DIR:?RUN_DIR must be set}"
SERVER_DIR="${SERVER_DIR:?SERVER_DIR must be set}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

SERVER_LOG="$RUN_DIR/server.log"

RCON_HOST="${RCON_HOST:-localhost}"
RCON_PORT="${RCON_PORT:-25575}"
RCON_PASSWORD="${RCON_PASSWORD:?RCON_PASSWORD must be set}"

TAIL_PID=""

cleanup() {
  [ -n "$TAIL_PID" ] && kill "$TAIL_PID" 2>/dev/null
}

start() {
  local java_args="${SERVER_JAVA_ARGS:?SERVER_JAVA_ARGS must be set}"
  local start_timeout="${SERVER_START_TIMEOUT:-240}"
  local settle_duration="${SERVER_SETTLE_DURATION:-30}"

  trap cleanup EXIT INT TERM

  cd "$SERVER_DIR"
  sed -i 's|eula=false|eula=true|g' eula.txt
  sed -i "s|enable-rcon=false|enable-rcon=true\nrcon.password=${RCON_PASSWORD}\nrcon.port=${RCON_PORT}|" server.properties
  sed -i 's|online-mode=true|online-mode=false|' server.properties
  sed -i 's|white-list=true|white-list=false|' server.properties
  

  # Backgrounded and logged to a file so this CI step can finish while the JVM
  # keeps running into the next steps.
  bash "$SCRIPT_DIR/run_with_exit.sh" "$SERVER_EXIT_FLAG" java $java_args > "$SERVER_LOG" 2>&1 &

  tail -n +1 -F "$SERVER_LOG" 2>/dev/null &
  TAIL_PID=$!

  local waited=0
  while [ "$waited" -lt "$start_timeout" ]; do
    if grep -q 'Done.*For help, type' "$SERVER_LOG" 2>/dev/null; then
      echo "server started after ${waited}s"
      echo "waiting ${settle_duration}s for server to settle..."
      sleep $settle_duration

       if [ -e "$SERVER_EXIT_FLAG" ]; then
        echo "server exited during settling (code $(cat "$SERVER_EXIT_FLAG"))"
        return 1
      fi

      : > "$SERVER_READY_FLAG"
      return 0
    fi
    if [ -e "$SERVER_EXIT_FLAG" ]; then
      echo "server exited during startup (code $(cat "$SERVER_EXIT_FLAG"))"
      return 1
    fi
    sleep 5
    waited=$((waited + 5))
  done

  echo "server did not become ready within ${start_timeout}s"
  return 1
}

stop() {
  echo "stopping server via rcon"
  rcon-cli --host "$RCON_HOST" --port "$RCON_PORT" --password "$RCON_PASSWORD" stop
}

case "${1:?usage: server.sh start|stop}" in
  start) start ;;
  stop)  stop ;;
  *) echo "unknown command: $1" >&2; exit 2 ;;
esac