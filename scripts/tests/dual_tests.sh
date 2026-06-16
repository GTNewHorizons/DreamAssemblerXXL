#!/usr/bin/env bash
# Runs tests that are seen by both the server and the client while the client is connected.
#
# HeadlessNH parks the client at the serverloaded gate right after it joins, so
# for the length of this script the connection should live and we can poke it from
# both ends: the server (over RCON) and the client (xdotool, but probably not needed for now).
#
# The orchestrator should emit the gate once this one has run to release the client again.
# 
# A result should be verified later (like in other scripts)
set -uo pipefail
shopt -s nullglob

RUN_DIR="${RUN_DIR:?RUN_DIR must be set}"
CLIENT_MC_DIR="${CLIENT_MC_DIR:?CLIENT_MC_DIR must be set}"

RCON_HOST="${RCON_HOST:-localhost}"
RCON_PORT="${RCON_PORT:-25575}"
RCON_PASSWORD="${RCON_PASSWORD:?RCON_PASSWORD must be set}"

HQA_RESULT_JSON="$RUN_DIR/horizonqa-result.json"
HQA_RESULT_TIMEOUT="${HQA_RESULT_TIMEOUT:-45}" # Has to be lower than -Dheadlessnh.gate.timeout passed to client

RCON_RETRIES="${RCON_RETRIES:-10}"         # attempts per command before giving up

# Run a single rcon command, retrying on failures
rcon_try() {
  local attempt
  for ((attempt = 1; attempt <= RCON_RETRIES; attempt++)); do
    if rcon-cli --host "$RCON_HOST" --port "$RCON_PORT" --password "$RCON_PASSWORD" "$@"; then
      return 0
    fi
    echo "rcon attempt $attempt/$RCON_RETRIES failed: $*"
    sleep 0.5
  done
  return 1
}

# Send a command to the server via rcon, allows failures
rcon() {
  if ! rcon_try "$@"; then
    echo "rcon command failed (ignored): $*"
  fi
  sleep 0.1 # dont hammer the connection too much
}

# Same as above, but doesnt allow failures
rcon_strict() {
  if ! rcon_try "$@"; then
    echo "rcon command failed: $*"
    rc=1
  fi
  sleep 0.1
}

# Capture whatever each side emits for the length of this script (-n 0: new lines only)
tail -n 0 -F "$RUN_DIR/server.log" > "$RUN_DIR/dual_test_server.log" 2>/dev/null &
server_tail_pid=$!
tail -n 0 -F "$RUN_DIR/client.log" > "$RUN_DIR/dual_test_client.log" 2>/dev/null &
client_tail_pid=$!
trap 'kill "$server_tail_pid" "$client_tail_pid" 2>/dev/null' EXIT

rc=0

# Ask the server who's online
players_line=$(rcon list 2>&1)
echo "server 'list' -> $players_line"
online=$(printf '%s' "$players_line" | grep -oiE 'there are [0-9]+' | grep -oE '[0-9]+' | head -1)
if [ -n "$online" ] && [ "$online" -ge 1 ]; then
  echo "server reports $online player(s) online"
else
  echo "server sees no players -- client not visible from the server side?"
  rc=1
fi

# Setup & run HQA tests
rcon_strict "gamemode 1 CI"
rcon "tp CI -2 132 -2"

sleep 10 # give it some time to generate

rcon "setblock -2 134 -2 0"
rcon "setblock -2 133 -2 0"
rcon "setblock -2 132 -2 0"
rcon "setblock -2 131 -2 0"
rcon "setblock -2 130 -2 0"
rcon "setblock -2 129 -2 1"
rcon "setblock -2 128 -2 1"

rcon "tp CI -2 132 -2"
rcon "tp CI -2 132 -2"
rcon_strict "horizonqa runall"

crash_reports=("$CLIENT_MC_DIR/crash-reports/crash"*.txt)
if [ "${#crash_reports[@]}" -gt 0 ]; then
  echo "discovered new client crash report while connected: ${crash_reports[-1]##*/}"
  rc=1
fi

# Let the log lines each side emitted in reaction settle into the tails
sleep 2

# Wait for the HQA report file to appear before completing
waited=0
while [ ! -f "$HQA_RESULT_JSON" ]; do
  if [ "$waited" -ge "$HQA_RESULT_TIMEOUT" ]; then
    echo "timed out after ${HQA_RESULT_TIMEOUT}s waiting for $HQA_RESULT_JSON"
    rc=1
    break
  fi
  sleep 1
  waited=$((waited + 1))
done
if [ -f "$HQA_RESULT_JSON" ]; then
  echo "found HQA result after ${waited}s: $HQA_RESULT_JSON"
fi

echo "$rc" > "$DUAL_EXIT_FLAG"
[ "$rc" -eq 0 ] && echo "DUAL TESTS: initial pass" || echo "DUAL TESTS: initial fail"
exit "$rc"