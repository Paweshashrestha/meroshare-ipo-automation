#!/bin/bash

# IPO Scheduler Setup Script
# This script sets up the systemd service for automatic IPO checking

echo "Setting up IPO Scheduler as systemd service..."

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVICE_FILE="$SCRIPT_DIR/systemd/ipo-scheduler.service"

# Check if service file exists
if [ ! -f "$SERVICE_FILE" ]; then
    echo "Error: Service file not found at $SERVICE_FILE"
    exit 1
fi

# Copy service file to systemd directory
echo "Copying service file to /etc/systemd/system/..."
sudo cp "$SERVICE_FILE" /etc/systemd/system/ipo-scheduler.service

# Reload systemd
echo "Reloading systemd daemon..."
sudo systemctl daemon-reload

# Enable service to start on boot
echo "Enabling service to start on boot..."
sudo systemctl enable ipo-scheduler.service

# Start the service
echo "Starting IPO scheduler service..."
sudo systemctl start ipo-scheduler.service

# Check status
echo ""
echo "Service status:"
sudo systemctl status ipo-scheduler.service --no-pager

echo ""
echo "=========================================="
echo "IPO Scheduler setup complete!"
echo "=========================================="
echo ""
echo "Useful commands:"
echo "  Check status:  sudo systemctl status ipo-scheduler"
echo "  View logs:      sudo journalctl -u ipo-scheduler -f"
echo "  Stop service:   sudo systemctl stop ipo-scheduler"
echo "  Start service:  sudo systemctl start ipo-scheduler"
echo "  Restart:        sudo systemctl restart ipo-scheduler"
echo ""

