#!/usr/bin/env python3
"""
Quick calibration for RED Tilt with water reference
Water temperature: 68°F, Gravity: 1.000
"""

import asyncio
from tilt_scanner import TiltScanner

async def quick_calibrate():
    print("=" * 60)
    print("Quick Tilt Calibration - Water Reference")
    print("=" * 60)
    print("Water temperature: 68°F")
    print("Expected gravity: 1.000")
    print()
    
    scanner = TiltScanner()
    
    # Load existing calibration
    scanner.load_calibration()
    
    print("Scanning for RED Tilt (10 seconds)...")
    await scanner.scan(10)
    
    # Find RED Tilt
    red_device = None
    for device in scanner.devices.values():
        if device.color == "RED":
            red_device = device
            break
    
    if not red_device:
        print("❌ RED Tilt not found. Make sure it's powered on and nearby.")
        return
    
    print(f"\n📊 Current RED Tilt readings:")
    print(f"   Temperature: {red_device.temperature_f:.1f}°F")
    print(f"   Gravity: {red_device.specific_gravity:.3f}")
    print()
    
    # Calculate and apply calibration
    actual_temp_f = 68.0
    actual_gravity = 1.000
    
    print("🔧 Applying calibration...")
    red_device.calibrate(actual_temp_f, actual_gravity)
    
    print(f"\n✅ Calibrated readings:")
    print(f"   Temperature: {red_device.get_calibrated_temperature_f():.1f}°F ({red_device.get_calibrated_temperature_c():.1f}°C)")
    print(f"   Gravity: {red_device.get_calibrated_gravity():.3f}")
    
    print(f"\n📝 Calibration offsets:")
    print(f"   Temperature offset: {red_device.temp_offset:+.1f}°F")
    print(f"   Gravity offset: {red_device.gravity_offset:+.4f}")
    
    # Save calibration
    scanner.save_calibration()
    print("\n💾 Calibration saved to tilt_calibration.json")
    print("✅ Calibration complete!")

if __name__ == "__main__":
    try:
        asyncio.run(quick_calibrate())
    except KeyboardInterrupt:
        print("\nCalibration interrupted.")
    except Exception as e:
        print(f"Error: {e}")
        print("Make sure to run with: sudo python3 quick_calibrate.py")