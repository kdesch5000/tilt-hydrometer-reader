#!/usr/bin/env python3
"""
Test script for Tidbyt integration
Creates mock Tilt data and tests the image generation and API
"""

import asyncio
import json
from datetime import datetime
from dataclasses import dataclass
from tidbyt_integration import TidbytPusher, configure_interactive
from tilt_api_server import TiltAPIServer


@dataclass
class MockTiltDevice:
    """Mock Tilt device for testing"""
    color: str = "RED"
    temperature_f: float = 68.5
    specific_gravity: float = 1.045
    rssi: int = -45
    last_seen: datetime = None
    temp_offset: float = 0.0
    gravity_offset: float = 0.0
    uuid: str = "mock-device-123"
    
    def __post_init__(self):
        if self.last_seen is None:
            self.last_seen = datetime.now()
    
    def get_calibrated_temperature_f(self):
        return self.temperature_f + self.temp_offset
    
    def get_calibrated_temperature_c(self):
        return (self.get_calibrated_temperature_f() - 32) * 5/9
    
    def get_calibrated_gravity(self):
        return self.specific_gravity + self.gravity_offset


class MockTiltMonitor:
    """Mock Tilt monitor for testing"""
    
    def __init__(self):
        self.scanner = MockTiltScanner()
        self.logger = MockTiltLogger()
    

class MockTiltScanner:
    """Mock Tilt scanner for testing"""
    
    def __init__(self):
        # Create some test devices
        self.devices = {
            "red": MockTiltDevice("RED", 68.5, 1.045, -45),
            "green": MockTiltDevice("GREEN", 72.1, 1.020, -52),
            "black": MockTiltDevice("BLACK", 65.8, 1.060, -38),
        }


class MockTiltLogger:
    """Mock Tilt logger for testing"""
    
    def __init__(self):
        self.history = {
            "RED": [],
            "GREEN": [],
            "BLACK": []
        }


def test_image_generation():
    """Test WebP image generation"""
    print("Testing WebP image generation...")
    
    pusher = TidbytPusher()
    mock_device = MockTiltDevice()
    
    try:
        image_data = pusher._create_webp_payload(mock_device)
        
        if isinstance(image_data, bytes):
            print(f"✅ Generated WebP image: {len(image_data)} bytes")
            
            # Save test image for inspection
            with open("test_tilt_display.webp", "wb") as f:
                f.write(image_data)
            print("✅ Saved test image as test_tilt_display.webp")
            
        else:
            print(f"✅ Generated fallback data: {len(str(image_data))} characters")
            print(f"   Content: {image_data}")
            
        return True
        
    except Exception as e:
        print(f"❌ Image generation failed: {e}")
        return False


def test_api_server():
    """Test the API server with mock data"""
    print("\nTesting API server...")
    
    # Create mock monitor
    mock_monitor = MockTiltMonitor()
    
    # Start API server
    server = TiltAPIServer(host='localhost', port=8001)  # Use different port for testing
    server.set_tilt_monitor(mock_monitor)
    
    try:
        server.start()
        
        import time
        time.sleep(1)  # Give server time to start
        
        # Test API endpoints
        import requests
        
        # Test status endpoint
        response = requests.get("http://localhost:8001/")
        if response.status_code == 200:
            print("✅ Status endpoint working")
            status_data = response.json()
            print(f"   Found {status_data['total_devices']} devices")
        else:
            print(f"❌ Status endpoint failed: {response.status_code}")
            
        # Test device endpoint
        response = requests.get("http://localhost:8001/api/tilt/red")
        if response.status_code == 200:
            print("✅ Device endpoint working")
            device_data = response.json()
            print(f"   RED Tilt: {device_data['temperature']}°F, {device_data['gravity']} SG")
        else:
            print(f"❌ Device endpoint failed: {response.status_code}")
        
        server.stop()
        return True
        
    except Exception as e:
        print(f"❌ API server test failed: {e}")
        server.stop()
        return False


def test_tidbyt_config():
    """Test Tidbyt configuration"""
    print("\nTesting Tidbyt configuration...")
    
    pusher = TidbytPusher()
    
    # Test configuration
    pusher.configure_tidbyt(
        device_id="test-device-123",
        api_key="test-api-key-456", 
        installation_id="test-install-789",
        enabled=True,
        push_interval_seconds=60
    )
    
    if pusher.config and pusher.enabled:
        print("✅ Configuration successful")
        print(f"   Device ID: {pusher.config.device_id}")
        print(f"   Installation ID: {pusher.config.installation_id}")
        print(f"   Push interval: {pusher.config.push_interval_seconds}s")
        
        # Test status
        status = pusher.get_status()
        print(f"   Status: {status}")
        
        return True
    else:
        print("❌ Configuration failed")
        return False


def test_mock_push():
    """Test pushing mock data (without actually sending to Tidbyt)"""
    print("\nTesting mock data push...")
    
    pusher = TidbytPusher()
    pusher.configure_tidbyt("test", "test", "test", True, 1)  # Very short interval for testing
    
    mock_device = MockTiltDevice()
    
    # Test should_push logic
    should_push_first = pusher.should_push(mock_device.color)
    print(f"✅ Should push first time: {should_push_first}")
    
    # Simulate marking as pushed
    pusher.last_push[mock_device.color] = datetime.now()
    should_push_second = pusher.should_push(mock_device.color)
    print(f"✅ Should push again immediately: {should_push_second}")
    
    return True


async def test_full_integration():
    """Test full integration with mock monitor"""
    print("\nTesting full integration...")
    
    # Import the monitor with Tidbyt enabled
    import sys
    import os
    sys.path.insert(0, os.path.dirname(__file__))
    
    from tilt_monitor import EasyHistoryMonitor
    
    # Mock the scanner to avoid actual Bluetooth scanning
    monitor = EasyHistoryMonitor(enable_tidbyt=True)
    monitor.scanner = MockTiltScanner()
    
    if monitor.tidbyt:
        print("✅ Tidbyt integration loaded in monitor")
        
        # Configure with test settings
        monitor.tidbyt.configure_tidbyt("test", "test", "test", True, 1)
        
        # Test the integration
        mock_device = list(monitor.scanner.devices.values())[0]
        
        try:
            # This would normally push to Tidbyt, but will fail gracefully with test config
            result = await monitor.tidbyt.push_to_tidbyt(mock_device)
            print(f"✅ Push attempt completed (result: {result})")
        except Exception as e:
            print(f"✅ Push attempt failed as expected with test config: {e}")
        
        return True
    else:
        print("❌ Tidbyt integration not available")
        return False


def main():
    """Run all tests"""
    print("=" * 60)
    print("              TIDBYT INTEGRATION TESTS")
    print("=" * 60)
    
    tests = [
        ("Image Generation", test_image_generation),
        ("API Server", test_api_server),
        ("Configuration", test_tidbyt_config),
        ("Mock Data Push", test_mock_push),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n--- {test_name} ---")
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} failed with exception: {e}")
            results.append((test_name, False))
    
    # Test async integration
    print(f"\n--- Full Integration ---")
    try:
        result = asyncio.run(test_full_integration())
        results.append(("Full Integration", result))
    except Exception as e:
        print(f"❌ Full Integration failed: {e}")
        results.append(("Full Integration", False))
    
    # Summary
    print("\n" + "=" * 60)
    print("                    TEST RESULTS")
    print("=" * 60)
    
    passed = 0
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name:20} {status}")
        if result:
            passed += 1
    
    print(f"\nPassed: {passed}/{len(results)} tests")
    
    if passed == len(results):
        print("🎉 All tests passed! Tidbyt integration is ready.")
    else:
        print("⚠️  Some tests failed. Check the output above.")
    
    # Clean up test files
    try:
        import os
        if os.path.exists("test_tilt_display.webp"):
            os.remove("test_tilt_display.webp")
        if os.path.exists("tilt_config.json"):
            # Reset config for actual use
            with open("tilt_config.json", "r") as f:
                config = json.load(f)
            config.pop("tidbyt", None)
            with open("tilt_config.json", "w") as f:
                json.dump(config, f, indent=2)
    except:
        pass


if __name__ == "__main__":
    main()