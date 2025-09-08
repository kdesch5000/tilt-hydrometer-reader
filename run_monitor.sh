#!/bin/bash
# Tilt Monitor Launcher Script
# Runs the monitor with proper virtual environment and sudo privileges

cd "$(dirname "$0")"

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Virtual environment not found. Please run:"
    echo "python3 -m venv venv"
    echo "source venv/bin/activate"
    echo "pip install -r requirements.txt"
    exit 1
fi

# Check if running with sudo
if [ "$EUID" -ne 0 ]; then
    echo "This script requires sudo privileges for Bluetooth access."
    echo "Rerunning with sudo..."
    exec sudo "$0" "$@"
fi

# Run the monitor with virtual environment Python
exec ./venv/bin/python tilt_monitor.py