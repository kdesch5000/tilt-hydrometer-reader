#!/usr/bin/env python3
"""
Simple test script for Tidbyt display with custom SG and temperature values
Generates a WebP image file for inspection without pushing to actual device

Usage:
    python3 test_tidbyt_custom.py [gravity] [temp_f] [color]

Examples:
    python3 test_tidbyt_custom.py 1.045 68.5 RED
    python3 test_tidbyt_custom.py 1.020 72.0 GREEN
    python3 test_tidbyt_custom.py 1.060 65.5 PURPLE
"""

import sys
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


def test_custom_display(gravity=1.045, temp_f=68.5, color="RED"):
    """Generate test display with custom values"""

    print("=" * 60)
    print("         TIDBYT CUSTOM DISPLAY TEST")
    print("=" * 60)
    print(f"\nGenerating display with:")
    print(f"  Color:       {color}")
    print(f"  Gravity:     {gravity:.3f} SG")
    print(f"  Temperature: {temp_f:.1f}°F ({(temp_f - 32) * 5/9:.1f}°C)")
    print()

    # Create pusher (no need for actual config)
    pusher = TidbytPusher()

    # Create mock device with custom values
    mock_device = MockTiltDevice(
        color=color.upper(),
        temperature_f=temp_f,
        specific_gravity=gravity
    )

    try:
        # Generate WebP image
        image_data = pusher._create_webp_payload(mock_device)

        if isinstance(image_data, bytes):
            # Save with descriptive filename
            filename = f"test_tidbyt_{color.lower()}_sg{gravity:.3f}_temp{temp_f:.1f}.webp"
            with open(filename, "wb") as f:
                f.write(image_data)

            print(f"✅ Generated WebP image: {len(image_data)} bytes")
            print(f"✅ Saved as: {filename}")
            print()
            print("View the image with:")
            print(f"  - Image viewer: open {filename}")
            print(f"  - Or push to Tidbyt using pixlet (if installed)")
            print()

        else:
            print(f"⚠️  Generated fallback data (PIL not available)")
            print(f"   Install Pillow: pip install Pillow")

        return True

    except Exception as e:
        print(f"❌ Image generation failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Parse arguments and run test"""

    # Default values
    gravity = 1.045
    temp_f = 68.5
    color = "RED"

    # Parse command line arguments
    if len(sys.argv) > 1:
        try:
            gravity = float(sys.argv[1])
            if gravity < 0.990 or gravity > 1.200:
                print(f"⚠️  Warning: Gravity {gravity} is outside typical range (0.990-1.200)")
        except ValueError:
            print(f"❌ Invalid gravity value: {sys.argv[1]}")
            print("Usage: python3 test_tidbyt_custom.py [gravity] [temp_f] [color]")
            sys.exit(1)

    if len(sys.argv) > 2:
        try:
            temp_f = float(sys.argv[2])
            if temp_f < 32 or temp_f > 212:
                print(f"⚠️  Warning: Temperature {temp_f}°F is outside typical range (32-212)")
        except ValueError:
            print(f"❌ Invalid temperature value: {sys.argv[2]}")
            print("Usage: python3 test_tidbyt_custom.py [gravity] [temp_f] [color]")
            sys.exit(1)

    if len(sys.argv) > 3:
        color = sys.argv[3].upper()
        valid_colors = ["RED", "GREEN", "BLACK", "PURPLE", "ORANGE", "BLUE", "YELLOW", "PINK"]
        if color not in valid_colors:
            print(f"⚠️  Warning: {color} not in standard Tilt colors")
            print(f"   Valid colors: {', '.join(valid_colors)}")
            # Allow it anyway for testing

    # Run test
    success = test_custom_display(gravity, temp_f, color)

    if success:
        print("✅ Test completed successfully!")
        print()
        print("Quick tests you can try:")
        print("  python3 test_tidbyt_custom.py 1.020 72.0 GREEN")
        print("  python3 test_tidbyt_custom.py 1.060 65.5 PURPLE")
        print("  python3 test_tidbyt_custom.py 1.000 68.0 BLUE")
        sys.exit(0)
    else:
        print("❌ Test failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()
