#!/usr/bin/env python3
"""
Tilt Hydrometer Calibration Helper
Interactive tool for calibrating Tilt hydrometers using water reference
"""

import asyncio
import json
from tilt_scanner import TiltScanner

async def calibration_session():
    """Interactive calibration session"""
    print("=" * 60)
    print("Tilt Hydrometer Calibration Tool")
    print("=" * 60)
    print("This tool will help you calibrate your Tilt for better accuracy.")
    print("For best results:")
    print("1. Place Tilt in clean water (gravity = 1.000)")
    print("2. Measure water temperature with accurate thermometer")
    print("3. Let Tilt stabilize for 2-3 minutes")
    print("4. Run this calibration")
    print()
    
    scanner = TiltScanner()
    
    # Load existing calibration
    scanner.load_calibration()
    
    # Short scan to find devices
    print("Scanning for Tilt devices...")
    await scanner.scan(15)
    
    if not scanner.devices:
        print("No Tilt devices found. Make sure your Tilt is powered on and nearby.")
        return
        
    print("\nFound the following Tilt devices:")
    scanner.list_devices()
    
    # Interactive calibration
    while True:
        print("\nCalibration Menu:")
        print("1. Calibrate a device")
        print("2. Scan again (15 seconds)")
        print("3. Show current readings")
        print("4. Save and exit")
        print("5. Exit without saving")
        
        choice = input("\nEnter choice (1-5): ").strip()
        
        if choice == '1':
            # Select device to calibrate
            colors = [device.color for device in scanner.devices.values()]
            print(f"\nAvailable devices: {', '.join(colors)}")
            color = input("Enter Tilt color to calibrate: ").strip().upper()
            
            device = None
            for d in scanner.devices.values():
                if d.color == color:
                    device = d
                    break
                    
            if not device:
                print(f"Device {color} not found.")
                continue
                
            print(f"\nCalibrating {color} Tilt:")
            print(f"Current reading: {device.temperature_f:.1f}°F, {device.specific_gravity:.3f} SG")
            
            # Get reference temperature
            try:
                ref_temp = float(input("Enter actual water temperature (°F): "))
                ref_gravity = 1.000
                
                # Apply calibration
                device.calibrate(ref_temp, ref_gravity)
                
                print(f"\n{color} Tilt calibrated successfully!")
                print(f"New reading: {device.get_calibrated_temperature_f():.1f}°F, {device.get_calibrated_gravity():.3f} SG")
                
            except ValueError:
                print("Invalid temperature. Please enter a numeric value.")
                
        elif choice == '2':
            print("Scanning for 15 seconds...")
            await scanner.scan(15)
            scanner.list_devices()
            
        elif choice == '3':
            scanner.list_devices()
            
        elif choice == '4':
            scanner.save_calibration()
            print("Calibration saved. Exiting...")
            break
            
        elif choice == '5':
            print("Exiting without saving...")
            break
            
        else:
            print("Invalid choice. Please enter 1-5.")

def create_sample_calibration():
    """Create a sample calibration file"""
    sample_data = {
        "RED": {
            "temp_offset": 0.0,
            "gravity_offset": 0.0
        },
        "GREEN": {
            "temp_offset": 0.0,
            "gravity_offset": 0.0
        },
        "BLACK": {
            "temp_offset": 0.0,
            "gravity_offset": 0.0
        }
    }
    
    with open('tilt_calibration.json', 'w') as f:
        json.dump(sample_data, f, indent=2)
    print("Sample calibration file created: tilt_calibration.json")

if __name__ == "__main__":
    try:
        asyncio.run(calibration_session())
    except KeyboardInterrupt:
        print("\nCalibration interrupted by user.")
    except Exception as e:
        print(f"Error: {e}")
        print("Note: This program requires root privileges to access Bluetooth.")
        print("Try running with: sudo python3 calibrate_tilt.py")