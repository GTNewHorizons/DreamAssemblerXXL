#!/usr/bin/env bash
# Orchestrates an integration test in a headless env between a client and a server
#
# This should only ever fail on operational problems.
# That roughly means something not starting, or a precondition for a next step is missing.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

WORK_DIR="${WORK_DIR:?WORK_DIR must be set}"
CLIENT_DIR="${CLIENT_DIR:-$WORK_DIR/client}"
CLIENT_MC_DIR="${CLIENT_MC_DIR:-$CLIENT_DIR/.minecraft}"
SERVER_DIR="${SERVER_DIR:-$WORK_DIR/server}"
RUN_DIR="${RUN_DIR:-$WORK_DIR/run}"
export CLIENT_DIR CLIENT_MC_DIR SERVER_DIR RUN_DIR

SERVER_READY_FLAG="$RUN_DIR/server.ready"
SERVER_EXIT_FLAG="$RUN_DIR/server.exit"
CLIENT_LOADED_FLAG="$RUN_DIR/.mainmenu.headlessnh"
CLIENT_JOINED_FLAG="$RUN_DIR/.serverloaded.headlessnh"
CLIENT_SINGLEP_FLAG="$RUN_DIR/.worldloaded.headlessnh"
DUAL_EXIT_FLAG="$RUN_DIR/.dual.exit"
CLIENT_GATE_SERVERLOADED="$RUN_DIR/serverloaded.gate"
export SERVER_READY_FLAG SERVER_EXIT_FLAG CLIENT_LOADED_FLAG CLIENT_JOINED_FLAG CLIENT_SINGLEP_FLAG DUAL_EXIT_FLAG CLIENT_GATE_SERVERLOADED

SERVER_STOP_TIMEOUT="${SERVER_STOP_TIMEOUT:-20}"
DUAL_TEST_WAIT="${DUAL_TEST_WAIT:-360}"

start_server() {
  rm -rf "$RUN_DIR" && mkdir -p "$RUN_DIR"
  bash "$SCRIPT_DIR/server.sh" start
}

# Screenshot the virtual display whenever a client marker first appears,
watch_markers() {
  local -A seen=()
  local m name
  while :; do
    for m in "$CLIENT_LOADED_FLAG" "$CLIENT_JOINED_FLAG" "$DUAL_EXIT_FLAG" "$CLIENT_SINGLEP_FLAG"; do
      if [ -e "$m" ] && [ -z "${seen[$m]:-}" ]; then
        seen[$m]=1
        name="$(basename "$m" | cut -d. -f2)"
        if scrot -o "$RUN_DIR/screenshot.$name.png" 2>/dev/null; then
          echo "marker '$name' appeared -- saved screenshot.$name.png"
        else
          echo "marker '$name' appeared -- screenshot failed"
        fi
      fi
    done
    sleep 0.5
  done
}

# Triggers dual tests once the client has joined &
# releases the client gate once the test are done
run_dual_tests() {
  local waited=0
  while [ ! -e "$CLIENT_JOINED_FLAG" ]; do
    if [ "$waited" -ge "$DUAL_TEST_WAIT" ]; then
      echo "client never joined within ${DUAL_TEST_WAIT}s -- skipping dual tests"
      return
    fi
    sleep 1
    waited=$((waited + 1))
  done

  bash "$SCRIPT_DIR/dual_tests.sh" > "$RUN_DIR/dual_test_executor.log" 2>&1 || true

  sleep 2 # give time for screenshot

  : > "$CLIENT_GATE_SERVERLOADED"
  echo "dropped serverloaded gate -> $CLIENT_GATE_SERVERLOADED"
}

run_client() {
  [ -e "$SERVER_READY_FLAG" ] || { echo "server never signalled ready"; exit 1; }

  export DISPLAY=":${DISPLAY_NUM:-99}"
  watch_markers &
  local watcher_pid=$!
  run_dual_tests &
  local dual_pid=$!

  local rc=0
  bash "$SCRIPT_DIR/headless_client.sh" || rc=$?

  kill "$watcher_pid" "$dual_pid" 2>/dev/null || true
  wait "$watcher_pid" "$dual_pid" 2>/dev/null || true
  return "$rc"
}

stop_server() {
  bash "$SCRIPT_DIR/server.sh" stop

  local waited=0
  while [ ! -e "$SERVER_EXIT_FLAG" ]; do
    [ "$waited" -ge "$SERVER_STOP_TIMEOUT" ] && { echo "server did not stop within ${SERVER_STOP_TIMEOUT}s"; exit 1; }
    sleep 2
    waited=$((waited + 2))
  done
  echo "server stopped (code $(cat "$SERVER_EXIT_FLAG"))"
}

case "${1:?usage: orchestrator.sh start-server|run-client|run-dual-tests|stop-server|verify-server|verify-client}" in
  start-server)   start_server ;;
  run-client)     run_client ;;
  run-dual-tests) run_dual_tests ;;
  stop-server)    stop_server ;;
  verify-server)  bash "$SCRIPT_DIR/verify_server.sh" ;;
  verify-client)  bash "$SCRIPT_DIR/verify_client.sh" ;;
  *) echo "unknown command: $1" >&2; exit 2 ;;
esac