#!/usr/bin/env bash
# Client side of the integration run, should get started once the server (at localhost) is up.
# 
# We handle the virtual display, starting the client, the recording and related here. 
# What the client itself does (joining the server, creating & joining a new sp world)
# is handled by HeadlessNH (which should be placed in the mods folder as part of setup)
# See https://github.com/MalTeeez/HeadlessNH
#
# To launch from the client install we need (beforehand, externally):
# - A .env file that contains all environment variables that are required for running headlessly
# - A .argv file that contains all the arguments we are launching, starting with the java binary
# - All the libraries and natives referenced in the .argv
#
# Same as with the server, we do not decide if a run was good here, that should happen afterwards 

set -uo pipefail

RUN_DIR="${RUN_DIR:?RUN_DIR must be set}"
CLIENT_DIR="${CLIENT_DIR:?CLIENT_DIR must be set}"
CLIENT_MC_DIR="${CLIENT_MC_DIR:-$CLIENT_DIR/.minecraft}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

CLIENT_LOG="$RUN_DIR/client.log"
CLIENT_EXIT_FLAG="$RUN_DIR/client.exit"
CLIENT_KILLED_FLAG="$RUN_DIR/client.killed"
CLIENT_VIDEO="$RUN_DIR/client.mp4"
XVFB_LOG="$RUN_DIR/xvfb.log"

CLIENT_LAUNCH_ENV="${CLIENT_LAUNCH_ENV:-$CLIENT_DIR/launch.env}"
CLIENT_LAUNCH_ARGV="${CLIENT_LAUNCH_ARGV:-$CLIENT_DIR/launch.argv}"
CLIENT_WINDOW_NAME="${CLIENT_WINDOW_NAME:-Minecraft}"
CLIENT_RUN_TIMEOUT="${CLIENT_RUN_TIMEOUT:-360}"     # force the game closed if it runs longer than this (def 6 mins)
CLIENT_GRACE_TIMEOUT="${CLIENT_GRACE_TIMEOUT:-10}"  # time allowed for save & exit after a nice close (def 10 secs)

DISPLAY_NUM="${DISPLAY_NUM:-99}"
RECORD_RESOLUTION="${RECORD_RESOLUTION:-854x480}"   # shared by Xvfb -screen and ffmpeg -video_size
RECORD_DEPTH=24
RECORD_FPS="${RECORD_FPS:-5}"
RECORD_MAX_SECONDS="${RECORD_MAX_SECONDS:-590}"     # hard cap on recording length
RECORD_FONT="${RECORD_FONT:-/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf}"

[ -f "$CLIENT_LAUNCH_ENV" ]  || { echo "launch env file missing: $CLIENT_LAUNCH_ENV"; exit 1; }
[ -f "$CLIENT_LAUNCH_ARGV" ] || { echo "launch argv file missing: $CLIENT_LAUNCH_ARGV"; exit 1; }

FFMPEG_PID=""
GAME_PGID=""
XVFB_PID=""
TAIL_PID=""

stop_ffmpeg() {
  if [ -n "$FFMPEG_PID" ] && kill -0 "$FFMPEG_PID" 2>/dev/null; then
    kill -INT "$FFMPEG_PID" 2>/dev/null
    wait "$FFMPEG_PID" 2>/dev/null
  fi
}

# Ask the window to close the way clicking the X would. Works with no window
# manager present, which is why it is sent by hand. Needs python3-xlib.
close_window_nicely() {
  local wid
  wid=$(xdotool search --onlyvisible --name "$CLIENT_WINDOW_NAME" 2>/dev/null | head -1) || return 1
  [ -n "$wid" ] || return 1
  python3 - "$wid" <<'PY' 2>/dev/null || return 1
import sys
from Xlib import X, display
from Xlib.protocol import event
d = display.Display()
w = d.create_resource_object('window', int(sys.argv[1], 0))
w.send_event(event.ClientMessage(
    window=w,
    client_type=d.intern_atom('WM_PROTOCOLS'),
    data=(32, [d.intern_atom('WM_DELETE_WINDOW'), X.CurrentTime, 0, 0, 0])))
d.flush()
PY
}

cleanup() {
  [ -n "$GAME_PGID" ] && kill -TERM -- "-$GAME_PGID" 2>/dev/null
  stop_ffmpeg
  [ -n "$XVFB_PID" ] && kill -TERM "$XVFB_PID" 2>/dev/null
  [ -n "$TAIL_PID" ] && kill "$TAIL_PID" 2>/dev/null
}
trap cleanup INT TERM

# 1. setup virtual screen
Xvfb ":$DISPLAY_NUM" -screen 0 "${RECORD_RESOLUTION}x${RECORD_DEPTH}" -nolisten tcp > "$XVFB_LOG" 2>&1 &
XVFB_PID=$!
sock="/tmp/.X11-unix/X$DISPLAY_NUM"
for _ in $(seq 1 60); do
  [ -S "$sock" ] && break
  kill -0 "$XVFB_PID" 2>/dev/null || { echo "Xvfb failed to start (see $XVFB_LOG)"; exit 1; }
  sleep 0.5
done
[ -S "$sock" ] || { echo "display :$DISPLAY_NUM never appeared"; cleanup; exit 1; }
sleep 1
export DISPLAY=":$DISPLAY_NUM"
echo "Xvfb up on :$DISPLAY_NUM"

# 2. record the screen (with a system-clock overlay) before the game starts.
#    Fragmented mp4 so the file is viewable even if the run is cut short.
ffmpeg -nostdin -loglevel warning -y \
  -f x11grab -draw_mouse 0 -framerate "$RECORD_FPS" -video_size "$RECORD_RESOLUTION" -i "$DISPLAY" \
  -vf "drawtext=fontfile=$RECORD_FONT:text='%{localtime\:%F %T}':x=10:y=10:fontsize=24:fontcolor=white:box=1:boxcolor=black@0.6:boxborderw=8" \
  -t "$RECORD_MAX_SECONDS" -c:v libx264 -pix_fmt yuv420p -g 10 -r "$RECORD_FPS" \
  -movflags +frag_keyframe+empty_moov+default_base_moof -f mp4 "$CLIENT_VIDEO" &
FFMPEG_PID=$!
sleep 2
if ! kill -0 "$FFMPEG_PID" 2>/dev/null; then
  echo "WARNING: ffmpeg exited immediately; continuing without a recording"
  FFMPEG_PID=""
else
  echo "recording -> $CLIENT_VIDEO"
fi

# 3. launch the game in its own process group so a single signal cleans up everything. 
#    run_with_exit.sh records the game's code to client.exit
cd "$CLIENT_MC_DIR"
echo "maxFps:10" >> options.txt
setsid bash "$SCRIPT_DIR/run_with_exit.sh" "$CLIENT_EXIT_FLAG" \
  bash -c 'env $(grep -v "^\s*#" "$1" | xargs) "$(head -1 "$2")" @<(tail -n +2 "$2")' \
  _ "$CLIENT_LAUNCH_ENV" "$CLIENT_LAUNCH_ARGV" \
  > "$CLIENT_LOG" 2>&1 &
GAME_PGID=$!
echo "launched game (process group $GAME_PGID) -> $CLIENT_LOG"

tail -n +1 -F "$CLIENT_LOG" 2>/dev/null &
TAIL_PID=$!

# focus window, --sync blocks until the window maps
if timeout ${CLIENT_FOCUS_TIMEOUT:-60} xdotool search --sync --onlyvisible --name "$CLIENT_WINDOW_NAME" windowfocus 2>/dev/null; then
  echo "focused '$CLIENT_WINDOW_NAME' window"
else
  echo "WARNING: no '$CLIENT_WINDOW_NAME' window to focus within 60s"
fi

# 4. close game when last marker appears, break if it takes too long
start=$(date +%s)
while kill -0 -- "-$GAME_PGID" 2>/dev/null; do
  if [ -e "$CLIENT_SINGLEP_FLAG" ]; then
    echo "ready-file $CLIENT_SINGLEP_FLAG present -- shutting down"; 
    sleep 5
    break
  fi

  if [ $(( $(date +%s) - start )) -ge "$CLIENT_RUN_TIMEOUT" ]; then
    echo "game exceeded ${CLIENT_RUN_TIMEOUT}s -- closing it"
    break
  fi

  if [ -n "$(ls -A "$CLIENT_MC_DIR/crash-reports" 2>/dev/null)" ]; then
    echo "client crash report found but game is still running -- ending early"
    break
  fi
  sleep 1
done

# 5. if still up, close nicely, then escalate
if kill -0 -- "-$GAME_PGID" 2>/dev/null; then
  if close_window_nicely; then
    echo "asked window to close; waiting up to ${CLIENT_GRACE_TIMEOUT}s for save & exit"
  else
    echo "could not send a nice close -- signalling instead"
  fi
  for _ in $(seq 1 $((CLIENT_GRACE_TIMEOUT * 2))); do
    kill -0 -- "-$GAME_PGID" 2>/dev/null || break
    sleep 0.5
  done
  if kill -0 -- "-$GAME_PGID" 2>/dev/null; then
    # game ignored the nice close; record that the exit code is ours to own
    : > "$CLIENT_KILLED_FLAG"
    kill -TERM -- "-$GAME_PGID" 2>/dev/null
    for _ in $(seq 1 20); do
      kill -0 -- "-$GAME_PGID" 2>/dev/null || break
      sleep 0.5
    done
  fi
  kill -KILL -- "-$GAME_PGID" 2>/dev/null
fi
echo "game closed"

# 6. finish the recording while the screen still exists, then tear it down
stop_ffmpeg
kill -TERM "$XVFB_PID" 2>/dev/null
for _ in $(seq 1 10); do
  kill -0 "$XVFB_PID" 2>/dev/null || break
  sleep 0.5
done
kill -KILL "$XVFB_PID" 2>/dev/null
[ -n "$TAIL_PID" ] && kill "$TAIL_PID" 2>/dev/null
trap - INT TERM

# If the game had to be killed outright, the wrapper never recorded a code - 
# leave a non-zero code so a later verification sees the forced shutdown
[ -e "$CLIENT_EXIT_FLAG" ] || echo 137 > "$CLIENT_EXIT_FLAG"

echo "client run done -- video at $CLIENT_VIDEO"