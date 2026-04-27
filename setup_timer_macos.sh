#!/bin/bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLIST_DIR="$HOME/Library/LaunchAgents"
PLIST_PATH="$PLIST_DIR/com.meroshare.ipo-check.plist"
PYTHON_BIN="$SCRIPT_DIR/venv/bin/python"
RUN_SCRIPT="$SCRIPT_DIR/src/scheduler/run_once.py"
HOUR="${1:-11}"
MINUTE="${2:-11}"

if ! [[ "$HOUR" =~ ^([0-9]|1[0-9]|2[0-3])$ ]]; then
    echo "Error: hour must be 0-23 (got '$HOUR')"
    echo "Usage: ./setup_timer_macos.sh [hour] [minute]"
    exit 1
fi

if ! [[ "$MINUTE" =~ ^([0-9]|[1-5][0-9])$ ]]; then
    echo "Error: minute must be 0-59 (got '$MINUTE')"
    echo "Usage: ./setup_timer_macos.sh [hour] [minute]"
    exit 1
fi

echo "Setting up IPO check LaunchAgent (runs daily at $(printf "%02d:%02d" "$HOUR" "$MINUTE") local time)..."

if [[ ! -x "$PYTHON_BIN" ]]; then
    echo "Error: Python not found at $PYTHON_BIN"
    echo "Create your venv first: python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt"
    exit 1
fi

if [[ ! -f "$RUN_SCRIPT" ]]; then
    echo "Error: run script not found at $RUN_SCRIPT"
    exit 1
fi

mkdir -p "$PLIST_DIR"

cat > "$PLIST_PATH" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>com.meroshare.ipo-check</string>
  <key>ProgramArguments</key>
  <array>
    <string>$PYTHON_BIN</string>
    <string>$RUN_SCRIPT</string>
  </array>
  <key>WorkingDirectory</key>
  <string>$SCRIPT_DIR</string>
  <key>StartCalendarInterval</key>
  <dict>
    <key>Hour</key>
    <integer>$HOUR</integer>
    <key>Minute</key>
    <integer>$MINUTE</integer>
  </dict>
  <key>StandardOutPath</key>
  <string>$SCRIPT_DIR/logs/ipo-check.out.log</string>
  <key>StandardErrorPath</key>
  <string>$SCRIPT_DIR/logs/ipo-check.err.log</string>
</dict>
</plist>
EOF

mkdir -p "$SCRIPT_DIR/logs"

launchctl unload "$PLIST_PATH" >/dev/null 2>&1 || true
launchctl load "$PLIST_PATH"

echo ""
echo "LaunchAgent enabled. IPO check will run daily at $(printf "%02d:%02d" "$HOUR" "$MINUTE") local time."
echo "To run at 11:11 Nepal time, use ./setup_timer_macos.sh 11 11 and set macOS timezone to Asia/Kathmandu."
echo ""
echo "Commands:"
echo "  Status:  launchctl list | rg com.meroshare.ipo-check"
echo "  Logs:    tail -f \"$SCRIPT_DIR/logs/ipo-check.err.log\""
echo "  Disable: launchctl unload \"$PLIST_PATH\""
echo ""
