# Tilt Scanner Usage Guide

## Setup

1. **Create virtual environment:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Run programs with root privileges** (required for Bluetooth access):
   ```bash
   sudo ./venv/bin/python tilt_scanner.py
   sudo ./venv/bin/python calibrate_tilt.py
   ```

## Basic Usage

### Scanning for Tilts
```bash
sudo ./venv/bin/python tilt_scanner.py
```
This will:
- Scan for 30 seconds
- Detect all Tilt colors automatically
- Show real-time readings
- Display calibrated values
- Save calibration data

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

## Output Format

```
[RED] Raw: 68.2°F, 1.045 SG | Calibrated: 68.7°F (20.4°C), 1.047 SG | RSSI: -65 dBm
```

- **Raw:** Direct readings from Tilt
- **Calibrated:** Adjusted readings with offsets applied  
- **RSSI:** Signal strength (closer to 0 = stronger signal)