#!/usr/bin/env bash
# Runs one agent-to-agent call end to end and plays the recording.
# Usage: scripts/demo.sh [v1|v2]
set -euo pipefail
cd "$(dirname "$0")/.."

VERSION="${1:-v2}"
mkdir -p logs

uv run python -m agents.booking.server dev > logs/booking.log 2>&1 &
BOOKING_PID=$!
uv run python -m agents.caller.server dev > logs/caller.log 2>&1 &
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

SIMULATION=$(uv run python -m simulations.cli run --version "$VERSION" | tee /dev/stderr | grep -o 'started simulation [0-9a-f]*' | awk '{print $3}')

stop_servers

echo
uv run python -m simulations.cli show "$SIMULATION"

# VS Code's audio preview can't play Opus, so keep a WAV copy next to the recording.
RECORDING="evidence/$SIMULATION/audio.ogg"
if [ -f "$RECORDING" ]; then
  ffmpeg -loglevel error -y -i "$RECORDING" "${RECORDING%.ogg}.wav"
  ffplay -autoexit -nodisp -loglevel error "${RECORDING%.ogg}.wav"
fi
