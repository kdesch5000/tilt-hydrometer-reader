#!/usr/bin/env python3
"""
Tilt Hydrometer Scanner
Reads data from multiple Tilt hydrometers via Bluetooth LE iBeacon protocol
Supports calibration for improved accuracy
"""

import asyncio
import json
import struct
import time
from datetime import datetime
from typing import Dict, Optional, Tuple
import aioblescan as aiobs

# Tilt Hydrometer UUID mappings for each color
TILT_UUIDS = {
    'A495BB10C5B14B44B5121370F02D74DE': 'RED',
    'A495BB20C5B14B44B5121370F02D74DE': 'GREEN', 
    'A495BB30C5B14B44B5121370F02D74DE': 'BLACK',
    'A495BB40C5B14B44B5121370F02D74DE': 'PURPLE',
    'A495BB50C5B14B44B5121370F02D74DE': 'ORANGE',
    'A495BB60C5B14B44B5121370F02D74DE': 'BLUE',
    'A495BB70C5B14B44B5121370F02D74DE': 'YELLOW',
    'A495BB80C5B14B44B5121370F02D74DE': 'PINK'
}

class TiltDevice:
    """Represents a single Tilt hydrometer device"""
    
    def __init__(self, color: str, uuid: str):
        self.color = color
        self.uuid = uuid
        self.temperature_f = 0.0
        self.specific_gravity = 0.0
        self.rssi = 0
        self.last_seen = None
        
        # Calibration offsets
        self.temp_offset = 0.0
        self.gravity_offset = 0.0
        
    def update_reading(self, temp_f: float, gravity: float, rssi: int):
        """Update device readings with raw values"""
        self.temperature_f = temp_f
        self.specific_gravity = gravity
        self.rssi = rssi
        self.last_seen = datetime.now()
        
    def get_calibrated_temperature_f(self) -> float:
        """Get temperature in Fahrenheit with calibration applied"""
        return self.temperature_f + self.temp_offset
        
    def get_calibrated_temperature_c(self) -> float:
        """Get temperature in Celsius with calibration applied"""
        return (self.get_calibrated_temperature_f() - 32) * 5/9
        
    def get_calibrated_gravity(self) -> float:
        """Get specific gravity with calibration applied"""
        return self.specific_gravity + self.gravity_offset
        
    def calibrate(self, actual_temp_f: float, actual_gravity: float = 1.000):
        """Calibrate device using known reference values"""
        self.temp_offset = actual_temp_f - self.temperature_f
        self.gravity_offset = actual_gravity - self.specific_gravity
        print(f"[{self.color}] Calibrated - Temp offset: {self.temp_offset:+.1f}°F, Gravity offset: {self.gravity_offset:+.4f}")

class TiltScanner:
    """Main scanner class for detecting and reading Tilt hydrometers"""
    
    def __init__(self):
        self.devices: Dict[str, TiltDevice] = {}
        self.running = False
        
    def parse_ibeacon_data(self, data: bytes) -> Optional[Tuple[str, float, float, int]]:
        """Parse iBeacon advertisement data for Tilt information"""
        if len(data) < 25:
            return None
            
        # Check for iBeacon format (Apple manufacturer data)
        if data[0] != 0x4C or data[1] != 0x00 or data[2] != 0x02 or data[3] != 0x15:
            return None
            
        # Extract UUID (16 bytes starting at offset 4)
        uuid_bytes = data[4:20]
        uuid = uuid_bytes.hex().upper()
        
        # Check if this is a Tilt UUID
        if uuid not in TILT_UUIDS:
            return None
            
        # Extract major (temperature) and minor (gravity) values
        major = struct.unpack('>H', data[20:22])[0]  # Temperature in °F
        minor = struct.unpack('>H', data[22:24])[0]  # Gravity * 1000
        
        temperature_f = float(major)
        specific_gravity = float(minor) / 1000.0
        
        return uuid, temperature_f, specific_gravity, 0  # RSSI will be set separately
        
    def process_advertisement(self, data):
        """Process BLE advertisement data"""
        if hasattr(data, 'raw_data'):
            # Look for manufacturer specific data
            for ad_structure in data.raw_data:
                if hasattr(ad_structure, 'payload') and len(ad_structure.payload) >= 25:
                    result = self.parse_ibeacon_data(ad_structure.payload)
                    if result:
                        uuid, temp_f, gravity, _ = result
                        color = TILT_UUIDS[uuid]
                        
                        # Get or create device
                        if uuid not in self.devices:
                            self.devices[uuid] = TiltDevice(color, uuid)
                            print(f"[DISCOVERED] {color} Tilt detected (UUID: {uuid})")
                        
                        # Update device reading
                        rssi = getattr(data, 'rssi', 0)
                        self.devices[uuid].update_reading(temp_f, gravity, rssi)
                        
                        # Print reading
                        device = self.devices[uuid]
                        print(f"[{color}] Raw: {temp_f:.1f}°F, {gravity:.3f} SG | "
                              f"Calibrated: {device.get_calibrated_temperature_f():.1f}°F "
                              f"({device.get_calibrated_temperature_c():.1f}°C), "
                              f"{device.get_calibrated_gravity():.3f} SG | "
                              f"RSSI: {rssi} dBm")
                        
    async def scan(self, duration: int = 30):
        """Scan for Tilt devices for specified duration"""
        print(f"Starting Tilt scan for {duration} seconds...")
        print("Looking for Tilt hydrometers...")
        
        # Create BLE scanner
        scanner = aiobs.BLEScanRequester()
        scanner.set_callback(self.process_advertisement)
        
        # Start scanning
        self.running = True
        await scanner.start()
        
        try:
            # Scan for specified duration
            await asyncio.sleep(duration)
        finally:
            await scanner.stop()
            self.running = False
            
        print(f"\nScan completed. Found {len(self.devices)} Tilt device(s).")
        
    def list_devices(self):
        """List all discovered devices"""
        if not self.devices:
            print("No Tilt devices found.")
            return
            
        print("\nDiscovered Tilt Devices:")
        print("-" * 80)
        for uuid, device in self.devices.items():
            last_seen = device.last_seen.strftime("%H:%M:%S") if device.last_seen else "Never"
            print(f"{device.color:8} | {device.get_calibrated_temperature_f():6.1f}°F "
                  f"({device.get_calibrated_temperature_c():5.1f}°C) | "
                  f"{device.get_calibrated_gravity():.3f} SG | "
                  f"{device.rssi:4d} dBm | {last_seen}")
                  
    def calibrate_device(self, color: str, actual_temp_f: float, actual_gravity: float = 1.000):
        """Calibrate a specific device by color"""
        device = None
        for d in self.devices.values():
            if d.color.upper() == color.upper():
                device = d
                break
                
        if device:
            device.calibrate(actual_temp_f, actual_gravity)
        else:
            print(f"Device {color} not found or not detected yet.")
            
    def save_calibration(self, filename: str = "tilt_calibration.json"):
        """Save calibration data to file"""
        calibration_data = {}
        for uuid, device in self.devices.items():
            calibration_data[device.color] = {
                'temp_offset': device.temp_offset,
                'gravity_offset': device.gravity_offset
            }
            
        with open(filename, 'w') as f:
            json.dump(calibration_data, f, indent=2)
        print(f"Calibration saved to {filename}")
        
    def load_calibration(self, filename: str = "tilt_calibration.json"):
        """Load calibration data from file"""
        try:
            with open(filename, 'r') as f:
                calibration_data = json.load(f)
                
            for device in self.devices.values():
                if device.color in calibration_data:
                    cal = calibration_data[device.color]
                    device.temp_offset = cal.get('temp_offset', 0.0)
                    device.gravity_offset = cal.get('gravity_offset', 0.0)
                    print(f"[{device.color}] Loaded calibration - Temp: {device.temp_offset:+.1f}°F, Gravity: {device.gravity_offset:+.4f}")
                    
        except FileNotFoundError:
            print(f"Calibration file {filename} not found. Using default values.")
        except Exception as e:
            print(f"Error loading calibration: {e}")

async def main():
    """Main program function"""
    print("=" * 60)
    print("Tilt Hydrometer Scanner - Test Program")
    print("=" * 60)
    
    scanner = TiltScanner()
    
    # Load existing calibration
    scanner.load_calibration()
    
    # Scan for devices
    await scanner.scan(30)
    
    # Show results
    scanner.list_devices()
    
    # Example calibration (uncomment and modify for your needs)
    # print("\nTo calibrate, place Tilt in water with known temperature and gravity=1.000")
    # print("Then use: scanner.calibrate_device('RED', actual_temp_f, 1.000)")
    # scanner.calibrate_device('RED', 68.0, 1.000)  # Example: RED tilt, water at 68°F
    
    # Save calibration
    if scanner.devices:
        scanner.save_calibration()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nScan interrupted by user.")
    except Exception as e:
        print(f"Error: {e}")
        print("Note: This program requires root privileges to access Bluetooth.")
        print("Try running with: sudo python3 tilt_scanner.py")