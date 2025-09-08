# Tidbyt Integration Setup Guide

This guide explains how to set up and use the Tidbyt integration with your Tilt Hydrometer Reader.

## Overview

The Tidbyt integration allows you to display real-time Tilt hydrometer data on your Tidbyt Gen 1 device, showing:
- Current specific gravity with trend indicator
- Temperature in Fahrenheit 
- Device color and timestamp
- Status indicators

## Prerequisites

1. **Tidbyt Device**: You need a Tidbyt Gen 1 device
2. **Tidbyt Mobile App**: Installed and set up with your device
3. **Tidbyt Developer Account**: Sign up at https://tidbyt.dev
4. **Python Dependencies**: Install the additional requirements

## Installation

### 1. Install Dependencies

Due to Python environment management on modern systems, we recommend using a virtual environment:

```bash
# Create virtual environment
python3 -m venv tidbyt-env

# Activate virtual environment
source tidbyt-env/bin/activate

# Install base dependencies
pip install -r requirements.txt

# Install Tidbyt-specific dependencies
pip install -r requirements-tidbyt.txt
```

**Alternative (not recommended):** If you prefer system-wide installation:
```bash
pip install -r requirements-tidbyt.txt --break-system-packages
```

### 2. Get Tidbyt Credentials

You need three pieces of information:

#### Device ID
1. Open the Tidbyt mobile app
2. Go to Settings → General → Device ID
3. Copy the Device ID (looks like: `device_12345`)

#### API Key  
1. Visit https://tidbyt.dev
2. Sign up or log in
3. Go to API Keys section
4. Create a new API key
5. Copy the API key (starts with `tidbyt_`)

#### Installation ID
This will be auto-generated during configuration, or you can create your own unique identifier.

### 3. Configure Integration

Run the Tilt monitor with Tidbyt support:

```bash
# If using virtual environment
source tidbyt-env/bin/activate
python tilt_monitor.py --tidbyt

# Or with system Python (requires root for Bluetooth)
sudo python tilt_monitor.py --tidbyt
```

During monitoring, press `c` to enter configuration, then select the Tidbyt option to set up:
1. Device ID
2. API Key  
3. Installation ID (auto-generated if left blank)
4. Push interval (how often to update the display)

## Usage

### Basic Usage

Start the monitor with Tidbyt integration:

```bash
# Easy way: Use the provided launch script
sudo ./run_with_tidbyt.sh

# Or manually with virtual environment
source tidbyt-env/bin/activate
sudo python tilt_monitor.py --tidbyt

# Or with system Python
sudo python tilt_monitor.py --tidbyt
```

The monitor will:
- Display Tilt data in the terminal as usual
- Push updates to your Tidbyt device every 5 minutes (default)
- Show Tidbyt status in the bottom status bar

### Configuration Options

Press `c` during monitoring to access configuration:

1. **Change API Key**: Update your Tidbyt API credentials
2. **Change Upload Interval**: Adjust how often data is pushed
3. **Calibrate Devices**: Standard Tilt calibration (same as non-Tidbyt mode)
4. **Tidbyt Integration**: Configure Tidbyt-specific settings
5. **Disable BrewStat.us**: Disable cloud logging
6. **Return to monitor**: Go back to monitoring

### Tidbyt Display Layout

The Tidbyt shows a 64x32 pixel display with:

```
RED TILT        14:30
 
SG 1.045 ↗
72.1°F
________________________
```

- **Top Line**: Device color and current time
- **Main Display**: Specific gravity with trend arrow
- **Bottom**: Temperature in Fahrenheit
- **Status Bar**: Color-coded bar at bottom

## Pixlet App (Alternative Method)

For advanced users, you can also use the included Pixlet app:

### 1. Start API Server

Run the API server to provide data to the Pixlet app:

```bash
python tilt_api_server.py
```

This starts a local HTTP server at `http://localhost:8000` with endpoints:
- `GET /` - Status and available devices
- `GET /api/tilt/{color}` - Data for specific device (e.g., `/api/tilt/red`)

### 2. Use Pixlet App

Install Pixlet and use the included `tilt.star` app:

```bash
# Install Pixlet (requires Go)
go install tidbyt.dev/pixlet@latest

# Render the app
pixlet render tilt.star

# Push to device
pixlet push <device-id> tilt.webp
```

## Troubleshooting

### Common Issues

**"Tidbyt integration not available"**
- Install dependencies: `pip install -r requirements-tidbyt.txt`
- Make sure PIL (Pillow) is installed for image generation

**"Token is not active" (401 error)**
- Check your API key is correct and active at https://tidbyt.dev
- Ensure the API key hasn't expired
- Verify the device ID matches your actual Tidbyt device

**No data appearing on Tidbyt**
- Check that your Tilt device is detected and online
- Verify push interval isn't too short (minimum 1 minute recommended)
- Check network connectivity

**Display looks wrong**
- The integration generates 64x32 pixel WebP images
- If fonts look wrong, it may fall back to basic text rendering

### Debug Mode

You can test the integration without a real Tidbyt:

```bash
python test_tidbyt.py
```

This runs all integration tests and generates a sample image.

### Manual Configuration

You can manually edit `tilt_config.json` to add Tidbyt settings:

```json
{
  "brewstat_api_key": "your_key",
  "tidbyt": {
    "device_id": "device_12345",
    "api_key": "tidbyt_abcd1234",
    "installation_id": "tilt-hydrometer",
    "enabled": true,
    "push_interval_seconds": 300
  }
}
```

## Advanced Configuration

### Custom Display Settings

Edit `tidbyt_integration.py` to customize:
- Colors for different Tilt devices
- Display layout and fonts
- Trend calculation sensitivity
- Image generation parameters

### Multiple Tilt Devices

The integration can handle multiple Tilt devices, but will push data for the most recently updated device. To display multiple devices, you can:

1. Configure multiple installation IDs
2. Run multiple instances with different Tilt colors
3. Modify the Pixlet app to cycle through devices

### API Server Integration

The included API server (`tilt_api_server.py`) can be used independently:

```bash
# Start server on different port
python -c "
from tilt_api_server import TiltAPIServer
server = TiltAPIServer('0.0.0.0', 8080)
server.start()
input('Press Enter to stop...')
server.stop()
"
```

## Support

For issues specific to:
- **Tilt devices**: Check the main README.md
- **Tidbyt hardware**: Visit https://tidbyt.com/support
- **Pixlet development**: See https://tidbyt.dev/docs
- **This integration**: Open an issue on the GitHub repository

## Files Created

The Tidbyt integration adds these files:
- `tidbyt_integration.py` - Main integration module
- `requirements-tidbyt.txt` - Additional dependencies
- `tilt.star` - Pixlet app for advanced usage
- `tilt_api_server.py` - HTTP API server
- `test_tidbyt.py` - Test suite
- `TIDBYT_SETUP.md` - This documentation

Your existing `tilt_config.json` is extended with Tidbyt settings when configured.