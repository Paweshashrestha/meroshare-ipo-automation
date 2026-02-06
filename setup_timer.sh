#!/bin/bash

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SYSTEMD_DIR="/etc/systemd/system"

echo "Setting up IPO check timer (runs daily at 10:00 Nepal time)..."

for f in ipo-check.service ipo-check.timer; do
    if [ ! -f "$SCRIPT_DIR/systemd/$f" ]; then
        echo "Error: $f not found"
        exit 1
    fi
done

sudo cp "$SCRIPT_DIR/systemd/ipo-check.service" "$SYSTEMD_DIR/"
sudo cp "$SCRIPT_DIR/systemd/ipo-check.timer" "$SYSTEMD_DIR/"
sudo systemctl daemon-reload
sudo systemctl enable --now ipo-check.timer

echo ""
echo "Timer enabled. IPO check will run daily at 10:00 (system local time)."
echo "Set timezone to Nepal: sudo timedatectl set-timezone Asia/Kathmandu"
echo ""
echo "Commands:"
echo "  Status:  sudo systemctl status ipo-check.timer"
echo "  Logs:    sudo journalctl -u ipo-check.service"
echo "  Disable: sudo systemctl disable --now ipo-check.timer"
echo ""
