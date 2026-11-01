#!/usr/bin/env bash
# Runs one agent-to-agent call end to end and plays the recording.
# Usage: scripts/demo.sh [v1|v2]
set -euo pipefail
cd "$(dirname "$0")/.."

VERSION="${1:-v2}"

SIMULATION=$(uv run sims run --start-agents --version "$VERSION" | tee /dev/stderr | grep -o 'started simulation [0-9a-f]*' | awk '{print $3}')

echo
uv run sims show "$SIMULATION"

# VS Code's audio preview can't play Opus, so keep a WAV copy next to the recording.
RECORDING="evidence/$SIMULATION/audio.ogg"
if [ -f "$RECORDING" ]; then
  ffmpeg -loglevel error -y -i "$RECORDING" "${RECORDING%.ogg}.wav"
  ffplay -autoexit -nodisp -loglevel error "${RECORDING%.ogg}.wav"
fi
