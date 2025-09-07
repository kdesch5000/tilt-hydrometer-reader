#!/usr/bin/env python3
"""
Direct Tilt scanner using aioblescan CLI pattern
Exactly follows the aioblescan __main__.py implementation
"""

import asyncio
import json
import aioblescan as aiobs
from aioblescan.plugins import Tilt

# Global variables (following aioblescan pattern)
tilt_decoder = Tilt()

def tilt_process(data):
    """Process function following aioblescan pattern"""
    ev = aiobs.HCI_Event()
    try:
        ev.decode(data)
        
        # Try Tilt decoder
        result = tilt_decoder.decode(ev)
        if result:
            print(f"Tilt Data: {result}")
            
    except Exception as e:
        pass  # Ignore decode errors for non-Tilt devices

async def amain():
    """Main async function following aioblescan pattern"""
    print("Starting Tilt scan (press Ctrl+C to stop)...")
    
    event_loop = asyncio.get_running_loop()

    # Create socket (following aioblescan example exactly)
    mysocket = aiobs.create_bt_socket(0)  # hci0

    # Create connection (exact aioblescan pattern)
    conn, btctrl = await event_loop._create_connection_transport(
        mysocket, aiobs.BLEScanRequester, None, None
    )

    # Attach processing function
    btctrl.process = tilt_process

    # Send scan request
    btctrl.send_scan_request()  # Not a coroutine

    try:
        # Run for 30 seconds instead of infinite loop
        print("Scanning for 30 seconds...")
        await asyncio.sleep(30)
    except KeyboardInterrupt:
        print("\nKeyboard interrupt")
    finally:
        print("\nStopping scan...")
        btctrl.stop_scan_request()  # Not a coroutine
        conn.close()

if __name__ == "__main__":
    try:
        asyncio.run(amain())
    except Exception as e:
        print(f"Error: {e}")
        print("Make sure to run with: sudo python3 tilt_direct.py")