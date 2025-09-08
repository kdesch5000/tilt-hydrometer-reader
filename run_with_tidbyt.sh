#!/bin/bash
# Tilt Monitor with Tidbyt Integration Launcher
# This script activates the virtual environment and runs the monitor with Tidbyt support

set -e

echo "🍺 Tilt Hydrometer Monitor with Tidbyt Integration"
echo "=================================================="

# Check if virtual environment exists
if [ ! -d "tidbyt-env" ]; then
    echo "❌ Virtual environment not found!"
    echo "Please run setup first:"
    echo "  python3 -m venv tidbyt-env"
    echo "  source tidbyt-env/bin/activate"
    echo "  pip install -r requirements.txt"
    echo "  pip install -r requirements-tidbyt.txt"
    exit 1
fi

# Check if we need root privileges for Bluetooth
if [ "$EUID" -ne 0 ]; then
    echo "⚠️  Warning: Running without root privileges"
    echo "   Bluetooth scanning may not work properly"
    echo "   Consider running: sudo ./run_with_tidbyt.sh"
    echo ""
fi

# Activate virtual environment and run
echo "🚀 Activating virtual environment and starting monitor..."
echo "   Press Ctrl+C to exit"
echo "   Press 'c' in monitor to configure Tidbyt settings"
echo ""

source tidbyt-env/bin/activate
python tilt_monitor.py --tidbyt