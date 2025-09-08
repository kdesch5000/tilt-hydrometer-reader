#!/usr/bin/env python3
"""
Simple HTTP API server for Tilt data
Serves current Tilt readings as JSON for Pixlet/Tidbyt consumption
"""

import asyncio
import json
import csv
import os
from datetime import datetime, timedelta
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse
import threading

from tilt_scanner import TiltScanner


class TiltDataHandler(BaseHTTPRequestHandler):
    """HTTP request handler for Tilt data API"""
    
    def __init__(self, *args, tilt_monitor=None, **kwargs):
        self.tilt_monitor = tilt_monitor
        super().__init__(*args, **kwargs)
    
    def do_GET(self):
        """Handle GET requests"""
        parsed_path = urlparse(self.path)
        path_parts = parsed_path.path.strip('/').split('/')
        
        if path_parts[0] == 'api' and len(path_parts) >= 3:
            if path_parts[1] == 'tilt':
                device_color = path_parts[2].upper()
                self.serve_tilt_data(device_color)
            else:
                self.send_404()
        elif parsed_path.path == '/':
            self.serve_status()
        else:
            self.send_404()
    
    def do_OPTIONS(self):
        """Handle CORS preflight requests"""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
    
    def serve_tilt_data(self, device_color):
        """Serve current data for a specific Tilt device"""
        try:
            if not self.tilt_monitor or not self.tilt_monitor.scanner:
                self.send_error_response("Tilt scanner not available")
                return
            
            # Find device by color
            device = None
            for d in self.tilt_monitor.scanner.devices.values():
                if d.color.upper() == device_color:
                    device = d
                    break
            
            if not device:
                self.send_error_response(f"Tilt device {device_color} not found")
                return
            
            # Check if device is recent (within 2 minutes)
            if device.last_seen and (datetime.now() - device.last_seen).seconds > 120:
                self.send_error_response(f"Tilt device {device_color} offline")
                return
            
            # Get trend data from history
            trend = self.calculate_trend(device_color)
            
            # Prepare response data
            data = {
                "color": device.color,
                "temperature": round(device.get_calibrated_temperature_f(), 1),
                "gravity": round(device.get_calibrated_gravity(), 3),
                "rssi": device.rssi,
                "timestamp": device.last_seen.isoformat() if device.last_seen else None,
                "trend": trend,
                "status": "online"
            }
            
            self.send_json_response(data)
            
        except Exception as e:
            self.send_error_response(f"Error getting Tilt data: {str(e)}")
    
    def calculate_trend(self, device_color):
        """Calculate gravity trend from recent readings"""
        try:
            if not self.tilt_monitor or device_color not in self.tilt_monitor.logger.history:
                return "unknown"
            
            history = self.tilt_monitor.logger.history[device_color]
            
            if len(history) < 2:
                return "stable"
            
            # Get readings from last 30 minutes
            recent_readings = [
                point for point in history 
                if (datetime.now() - point.timestamp).seconds <= 1800  # 30 minutes
            ]
            
            if len(recent_readings) < 2:
                return "stable"
            
            # Calculate trend
            oldest_gravity = recent_readings[0].gravity
            newest_gravity = recent_readings[-1].gravity
            
            gravity_change = newest_gravity - oldest_gravity
            
            # Threshold for significant change (0.002 SG)
            if abs(gravity_change) < 0.002:
                return "stable"
            elif gravity_change > 0:
                return "rising"
            else:
                return "falling"
                
        except Exception:
            return "unknown"
    
    def serve_status(self):
        """Serve API status and available devices"""
        try:
            if not self.tilt_monitor or not self.tilt_monitor.scanner:
                self.send_error_response("Tilt scanner not available")
                return
            
            devices = []
            for device in self.tilt_monitor.scanner.devices.values():
                online = device.last_seen and (datetime.now() - device.last_seen).seconds < 120
                devices.append({
                    "color": device.color,
                    "online": online,
                    "last_seen": device.last_seen.isoformat() if device.last_seen else None,
                    "temperature": round(device.get_calibrated_temperature_f(), 1) if online else None,
                    "gravity": round(device.get_calibrated_gravity(), 3) if online else None
                })
            
            status = {
                "api_version": "1.0",
                "timestamp": datetime.now().isoformat(),
                "devices": devices,
                "total_devices": len(devices),
                "online_devices": sum(1 for d in devices if d["online"])
            }
            
            self.send_json_response(status)
            
        except Exception as e:
            self.send_error_response(f"Error getting status: {str(e)}")
    
    def send_json_response(self, data):
        """Send JSON response"""
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        
        json_data = json.dumps(data, indent=2)
        self.wfile.write(json_data.encode('utf-8'))
    
    def send_error_response(self, message):
        """Send error response"""
        self.send_response(404)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        
        error_data = {
            "error": message,
            "timestamp": datetime.now().isoformat()
        }
        
        json_data = json.dumps(error_data, indent=2)
        self.wfile.write(json_data.encode('utf-8'))
    
    def send_404(self):
        """Send 404 response"""
        self.send_error_response("Endpoint not found")
    
    def log_message(self, format, *args):
        """Suppress default logging"""
        pass


class TiltAPIServer:
    """HTTP server for Tilt data API"""
    
    def __init__(self, host='localhost', port=8000):
        self.host = host
        self.port = port
        self.server = None
        self.server_thread = None
        self.tilt_monitor = None
        self.running = False
    
    def set_tilt_monitor(self, monitor):
        """Set the Tilt monitor instance"""
        self.tilt_monitor = monitor
    
    def start(self):
        """Start the HTTP server in a separate thread"""
        if self.running:
            return
        
        def handler(*args, **kwargs):
            return TiltDataHandler(*args, tilt_monitor=self.tilt_monitor, **kwargs)
        
        self.server = HTTPServer((self.host, self.port), handler)
        self.running = True
        
        self.server_thread = threading.Thread(
            target=self._run_server, 
            daemon=True
        )
        self.server_thread.start()
        
        print(f"Tilt API server started at http://{self.host}:{self.port}")
        print(f"API endpoints:")
        print(f"  GET / - Status and available devices")
        print(f"  GET /api/tilt/{{color}} - Get data for specific Tilt (e.g., /api/tilt/red)")
    
    def _run_server(self):
        """Run the HTTP server"""
        try:
            self.server.serve_forever()
        except Exception as e:
            print(f"API server error: {e}")
    
    def stop(self):
        """Stop the HTTP server"""
        if self.running and self.server:
            self.server.shutdown()
            self.server.server_close()
            self.running = False
            print("Tilt API server stopped")


if __name__ == "__main__":
    # Test server without Tilt monitor
    server = TiltAPIServer()
    
    try:
        server.start()
        print("Test API server running. Press Ctrl+C to stop.")
        
        # Keep the main thread alive
        import time
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\nShutting down API server...")
        server.stop()