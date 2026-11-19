#!/bin/bash
# Double-click to preview the prototypes locally (macOS).
cd "$(dirname "$0")"
python3 tools/build.py
PORT=8765
( sleep 1; open "http://localhost:$PORT/" ) &
echo "Preview: http://localhost:$PORT/  (Ctrl+C to stop)"
python3 -m http.server "$PORT"
