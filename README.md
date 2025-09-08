# Tilt Hydrometer Bluetooth Reader

## Project Goals

This project aims to create a standalone Bluetooth data reader for the Tilt hydrometer that runs on Raspberry Pi 5, completely independent of Tilt's official software.

### Primary Objectives

1. **Direct Bluetooth Communication**: Establish direct Bluetooth Low Energy (BLE) connection with Tilt hydrometer
2. **Real-time Data Reading**: Continuously read gravity and temperature measurements
3. **Independent Logging**: Store data locally without relying on Tilt's cloud services or software
4. **Raspberry Pi 5 Compatibility**: Optimized for Raspberry Pi 5 hardware
5. **Data Display**: Simple interface to view current and historical readings

### Key Features

- [x] Bluetooth LE scanning and connection to Tilt devices
- [x] Parse gravity (specific gravity) and temperature data
- [x] Local data storage (CSV/JSON format)
- [x] Terminal-based ASCII art display interface
- [x] BrewStat.us cloud logging integration
- [x] Support for multiple Tilt colors/devices
- [x] Device calibration system
- [x] Real-time monitoring with instant keyboard controls

### Technical Requirements

- **Platform**: Raspberry Pi 5 with Bluetooth LE support
- **Programming Language**: Python (preferred for Raspberry Pi ecosystem)
- **Dependencies**: Bluetooth LE libraries, data storage, terminal UI libraries (curses/rich)
- **No External Services**: Complete offline operation

## Research Notes

### Tilt Hydrometer Technical Details

#### iBeacon Protocol Specifications
- **Communication Method**: Bluetooth Low Energy (BLE) using iBeacon advertising packets
- **Data Broadcasting**: Broadcasts every 5 seconds without requiring connection
- **Data Format**: 27-octet iBeacon manufacturer-specific data structure
- **Manufacturer ID**: Apple (4C 00)

#### Data Encoding Format
```
iBeacon Structure:
- FF: Manufacturer specific data type
- 4C 00: Apple manufacturer ID  
- 02: iBeacon type (constant)
- 15: Data length (constant)
- UUID: 16-byte device identifier (color-specific)
- Major: 16-bit temperature (°F, big-endian)
- Minor: 16-bit gravity (*1000, big-endian)  
- TX Power: 8-bit signal power (dBm)
```

#### Color-Coded Device UUIDs
Each Tilt color has a unique UUID:
- **Red**: A495BB10C5B14B44B5121370F02D74DE
- **Green**: A495BB20C5B14B44B5121370F02D74DE
- **Black**: A495BB30C5B14B44B5121370F02D74DE
- **Purple**: A495BB40C5B14B44B5121370F02D74DE
- **Orange**: A495BB50C5B14B44B5121370F02D74DE
- **Blue**: A495BB60C5B14B44B5121370F02D74DE
- **Yellow**: A495BB70C5B14B44B5121370F02D74DE
- **Pink**: A495BB80C5B14B44B5121370F02D74DE

#### Data Parsing Algorithm
```python
# Temperature (Major field) - degrees Fahrenheit
temperature = (data[20] << 8) | data[21]

# Specific Gravity (Minor field) - divide by 1000
gravity = ((data[22] << 8) | data[23]) / 1000.0
```

#### Device Specifications
- **Gravity Range**: 0.990 to 1.120 SG
- **Gravity Accuracy**: ±0.002 SG
- **Temperature Accuracy**: ±1°F (±0.5°C)
- **Resolution**: 0.001 SG increments, 1°F increments
- **Update Rate**: Every 5 seconds

### Implementation Approach

#### Recommended Python Libraries

1. **aioblescan** (Primary Choice)
   - Async Python library specifically designed for BLE beacon scanning
   - Proven compatibility with Tilt hydrometers
   - Can decode iBeacon data automatically
   - Good Raspberry Pi support

2. **bleak** (Alternative)  
   - Cross-platform BLE library
   - **Caution**: Known issues with Raspberry Pi 5
   - Requires enabling experimental BlueZ features
   - May need passive scanning mode

#### Raspberry Pi 5 Configuration Requirements
```bash
# Enable experimental BlueZ features
echo "Experimental = true" >> /etc/bluetooth/main.conf
sudo systemctl restart bluetooth
```

#### Architecture Design
```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Tilt Device   │───▶│  BLE Scanner     │───▶│  Data Parser    │
│   (iBeacon)     │    │  (aioblescan)    │    │  (UUID+Data)    │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                                         │
┌─────────────────┐    ┌──────────────────┐             ▼
│ Terminal ASCII  │◄───│  Data Storage    │◄────────────┐
│   Interface     │    │  (CSV/JSON)      │             │
└─────────────────┘    └──────────────────┘             │
                                │                       │
                                ▼                       │
                       ┌──────────────────┐             │
                       │  BrewStat.us     │◄────────────┘
                       │  Cloud Logger    │
                       └──────────────────┘
```

#### Development Phases
1. **Phase 1**: Basic BLE scanning and iBeacon detection
2. **Phase 2**: Tilt-specific data parsing and validation  
3. **Phase 3**: Data logging and storage implementation
4. **Phase 4**: Terminal ASCII art interface with real-time display
5. **Phase 5**: BrewStat.us API integration for cloud logging
6. **Phase 6**: Multi-device support and data export

#### Potential Challenges
- **Raspberry Pi 5 BLE Stack**: Known compatibility issues with some libraries
- **WiFi Interference**: 2.4GHz WiFi may interfere with BLE on Pi 5
- **BlueZ Limitations**: May require experimental features enabled
- **Permission Requirements**: BLE scanning typically requires root privileges

### BrewStat.us Cloud Integration

#### API Endpoint
- **URL Format**: `https://www.brewstat.us/tilt/{API_KEY}/log`
- **Method**: POST (assumed based on standard cloud logging practices)
- **Example**: `https://www.brewstat.us/tilt/XXXXXX/log`

#### Data Format Requirements
Based on research of similar services, the expected payload likely includes:
```json
{
  "timestamp": "2025-01-07T12:00:00Z",
  "temperature": 68.5,
  "gravity": 1.045,
  "color": "RED",
  "device_id": "A495BB10C5B14B44B5121370F02D74DE"
}
```

#### Integration Features
- **Automatic Upload**: Send data every 15 minutes (standard Tilt cloud interval)
- **Offline Buffering**: Queue data when network unavailable
- **Error Handling**: Retry failed uploads with exponential backoff
- **Configuration**: User-provided API key from BrewStat.us account

#### Terminal Interface Design
```
╔══════════════════════════════════════════════════════════════════════════════════════╗
║                          🍺 TILT HYDROMETER MONITOR 🍺                              ║
╠══════════════════════════════════════════════════════════════════════════════════════╣
║                                                                                      ║
║  Device: RED TILT                    Status: ●CONNECTED                             ║
║  Last Update: 2025-01-07 12:34:56    Signal: -65 dBm                               ║
║                                                                                      ║
║  ┌─────────────────────────────────┐  ┌─────────────────────────────────────────┐   ║
║  │        TEMPERATURE              │  │          SPECIFIC GRAVITY               │   ║
║  │                                 │  │                                         │   ║
║  │           68.5°F                │  │             1.045                       │   ║
║  │         (20.3°C)                │  │                                         │   ║
║  │                                 │  │   ████████████░░░░░                     │   ║
║  │    ████████████████░░            │  │   Progress: ██████░░ 75%               │   ║
║  │    Min: 65°F  Max: 72°F         │  │   Start: 1.060  Target: 1.010          │   ║
║  └─────────────────────────────────┘  └─────────────────────────────────────────┘   ║
║                                                                                      ║
║  ┌─────────────────────────────────────────────────────────────────────────────┐   ║
║  │                       TEMPERATURE HISTORY (14 days)                         │   ║
║  │ 72°F│                                                              █        │   ║
║  │ 70°F│  █                                                          █ █       │   ║
║  │ 68°F│  █ █      █                                               █ █ █ █     │   ║
║  │ 66°F│  █ █ █    █ █                                          █ █ █ █ █ █    │   ║
║  │ 64°F│  █ █ █ █ █ █ █ █ █ █ █ █ █ █ █ █ █ █ █ █ █ █ █ █ █ █ █ █ █ █ █ █    │   ║
║  │     └─────────────────────────────────────────────────────────────────────  │   ║
║  │     Day: 1  2  3  4  5  6  7  8  9 10 11 12 13 14        (15min intervals) │   ║
║  └─────────────────────────────────────────────────────────────────────────────┘   ║
║                                                                                      ║
║  ┌─────────────────────────────────────────────────────────────────────────────┐   ║
║  │                        GRAVITY HISTORY (14 days)                            │   ║
║  │1.060│█                                                                      │   ║
║  │1.055│█ █                                                                    │   ║
║  │1.050│█ █ █                                                                  │   ║
║  │1.045│█ █ █ █                                                               │   ║
║  │1.040│█ █ █ █ █                                                             │   ║
║  │1.035│█ █ █ █ █ █ █ █ █ █ █ █ █ █ █ █ █ █ █ █ █ █ █ █ █ █ █ █ █ █ █ █       │   ║
║  │     └─────────────────────────────────────────────────────────────────────  │   ║
║  │     Day: 1  2  3  4  5  6  7  8  9 10 11 12 13 14        (15min intervals) │   ║
║  └─────────────────────────────────────────────────────────────────────────────┘   ║
║                                                                                      ║
║  Cloud Status: BrewStat.us ●CONNECTED    Last Upload: 12:30:01                     ║
║  Local Log: 1,247 readings               Storage: data/tilt_log_2025-01-07.csv     ║
║                                                                                      ║
║  Recent Activity:                                                                   ║
║  12:34:56  68.5°F  1.045  Steady fermentation                                      ║
║  12:29:56  68.4°F  1.046  Temperature rising                                       ║
║  12:24:56  68.2°F  1.047  Gravity dropping                                         ║
║                                                                                      ║
║  Press 'q' to quit | 'r' to reset | 's' to save | 'c' to configure                ║
╚══════════════════════════════════════════════════════════════════════════════════════╝

Color Scheme:
- All text: GREEN
- Section headings (TEMPERATURE, GRAVITY, etc.): WHITE & BOLD  
- Bar charts: YELLOW (normal range) / RED (out of range)
- Status indicators: GREEN (●CONNECTED) / RED (●DISCONNECTED)
```

## Current Implementation

### Core Applications

1. **tilt_monitor.py** - Complete terminal ASCII interface monitor
   - Real-time display with large ASCII numbers for gravity and temperature
   - Side-by-side history charts for temperature and gravity trends  
   - Instant keyboard controls (q=quit, c=configure, h=help)
   - Built-in interactive calibration system for temperature and gravity
   - BrewStat.us cloud logging with configurable upload intervals
   - Multi-device support for all 8 Tilt colors
   - Automatic data logging to CSV files

2. **tilt_scanner.py** - Core Bluetooth scanning engine
   - iBeacon protocol implementation for Tilt detection
   - Multi-device scanning and data parsing
   - Calibration system with offset corrections
   - Real-time RSSI signal strength monitoring

3. **calibrate_tilt.py** - Device calibration utility
   - Interactive calibration process
   - Temperature and gravity offset corrections
   - Persistent calibration storage

### Usage

```bash
# Install dependencies
pip install -r requirements.txt

# Run main monitor (requires root for Bluetooth)
sudo python3 tilt_monitor.py

# Calibrate devices
sudo python3 calibrate_tilt.py
```

### Interface Features

- **Large ASCII Art Numbers**: 7-row high display with perfect mathematical centering
- **Symmetric Layout**: Identical 33-character wide boxes for gravity and temperature
- **Real-time Updates**: 3-second refresh cycle
- **Aligned History Charts**: Gravity and temperature charts positioned below their corresponding big numbers
- **Signal Monitoring**: RSSI strength and last update timestamps  
- **Built-in Calibration**: Interactive temperature and gravity calibration system
- **Cloud Integration**: Automatic BrewStat.us uploads every 15 minutes
- **Configuration Screen**: Interactive setup for API keys, upload intervals, and device calibration
- **Instant Controls**: No Enter key required for q/c/h commands

## Project Status

- [x] Project initialization and research
- [x] Bluetooth protocol implementation (iBeacon/BLE)
- [x] Library evaluation and aioblescan integration
- [x] Complete terminal ASCII interface development
- [x] Multi-device support and calibration system
- [x] BrewStat.us cloud logging integration
- [x] Data storage and history tracking
- [x] Real-time monitoring with instant controls