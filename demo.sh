#!/usr/bin/env bash
# Runs one agent-to-agent call end to end and plays the recording.
# Usage: ./demo.sh [v1|v2]
set -euo pipefail
cd "$(dirname "$0")"

VERSION="${1:-v2}"
mkdir -p logs

uv run python -m booking.server dev > logs/booking.log 2>&1 &
BOOKING_PID=$!
uv run python -m caller.server dev > logs/caller.log 2>&1 &
CALLER_PID=$!
stop_servers() {
  pkill -P "$BOOKING_PID" 2>/dev/null || true
  pkill -P "$CALLER_PID" 2>/dev/null || true
  kill "$BOOKING_PID" "$CALLER_PID" 2>/dev/null || true
}
trap stop_servers EXIT

until grep -q "registered worker" logs/booking.log && grep -q "registered worker" logs/caller.log; do
  sleep 1
done

ROOM=$(uv run call.py --version "$VERSION" | tee /dev/stderr | grep -o 'call-[0-9a-f]*' | head -1)

OPUS_RECORDING="recordings/$ROOM.ogg"
for _ in $(seq 1 20); do
  [ -f "$OPUS_RECORDING" ] && break
  sleep 1
done
# VS Code's audio preview can't play Opus, so keep a WAV copy instead.
RECORDING="recordings/$ROOM.wav"
ffmpeg -loglevel error -y -i "$OPUS_RECORDING" "$RECORDING" && rm "$OPUS_RECORDING"

stop_servers

echo
grep -h " call - " logs/booking.log logs/caller.log | grep "$ROOM" \
  | sed -E 's/\x1b\[[0-9;]*m//g; s/^[0-9-]+ ([0-9:,]+) .* call - /\1  /; s/ \{"pid.*$//' | sort | cut -c1-200

echo
echo "Recording: $RECORDING"
ffplay -autoexit -nodisp -loglevel error "$RECORDING"
