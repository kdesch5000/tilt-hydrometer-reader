#!/usr/bin/env python3
"""
Tidbyt Installation Cleanup Tool
Removes old/duplicate Tilt installations and pushes a fresh one
"""

import requests
import json
from tidbyt_integration import TidbytPusher
from test_tidbyt import MockTiltDevice

def cleanup_and_push_fresh():
    """Remove old installations and push a completely fresh Tilt display"""
    
    pusher = TidbytPusher()
    
    if not pusher.config or not pusher.enabled:
        print("❌ Tidbyt not configured. Please configure first.")
        return
    
    device_id = pusher.config.device_id
    api_key = pusher.config.api_key
    
    print(f"🧹 Cleaning up Tidbyt installations for device: {device_id}")
    
    # Step 1: Try to clear any existing installations by pushing empty/background
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json'
    }
    
    # List of possible old installation IDs to try clearing
    old_ids = [
        "tilt-hydrometer",
        "Tilt Hydrometer", 
        "tilt-red-hydrometer",
        "tilt-green-hydrometer", 
        "tilt-black-hydrometer",
        "VqrvNQfRaE2722H3UO3qZ",  # The weird one you saw
    ]
    
    # Try to remove each old installation
    for old_id in old_ids:
        try:
            url = f"https://api.tidbyt.com/v0/devices/{device_id}/installations/{old_id}"
            response = requests.delete(url, headers=headers, timeout=10)
            if response.status_code in [200, 204]:
                print(f"✅ Removed installation: {old_id}")
            elif response.status_code == 404:
                print(f"ℹ️  Installation not found: {old_id}")
            else:
                print(f"⚠️  Could not remove {old_id}: {response.status_code}")
        except Exception as e:
            print(f"⚠️  Error removing {old_id}: {e}")
    
    print("\n🚀 Pushing fresh Tilt display...")
    
    # Step 2: Push a completely fresh installation with new ID
    mock_device = MockTiltDevice('RED', 72.1, 1.042, -45)  # Use your actual device data
    
    try:
        # Force a fresh push with the new consistent ID
        import asyncio
        success = asyncio.run(pusher.push_to_tidbyt(mock_device))
        if success:
            print("✅ Fresh Tilt display pushed successfully!")
            print(f"✅ Installation ID: tilt-hydrometer-{mock_device.color.lower()}-v2024")
            print("\nYour Tidbyt should now show only one, current Tilt display.")
        else:
            print("❌ Failed to push fresh display")
    except Exception as e:
        print(f"❌ Error pushing fresh display: {e}")

if __name__ == "__main__":
    print("=" * 60)
    print("         TIDBYT TILT DISPLAY CLEANUP TOOL")
    print("=" * 60)
    print()
    print("This tool will:")
    print("1. Remove old/duplicate Tilt installations")
    print("2. Push a fresh, single Tilt display")
    print()
    
    confirm = input("Proceed with cleanup? (y/N) > ").strip().lower()
    if confirm == 'y':
        cleanup_and_push_fresh()
    else:
        print("Cleanup cancelled")