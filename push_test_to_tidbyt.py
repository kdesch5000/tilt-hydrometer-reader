#!/usr/bin/env python3
"""
Push test display directly to your Tidbyt device
Shows the enhanced brighter and thicker lines
"""

import sys
import asyncio
from datetime import datetime
from dataclasses import dataclass
from tidbyt_integration import TidbytPusher


@dataclass
class MockTiltDevice:
    """Mock Tilt device for testing with custom values"""
    color: str = "RED"
    temperature_f: float = 68.5
    specific_gravity: float = 1.045
    rssi: int = -45
    last_seen: datetime = None
    temp_offset: float = 0.0
    gravity_offset: float = 0.0
    uuid: str = "mock-device-test"

    def __post_init__(self):
        if self.last_seen is None:
            self.last_seen = datetime.now()

    def get_calibrated_temperature_f(self):
        return self.temperature_f + self.temp_offset

    def get_calibrated_temperature_c(self):
        return (self.get_calibrated_temperature_f() - 32) * 5/9

    def get_calibrated_gravity(self):
        return self.specific_gravity + self.gravity_offset


async def push_test_display(gravity=1.045, temp_f=68.5, color="RED"):
    """Push test display to actual Tidbyt device"""

    print("=" * 60)
    print("         PUSH TEST TO TIDBYT DEVICE")
    print("=" * 60)
    print()

    # Create pusher with your actual config
    pusher = TidbytPusher()

    if not pusher.config:
        print("❌ Tidbyt not configured!")
        print("   Please configure Tidbyt in tilt_config.json")
        return False

    print(f"📡 Pushing to Tidbyt device: {pusher.config.device_id}")
    print()
    print(f"Display settings:")
    print(f"  Color:       {color}")
    print(f"  Gravity:     {gravity:.3f} SG")
    print(f"  Temperature: {temp_f:.1f}°F ({(temp_f - 32) * 5/9:.1f}°C)")
    print()

    # Create mock device with custom values
    mock_device = MockTiltDevice(
        color=color.upper(),
        temperature_f=temp_f,
        specific_gravity=gravity
    )

    # Override the should_push check for testing
    pusher.last_push.clear()

    try:
        print("⏳ Pushing to Tidbyt...")
        success = await pusher.push_to_tidbyt(mock_device)

        if success:
            print()
            print("✅ Successfully pushed to Tidbyt!")
            print()
            print("Check your Tidbyt device now to see:")
            print("  ✓ Brighter white boxes (240,240,240 instead of 100,100,100)")
            print("  ✓ Thicker borders (2px instead of 1px)")
            print("  ✓ Thicker status bar at bottom")
            print()
            print(f"Installation ID: tilthydrometer{color.lower()}v2024")
            return True
        else:
            print()
            print("❌ Push failed - check the error message above")
            return False

    except Exception as e:
        print()
        print(f"❌ Error pushing to Tidbyt: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Parse arguments and push to Tidbyt"""

    # Default values
    gravity = 1.045
    temp_f = 68.5
    color = "RED"

    # Parse command line arguments
    if len(sys.argv) > 1:
        try:
            gravity = float(sys.argv[1])
        except ValueError:
            print(f"❌ Invalid gravity value: {sys.argv[1]}")
            sys.exit(1)

    if len(sys.argv) > 2:
        try:
            temp_f = float(sys.argv[2])
        except ValueError:
            print(f"❌ Invalid temperature value: {sys.argv[2]}")
            sys.exit(1)

    if len(sys.argv) > 3:
        color = sys.argv[3].upper()

    # Run async push
    success = asyncio.run(push_test_display(gravity, temp_f, color))

    if success:
        print("Try different values:")
        print("  python3 push_test_to_tidbyt.py 1.020 72.0 GREEN")
        print("  python3 push_test_to_tidbyt.py 1.060 65.5 PURPLE")
        sys.exit(0)
    else:
        print()
        print("❌ Push failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()
