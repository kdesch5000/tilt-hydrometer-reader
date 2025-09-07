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

- [ ] Bluetooth LE scanning and connection to Tilt devices
- [ ] Parse gravity (specific gravity) and temperature data
- [ ] Local data storage (CSV/JSON format)
- [ ] Terminal-based ASCII art display interface
- [ ] BrewStat.us cloud logging integration
- [ ] Support for multiple Tilt colors/devices
- [ ] Data export capabilities

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
- **Example**: `https://www.brewstat.us/tilt/YkgjKDB3pV/log`

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

## Project Status

- [x] Project initialization
- [ ] Bluetooth protocol research
- [ ] Library evaluation
- [ ] Prototype development
- [ ] Testing and validation