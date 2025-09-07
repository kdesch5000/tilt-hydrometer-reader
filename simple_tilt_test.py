#!/usr/bin/env python3
"""
Simple Tilt Test using aioblescan library
Based on the aioblescan __main__.py example
"""

import asyncio
import json
import aioblescan as aiobs
from aioblescan.plugins import Tilt

# Tilt color mappings
TILT_COLORS = {
    'BB10C5B14B44B5121370F02D74DE': 'RED',
    'BB20C5B14B44B5121370F02D74DE': 'GREEN', 
    'BB30C5B14B44B5121370F02D74DE': 'BLACK',
    'BB40C5B14B44B5121370F02D74DE': 'PURPLE',
    'BB50C5B14B44B5121370F02D74DE': 'ORANGE',
    'BB60C5B14B44B5121370F02D74DE': 'BLUE',
    'BB70C5B14B44B5121370F02D74DE': 'YELLOW',
    'BB80C5B14B44B5121370F02D74DE': 'PINK'
}

# Global variables
found_devices = {}
tilt_decoder = Tilt()

def process_tilt_data(data):
    """Process BLE data looking for Tilt devices"""
    ev = aiobs.HCI_Event()
    try:
        ev.decode(data)
    except:
        return
        
    # Try Tilt decoder
    result = tilt_decoder.decode(ev)
    if result:
        try:
            tilt_data = json.loads(result)
            uuid = tilt_data.get("uuid", "").upper()
            temp_f = tilt_data.get("major", 0)
            gravity_raw = tilt_data.get("minor", 0)
            gravity = gravity_raw / 1000.0
            rssi = tilt_data.get("rssi", 0)
            mac = tilt_data.get("mac", "unknown")
            
            # Determine color
            color = "UNKNOWN"
            for uuid_part, tilt_color in TILT_COLORS.items():
                if uuid_part in uuid:
                    color = tilt_color
                    break
                    
            if color != "UNKNOWN":
                device_key = f"{color}_{uuid}"
                found_devices[device_key] = {
                    'color': color,
                    'temperature_f': temp_f,
                    'gravity': gravity,
                    'rssi': rssi,
                    'mac': mac,
                    'uuid': uuid
                }
                
                print(f"[{color}] Temperature: {temp_f}°F ({(temp_f-32)*5/9:.1f}°C), "
                      f"Gravity: {gravity:.3f}, RSSI: {rssi}dBm, MAC: {mac}")
                      
        except json.JSONDecodeError as e:
            print(f"JSON decode error: {e}")
        except Exception as e:
            print(f"Processing error: {e}")

async def main():
    print("=" * 60)
    print("Simple Tilt Hydrometer Test")
    print("=" * 60)
    print("Scanning for Tilt devices for 30 seconds...")
    print("Make sure your Tilt is powered on and nearby.")
    print()
    
    event_loop = asyncio.get_running_loop()
    
    # Create Bluetooth socket
    try:
        mysocket = aiobs.create_bt_socket(0)  # Use hci0
    except Exception as e:
        print(f"Failed to create Bluetooth socket: {e}")
        print("Make sure Bluetooth is enabled and you're running with sudo")
        return
    
    conn = None
    btctrl = None
    
    try:
        # Create connection - try the method from aioblescan example
        conn, btctrl = await event_loop._create_connection_transport(
            mysocket, aiobs.BLEScanRequester, None, None
        )
        
        # Attach our processing function
        btctrl.process = process_tilt_data
        
        # Start scanning
        btctrl.send_scan_request()  # Not a coroutine
        print("Bluetooth scanning started...")
        
        # Scan for 30 seconds
        await asyncio.sleep(30)
        
    except Exception as e:
        print(f"Scanning error: {e}")
        
    finally:
        try:
            if btctrl:
                btctrl.stop_scan_request()  # Not a coroutine
            if conn:
                conn.close()
        except:
            pass
            
        print(f"\nScan complete! Found {len(found_devices)} Tilt device(s):")
        for device_key, device_data in found_devices.items():
            print(f"  {device_data['color']}: {device_data['temperature_f']}°F, {device_data['gravity']:.3f} SG")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nScan interrupted by user.")
    except Exception as e:
        print(f"Error: {e}")
        print("Make sure to run with: sudo python3 simple_tilt_test.py")