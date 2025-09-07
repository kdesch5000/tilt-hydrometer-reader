#!/usr/bin/env python3
"""
Minimal aioblescan test to verify basic functionality
"""

import asyncio
import aioblescan as aiobs

def simple_process(data):
    """Simple data processor that just prints raw data"""
    print(f"Received BLE data: {len(data)} bytes")

async def minimal_scan():
    print("Testing basic aioblescan functionality...")
    
    try:
        event_loop = asyncio.get_running_loop()
        mysocket = aiobs.create_bt_socket(0)
        print("✓ Bluetooth socket created")
        
        conn, btctrl = await event_loop._create_connection_transport(
            mysocket, aiobs.BLEScanRequester, None, None
        )
        print("✓ Connection established")
        
        btctrl.process = simple_process
        btctrl.send_scan_request()  # Remove await - it's not a coroutine
        print("✓ Scan request sent")
        
        print("Scanning for 5 seconds...")
        await asyncio.sleep(5)
        
        btctrl.stop_scan_request()  # Remove await - it's not a coroutine
        conn.close()
        print("✓ Scan completed successfully")
        
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    try:
        asyncio.run(minimal_scan())
    except KeyboardInterrupt:
        print("\nInterrupted")
    except Exception as e:
        print(f"Failed: {e}")