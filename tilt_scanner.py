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
from aioblescan.plugins import Tilt

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
    
    def __init__(self, device_id=0, quiet=False):
        self.devices: Dict[str, TiltDevice] = {}
        self.running = False
        self.device_id = device_id
        self.tilt_decoder = Tilt()
        self.quiet = quiet
        self.calibration_data: Dict[str, Dict[str, float]] = {}  # Store calibration for future devices
        
    def process_data(self, data):
        """Process BLE advertisement data using aioblescan format"""
        # Decode HCI event
        ev = aiobs.HCI_Event()
        try:
            ev.decode(data)
        except:
            return
            
        # Try to decode with Tilt plugin
        result = self.tilt_decoder.decode(ev)
        if result:
            # Parse the result to extract information
            result_str = str(result)
            
            # Extract MAC address for device identification
            mac_addresses = ev.retrieve("peer")
            mac = mac_addresses[0].val if mac_addresses else "unknown"
            
            # Extract RSSI
            rssi_data = ev.retrieve("rssi")
            rssi = rssi_data[0].val if rssi_data else 0
            
            # Parse the Tilt result string to extract color, temp, and gravity
            # Expected format contains color, temperature, and gravity information
            self.parse_tilt_result(result_str, mac, rssi)
    
    def parse_tilt_result(self, result_str: str, mac: str, rssi: int):
        """Parse Tilt plugin JSON result"""
        try:
            # The Tilt plugin returns JSON data
            data = json.loads(result_str)
            
            # Extract values from JSON
            uuid = data.get("uuid", "")
            temp_f = float(data.get("major", 0))  # Temperature in °F
            gravity = float(data.get("minor", 0)) / 1000.0  # Gravity (divided by 1000)
            rssi_val = data.get("rssi", rssi)
            mac_addr = data.get("mac", mac)
            
            # Determine color from UUID
            # The UUID might have A495 duplicated, let's clean it up
            clean_uuid = uuid.upper()
            
            # If UUID starts with A495A495, remove the duplicate
            if clean_uuid.startswith("A495A495"):
                clean_uuid = clean_uuid[4:]  # Remove first A495
            
            # Check against our known UUIDs
            color = "UNKNOWN"
            if clean_uuid in TILT_UUIDS:
                color = TILT_UUIDS[clean_uuid]
            
            if color == "UNKNOWN":
                return  # Silently skip unknown UUIDs for clean monitor display
                
            # Use clean UUID as device key
            device_key = clean_uuid
            
            # Get or create device
            if device_key not in self.devices:
                self.devices[device_key] = TiltDevice(color, device_key)

                # Apply stored calibration if available
                if color in self.calibration_data:
                    cal = self.calibration_data[color]
                    self.devices[device_key].temp_offset = cal.get('temp_offset', 0.0)
                    self.devices[device_key].gravity_offset = cal.get('gravity_offset', 0.0)
                    if not self.quiet:
                        print(f"[{color}] Applied calibration - Temp: {self.devices[device_key].temp_offset:+.1f}°F, Gravity: {self.devices[device_key].gravity_offset:+.4f}")

                if not self.quiet:
                    print(f"[DISCOVERED] {color} Tilt detected (UUID: {clean_uuid}, MAC: {mac_addr})")
            
            # Update device reading
            self.devices[device_key].update_reading(temp_f, gravity, rssi_val)
            
            # Print reading only if not in quiet mode
            if not self.quiet:
                device = self.devices[device_key]
                print(f"[{color}] Raw: {temp_f:.1f}°F, {gravity:.3f} SG | "
                      f"Calibrated: {device.get_calibrated_temperature_f():.1f}°F "
                      f"({device.get_calibrated_temperature_c():.1f}°C), "
                      f"{device.get_calibrated_gravity():.3f} SG | "
                      f"RSSI: {rssi_val} dBm")
                      
        except json.JSONDecodeError as e:
            if not self.quiet:
                print(f"Error parsing Tilt JSON: {e}")
                print(f"Result string: {result_str}")
        except Exception as e:
            if not self.quiet:
                print(f"Error processing Tilt data: {e}")
                print(f"Result string: {result_str}")
                        
    async def scan(self, duration: int = 30):
        """Scan for Tilt devices for specified duration"""
        if not self.quiet:
            print(f"Starting Tilt scan for {duration} seconds...")
            print("Looking for Tilt hydrometers...")
        
        conn = None
        btctrl = None
        
        try:
            event_loop = asyncio.get_running_loop()
            
            # Create Bluetooth socket
            mysocket = aiobs.create_bt_socket(self.device_id)
            
            # Create connection using stable method
            try:
                # Use the standard create_connection method
                conn, btctrl = await event_loop.create_connection(
                    aiobs.BLEScanRequester, sock=mysocket
                )
            except Exception as connect_error:
                # If that fails, try alternative method
                try:
                    conn, btctrl = await event_loop._create_connection_transport(
                        mysocket, aiobs.BLEScanRequester, None, None
                    )
                except Exception:
                    # Re-raise original connection error
                    raise connect_error
            
            # Attach our processing function
            btctrl.process = self.process_data
            
            # Start scanning - handle both sync and async versions
            try:
                if asyncio.iscoroutinefunction(btctrl.send_scan_request):
                    await btctrl.send_scan_request()
                else:
                    btctrl.send_scan_request()
            except Exception as e:
                if not self.quiet:
                    print(f"Error starting scan: {e}")
                return
                
            if not self.quiet:
                print("Bluetooth LE scanning started...")
            
            self.running = True
            
            # Scan for specified duration
            await asyncio.sleep(duration)
            
        except PermissionError as e:
            if not self.quiet:
                print(f"Permission denied: {e}")
                print("Make sure to run with sudo privileges")
            return
        except Exception as e:
            if not self.quiet:
                print(f"Error during scanning: {e}")
                print("Make sure Bluetooth is enabled and you have proper permissions")
            return
            
        finally:
            cleanup_errors = []
            
            # Stop scanning safely - handle both sync and async versions
            if btctrl:
                try:
                    if asyncio.iscoroutinefunction(btctrl.stop_scan_request):
                        await btctrl.stop_scan_request()
                    else:
                        btctrl.stop_scan_request()
                except Exception as e:
                    cleanup_errors.append(f"Stop scan: {e}")
                    
            # Close connection safely
            if conn:
                try:
                    conn.close()
                except Exception as e:
                    cleanup_errors.append(f"Close connection: {e}")
                    
            self.running = False
            
            if not self.quiet:
                if cleanup_errors:
                    print(f"Cleanup warnings: {', '.join(cleanup_errors)}")
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
        """Load calibration data from file and apply to existing and future devices"""
        try:
            with open(filename, 'r') as f:
                self.calibration_data = json.load(f)

            # Apply calibration to any already-discovered devices
            for device in self.devices.values():
                if device.color in self.calibration_data:
                    cal = self.calibration_data[device.color]
                    device.temp_offset = cal.get('temp_offset', 0.0)
                    device.gravity_offset = cal.get('gravity_offset', 0.0)
                    print(f"[{device.color}] Loaded calibration - Temp: {device.temp_offset:+.1f}°F, Gravity: {device.gravity_offset:+.4f}")

            # If no devices yet, just store for later
            if not self.devices:
                colors_loaded = ', '.join(self.calibration_data.keys())
                print(f"Calibration data loaded for: {colors_loaded} (will be applied when devices are discovered)")

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