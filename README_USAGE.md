# Tilt Hydrometer Monitor Usage Guide

## Setup

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Run with root privileges** (required for Bluetooth access):
   ```bash
   sudo python3 tilt_monitor.py
   ```

## Main Monitor Application

### Terminal ASCII Interface
The main monitor (`tilt_monitor.py`) provides a complete real-time ASCII interface:

```bash
sudo python3 tilt_monitor.py
```

**Features:**
- Large 7-row ASCII numbers for gravity and temperature
- Side-by-side history charts (24-hour trends)
- Real-time updates every 3 seconds
- Instant keyboard controls (no Enter key required)
- BrewStat.us cloud logging integration
- Multi-device support for all Tilt colors

### Keyboard Controls
- **q** - Quit the monitor
- **c** - Open configuration screen for BrewStat.us settings
- **h** - Show help menu
- **Ctrl+C** - Emergency quit

### Configuration Screen
Press 'c' to access the interactive configuration menu:
1. **Change API Key** - Set your BrewStat.us API key
2. **Change Upload Interval** - Adjust cloud upload frequency (1-60 minutes)
3. **Disable BrewStat.us** - Turn off cloud logging
4. **Return to monitor** - Go back to main display

### Calibration Process

1. **Prepare calibration setup:**
   - Fill container with clean water (gravity = 1.000)
   - Measure water temperature with accurate thermometer
   - Place Tilt in water, let stabilize 2-3 minutes

2. **Run calibration tool:**
   ```bash
   sudo ./venv/bin/python calibrate_tilt.py
   ```

3. **Interactive calibration:**
   - Select Tilt color to calibrate
   - Enter actual water temperature
   - Tool automatically calculates offsets
   - Save calibration when done

## Multi-Device Support

The scanner automatically detects all Tilt colors:
- RED, GREEN, BLACK, PURPLE, ORANGE, BLUE, YELLOW, PINK
- Each device maintains separate calibration offsets
- Readings are color-coded in output

## Calibration File

Calibration data is stored in `tilt_calibration.json`:
```json
{
  "RED": {
    "temp_offset": -2.5,
    "gravity_offset": 0.002
  },
  "GREEN": {
    "temp_offset": 1.0,
    "gravity_offset": -0.001
  }
}
```

## Troubleshooting

**Permission denied errors:**
- Always run with `sudo` for Bluetooth access
- Ensure user is in `bluetooth` group

**No devices found:**
- Check Tilt is powered on and floating
- Verify Bluetooth is enabled: `sudo systemctl status bluetooth`
- Tilt must be within range (~30 feet)

**Inaccurate readings:**
- Perform calibration with known reference
- Use clean water at room temperature for best results
- Let Tilt stabilize before taking readings

## Display Layout

The monitor displays:

```
[ONLINE] RED TILT - 14:35:22
----------------------------------------------------------------------

GRAVITY                    TEMPERATURE

████  ███ █    ███             ███  ███  ███
█  █ █     █   █           █  █   █   █ █   █
█  █ █     █   █           █  █   █   █ █   █
████ ████  █   ████        █  █   █   █ █   █
   █    █  █      █        █  █   █   █ █   █  
   █    █  █      █        █  █   █   █ █   █
███  ███   █   ███         █   ███   ███  ███

(1.012 SG)               (72.0°F / 22.2°C)

Signal: -65dBm | Last Update: 14:35:19

HISTORY:
TEMP (24h): Current trend charts...
GRAV (24h): Current trend charts...
```

**Data Display:**
- **Large ASCII Numbers:** 7-row high display for easy reading from distance
- **Device Status:** Online/Offline indicator with timestamp
- **Signal Strength:** RSSI value showing connection quality
- **History Charts:** Visual 24-hour trends for temperature and gravity
- **Calibrated Values:** All readings include calibration offsets