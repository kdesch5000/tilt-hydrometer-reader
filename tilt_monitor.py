#!/usr/bin/env python3
"""
Easy History Monitor - Simple controls with threading for keyboard input
"""

import asyncio
import json
import csv
import os
import sys
import signal
import threading
import requests
import termios
import tty
import select
import argparse
from datetime import datetime, timedelta
from typing import Dict, List
from dataclasses import dataclass
from pathlib import Path

from tilt_scanner import TiltScanner, TiltDevice

# ANSI Color Codes
COLORS = {
    'reset': '\033[0m',
    'black_bg': '\033[40m',
    'green': '\033[32m',
    'bold_white': '\033[1;97m',
    'yellow': '\033[33m',
    'clear_screen': '\033[2J\033[H',
}

@dataclass
class DataPoint:
    timestamp: datetime
    temperature_f: float
    gravity: float
    rssi: int

class EasyHistoryLogger:
    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        self.history: Dict[str, List[DataPoint]] = {}
        self.hourly_max: Dict[str, Dict[str, float]] = {}  # color -> {hour: max_temp, hour: max_gravity}
        
    def log_reading(self, device: TiltDevice):
        if device.color not in self.history:
            self.history[device.color] = []
            self.hourly_max[device.color] = {}
            
        data_point = DataPoint(
            timestamp=datetime.now(),
            temperature_f=device.get_calibrated_temperature_f(),
            gravity=device.get_calibrated_gravity(),
            rssi=device.rssi
        )
        
        self.history[device.color].append(data_point)
        
        # Update hourly maximums
        hour_key = data_point.timestamp.strftime('%Y-%m-%d-%H')
        temp_key = f"{hour_key}-temp"
        grav_key = f"{hour_key}-grav"
        
        if temp_key not in self.hourly_max[device.color]:
            self.hourly_max[device.color][temp_key] = data_point.temperature_f
        else:
            self.hourly_max[device.color][temp_key] = max(
                self.hourly_max[device.color][temp_key], 
                data_point.temperature_f
            )
            
        if grav_key not in self.hourly_max[device.color]:
            self.hourly_max[device.color][grav_key] = data_point.gravity
        else:
            self.hourly_max[device.color][grav_key] = max(
                self.hourly_max[device.color][grav_key], 
                data_point.gravity
            )
        
        # Keep only 48 hours of hourly data
        cutoff_time = datetime.now() - timedelta(hours=48)
        cutoff_hour = cutoff_time.strftime('%Y-%m-%d-%H')
        
        keys_to_remove = [
            key for key in self.hourly_max[device.color].keys()
            if key.split('-')[:-1] < cutoff_hour.split('-')  # Compare date-hour parts
        ]
        for key in keys_to_remove:
            del self.hourly_max[device.color][key]
        
        # Keep only recent readings for trend analysis
        cutoff = datetime.now() - timedelta(hours=4)
        self.history[device.color] = [
            point for point in self.history[device.color] 
            if point.timestamp > cutoff
        ]
        
        # Save to CSV
        self._save_to_csv(device.color, data_point)
        
    def _save_to_csv(self, color: str, data_point: DataPoint):
        csv_file = self.data_dir / f"tilt_{color.lower()}_{data_point.timestamp.strftime('%Y-%m')}.csv"
        
        write_header = not csv_file.exists()
        
        with open(csv_file, 'a', newline='') as f:
            writer = csv.writer(f)
            if write_header:
                writer.writerow(['timestamp', 'temperature_f', 'temperature_c', 'gravity', 'rssi'])
            
            writer.writerow([
                data_point.timestamp.isoformat(),
                data_point.temperature_f,
                (data_point.temperature_f - 32) * 5/9,
                data_point.gravity,
                data_point.rssi
            ])

class EasyBrewStatLogger:
    def __init__(self):
        self.api_key = None
        self.last_upload = {}
        self.upload_interval_seconds = 900  # Default 15 minutes = 900 seconds
        self.enabled = False
        self._load_config()
        
    def _load_config(self):
        try:
            with open('tilt_config.json', 'r') as f:
                config = json.load(f)
                api_key = config.get('brewstat_api_key', '').strip()
                if api_key:
                    self.api_key = api_key
                    self.enabled = True
                    
                # Load upload interval (convert minutes to seconds if needed)
                interval_minutes = config.get('upload_interval_minutes', 15)
                self.upload_interval_seconds = interval_minutes * 60
                
        except FileNotFoundError:
            pass
            
    def _save_config(self, api_key: str = None, interval_seconds: int = None):
        try:
            with open('tilt_config.json', 'r') as f:
                config = json.load(f)
        except FileNotFoundError:
            config = {}
            
        if api_key is not None:
            config['brewstat_api_key'] = api_key
            
        if interval_seconds is not None:
            config['upload_interval_minutes'] = interval_seconds // 60
            self.upload_interval_seconds = interval_seconds
        
        with open('tilt_config.json', 'w') as f:
            json.dump(config, f, indent=2)
            
    def configure_interactive(self):
        print(COLORS['clear_screen'] + COLORS['black_bg'] + COLORS['green'])
        print(COLORS['bold_white'] + "=" * 60 + COLORS['green'])
        print("              BREWSTAT.US CONFIGURATION")
        print(COLORS['bold_white'] + "=" * 60 + COLORS['green'])
        print("")
        
        if self.api_key:
            masked_key = f"{self.api_key[:8]}...{self.api_key[-4:]}" if len(self.api_key) > 12 else self.api_key
            print(f"Current API Key: {masked_key}")
        else:
            print("Current API Key: [NOT SET]")
            
        print(f"Current Upload Interval: {self.upload_interval_seconds} seconds ({self.upload_interval_seconds//60} minutes)")
        print("")
        
        print(COLORS['bold_white'] + "=" * 60 + COLORS['green'])
        print("1. Change API Key")
        print("2. Change Upload Interval") 
        print("3. Disable BrewStat.us")
        print("4. Return to monitor")
        print(COLORS['bold_white'] + "=" * 60 + COLORS['green'])
        
        try:
            choice = input("Select option (1-4) > ").strip()
            
            if choice == '1':
                print("\nEnter your BrewStat.us API key:")
                print("(Get your key from https://www.brewstat.us)")
                new_key = input("API Key > ").strip()
                
                if new_key:
                    self.api_key = new_key
                    self.enabled = True
                    self._save_config(api_key=new_key)
                    print("✅ BrewStat.us API key updated!")
                else:
                    print("API key unchanged")
                    
            elif choice == '2':
                print(f"\nCurrent interval: {self.upload_interval_seconds} seconds")
                print("Enter new upload interval in SECONDS:")
                print("Examples: 300 (5 min), 900 (15 min), 1800 (30 min), 3600 (1 hour)")
                
                try:
                    new_interval = int(input("Seconds > ").strip())
                    if new_interval > 0:
                        self._save_config(interval_seconds=new_interval)
                        print(f"✅ Upload interval updated to {new_interval} seconds ({new_interval//60} minutes)")
                    else:
                        print("❌ Invalid interval - must be positive")
                except ValueError:
                    print("❌ Invalid number")
                    
            elif choice == '3':
                confirm = input("Disable BrewStat.us logging? (y/N) > ").strip().lower()
                if confirm == 'y':
                    self.api_key = None
                    self.enabled = False
                    self._save_config(api_key="")
                    print("✅ BrewStat.us logging DISABLED")
                else:
                    print("Not disabled")
                    
            elif choice == '4':
                print("Returning to monitor...")
                return
            else:
                print("Invalid choice")
                
        except KeyboardInterrupt:
            print("\nConfiguration cancelled")
        except Exception as e:
            print(f"❌ Error: {e}")
            
        print(f"\nPress Enter to return to monitor...{COLORS['reset']}")
        try:
            input()
        except KeyboardInterrupt:
            pass
            
    def should_upload(self, color: str) -> bool:
        if not self.enabled or not self.api_key:
            return False
            
        last = self.last_upload.get(color)
        if not last:
            return True
            
        return (datetime.now() - last).total_seconds() > self.upload_interval_seconds
        
    async def upload_reading(self, device: TiltDevice):
        if not self.should_upload(device.color):
            return False
            
        try:
            url = f"https://www.brewstat.us/tilt/{self.api_key}/log"
            data = {
                "timestamp": datetime.now().isoformat(),
                "temperature": device.get_calibrated_temperature_f(),
                "gravity": device.get_calibrated_gravity(),
                "color": device.color,
                "device_id": device.uuid
            }
            
            response = requests.post(url, json=data, timeout=10)
            if response.status_code == 200:
                self.last_upload[device.color] = datetime.now()
                return True
            return False
        except Exception:
            return False

class EasyHistoryMonitor:
    def __init__(self, enable_tidbyt=False):
        self.scanner = TiltScanner(quiet=True)
        self.logger = EasyHistoryLogger()
        self.brewstat = EasyBrewStatLogger()
        self.tidbyt = None
        if enable_tidbyt:
            try:
                from tidbyt_integration import TidbytPusher
                self.tidbyt = TidbytPusher()
            except ImportError:
                print("Warning: Tidbyt integration not available. Install requirements-tidbyt.txt")
        self.running = True
        self.configure_requested = False
        self.in_config_mode = False
        
    def strip_ansi(self, text):
        """Remove ANSI escape codes from text for accurate length calculation"""
        import re
        ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
        return ansi_escape.sub('', text)

    def create_large_number(self, number, decimal_places=3):
        """Create large ASCII numbers with 7 rows for better readability"""
        # 7-row ASCII digits (4 chars wide)
        digits = {
            '0': ["████", "█  █", "█  █", "█  █", "█  █", "█  █", "████"],
            '1': [" █  ", "██  ", " █  ", " █  ", " █  ", " █  ", "████"],
            '2': ["████", "   █", "   █", "████", "█   ", "█   ", "████"],
            '3': ["████", "   █", "   █", "████", "   █", "   █", "████"],
            '4': ["█  █", "█  █", "█  █", "████", "   █", "   █", "   █"],
            '5': ["████", "█   ", "█   ", "████", "   █", "   █", "████"],
            '6': ["████", "█   ", "█   ", "████", "█  █", "█  █", "████"],
            '7': ["████", "   █", "   █", "  █ ", " █  ", "█   ", "█   "],
            '8': ["████", "█  █", "█  █", "████", "█  █", "█  █", "████"],
            '9': ["████", "█  █", "█  █", "████", "   █", "   █", "████"],
            '.': ["    ", "    ", "    ", "    ", "    ", "███ ", "███ "],
        }
        
        # Format number
        formatted = f"{number:.{decimal_places}f}"
        
        # Build 7 rows WITHOUT embedded spaces
        row_parts = [[], [], [], [], [], [], []]
        
        for char in formatted:
            if char in digits:
                for i in range(7):
                    row_parts[i].append(digits[char][i])
        
        # Join with single space between digits
        rows = []
        for i in range(7):
            rows.append(" ".join(row_parts[i]))
        
        return rows

    async def _handle_calibration_menu(self):
        """Handle the calibration submenu"""
        print(COLORS['clear_screen'], end='', flush=True)
        
        # Show available devices
        print(COLORS['black_bg'] + COLORS['green'])
        print(COLORS['bold_white'] + "=" * 60 + COLORS['green'])
        print("                 DEVICE CALIBRATION")
        print(COLORS['bold_white'] + "=" * 60 + COLORS['green'])
        print("")
        
        if not self.scanner.devices:
            print("No Tilt devices detected!")
            print("Make sure your Tilt is powered on and nearby.")
            input("\nPress Enter to continue...")
            return
            
        # List available devices
        device_list = list(self.scanner.devices.values())
        print("Available devices:")
        for i, device in enumerate(device_list, 1):
            status = "ONLINE" if device.last_seen and (datetime.now() - device.last_seen).seconds < 30 else "OFFLINE"
            print(f"{i}. {device.color} TILT - {status}")
            if device.last_seen:
                temp_f = device.get_calibrated_temperature_f()
                gravity = device.get_calibrated_gravity()
                print(f"   Current: {temp_f:.1f}°F, {gravity:.3f} SG")
                if hasattr(device, 'temp_offset') and hasattr(device, 'gravity_offset'):
                    print(f"   Offsets: {device.temp_offset:+.1f}°F, {device.gravity_offset:+.4f} SG")
        
        print("")
        print("0. Return to configuration menu")
        print("")
        
        try:
            choice = input("Select device to calibrate > ").strip()
            
            if choice == '0':
                return
                
            device_num = int(choice)
            if 1 <= device_num <= len(device_list):
                selected_device = device_list[device_num - 1]
                await self._calibrate_device(selected_device)
            else:
                print("Invalid selection")
                input("\nPress Enter to continue...")
                
        except ValueError:
            print("Invalid input")
            input("\nPress Enter to continue...")
        except KeyboardInterrupt:
            print("\nCalibration cancelled")
            
    async def _calibrate_device(self, device):
        """Calibrate a specific device"""
        print(COLORS['clear_screen'], end='', flush=True)
        
        print(COLORS['black_bg'] + COLORS['green'])
        print(COLORS['bold_white'] + "=" * 60 + COLORS['green'])
        print(f"           CALIBRATING {device.color} TILT")
        print(COLORS['bold_white'] + "=" * 60 + COLORS['green'])
        print("")
        
        # Show current readings
        temp_f = device.get_calibrated_temperature_f()
        temp_c = device.get_calibrated_temperature_c()
        gravity = device.get_calibrated_gravity()
        
        print(f"Current readings:")
        print(f"  Temperature: {temp_f:.1f}°F ({temp_c:.1f}°C)")
        print(f"  Gravity: {gravity:.3f} SG")
        print("")
        
        if hasattr(device, 'temp_offset') and hasattr(device, 'gravity_offset'):
            print(f"Current offsets:")
            print(f"  Temperature: {device.temp_offset:+.1f}°F")
            print(f"  Gravity: {device.gravity_offset:+.4f} SG")
            print("")
        
        print("Calibration Instructions:")
        print("1. For temperature: Use an accurate thermometer in the same liquid")
        print("2. For gravity: Use distilled water (1.000 SG) or calibrated solution")
        print("3. Let readings stabilize for 2-3 minutes before calibrating")
        print("")
        
        print("What would you like to calibrate?")
        print("1. Temperature only")
        print("2. Gravity only") 
        print("3. Both temperature and gravity")
        print("4. Reset calibration (remove offsets)")
        print("0. Return to device menu")
        print("")
        
        try:
            choice = input("Select calibration type > ").strip()
            
            if choice == '0':
                return
            elif choice == '1':
                await self._calibrate_temperature(device)
            elif choice == '2':
                await self._calibrate_gravity(device)
            elif choice == '3':
                await self._calibrate_temperature(device)
                await self._calibrate_gravity(device)
            elif choice == '4':
                device.temp_offset = 0.0
                device.gravity_offset = 0.0
                self.scanner.save_calibration()
                print("✅ Calibration reset! All offsets set to zero.")
                input("\nPress Enter to continue...")
            else:
                print("Invalid selection")
                input("\nPress Enter to continue...")
                
        except KeyboardInterrupt:
            print("\nCalibration cancelled")
            
    async def _calibrate_temperature(self, device):
        """Calibrate temperature for a device"""
        print(f"\n--- Temperature Calibration for {device.color} TILT ---")
        print(f"Current reading: {device.get_calibrated_temperature_f():.1f}°F")
        print("")
        print("Enter the actual temperature as measured by an accurate thermometer:")
        
        try:
            actual_temp = float(input("Actual temperature (°F) > ").strip())
            
            # Calculate new offset
            current_raw_temp = device.temperature_f
            new_offset = actual_temp - current_raw_temp
            
            print(f"\nCalculating offset:")
            print(f"  Actual temperature: {actual_temp:.1f}°F")
            print(f"  Tilt raw reading: {current_raw_temp:.1f}°F") 
            print(f"  New offset: {new_offset:+.1f}°F")
            
            confirm = input(f"\nApply this calibration? (y/N) > ").strip().lower()
            if confirm == 'y':
                device.temp_offset = new_offset
                self.scanner.save_calibration()
                print("✅ Temperature calibration saved!")
                print(f"New calibrated reading: {device.get_calibrated_temperature_f():.1f}°F")
            else:
                print("Temperature calibration cancelled")
                
        except ValueError:
            print("Invalid temperature value")
        except KeyboardInterrupt:
            print("\nTemperature calibration cancelled")
            
        input("\nPress Enter to continue...")
        
    async def _calibrate_gravity(self, device):
        """Calibrate gravity for a device"""
        print(f"\n--- Gravity Calibration for {device.color} TILT ---")
        print(f"Current reading: {device.get_calibrated_gravity():.3f} SG")
        print("")
        print("Enter the actual specific gravity:")
        print("  - Use 1.000 for distilled water")
        print("  - Use calibrated solution value if available")
        
        try:
            actual_gravity = float(input("Actual gravity (SG) > ").strip())
            
            # Validate reasonable gravity range
            if actual_gravity < 0.990 or actual_gravity > 1.150:
                print("⚠️  Warning: Gravity value outside normal range (0.990-1.150)")
                confirm_range = input("Continue anyway? (y/N) > ").strip().lower()
                if confirm_range != 'y':
                    print("Gravity calibration cancelled")
                    input("\nPress Enter to continue...")
                    return
            
            # Calculate new offset
            current_raw_gravity = device.specific_gravity
            new_offset = actual_gravity - current_raw_gravity
            
            print(f"\nCalculating offset:")
            print(f"  Actual gravity: {actual_gravity:.3f} SG")
            print(f"  Tilt raw reading: {current_raw_gravity:.3f} SG")
            print(f"  New offset: {new_offset:+.4f} SG")
            
            confirm = input(f"\nApply this calibration? (y/N) > ").strip().lower()
            if confirm == 'y':
                device.gravity_offset = new_offset
                self.scanner.save_calibration()
                print("✅ Gravity calibration saved!")
                print(f"New calibrated reading: {device.get_calibrated_gravity():.3f} SG")
            else:
                print("Gravity calibration cancelled")
                
        except ValueError:
            print("Invalid gravity value")
        except KeyboardInterrupt:
            print("\nGravity calibration cancelled")
            
        input("\nPress Enter to continue...")
        
    def signal_handler(self, signum, frame):
        print("\nShutting down...")
        self.running = False
        
    def input_thread(self):
        """Thread to handle non-blocking keyboard input"""
        # Check if stdin is a tty
        if not sys.stdin.isatty():
            return
            
        # Set up non-blocking input
        try:
            old_settings = termios.tcgetattr(sys.stdin)
        except termios.error:
            # Not a terminal - skip input handling
            return
            
        try:
            tty.setraw(sys.stdin.fileno())
            while self.running:
                # Skip input handling during configuration mode
                if self.in_config_mode:
                    import time
                    time.sleep(0.1)
                    continue
                    
                try:
                    if select.select([sys.stdin], [], [], 0.1) == ([sys.stdin], [], []):
                        char = sys.stdin.read(1).lower()
                        if char == 'q':
                            print("\r\nQuit command received...\r\n", flush=True)
                            self.running = False
                        elif char == 'c':
                            print("\r\nConfigure command received...\r\n", flush=True)
                            self.configure_requested = True
                        elif char == 'h' or char == '?':
                            print("\r\nCommands:")
                            print("  q - Quit the monitor")
                            print("  c - Configure BrewStat.us API")
                            print("  h - Show this help\r\n", flush=True)
                except (EOFError, KeyboardInterrupt):
                    self.running = False
                    break
        finally:
            try:
                termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
            except:
                pass
                
    def create_hourly_chart(self, device, chart_type="temperature", width=24):
        """Create compact vertical bar chart for side-by-side display"""
        if device.color not in self.logger.hourly_max:
            return ["No data"]
        
        hourly_data = self.logger.hourly_max[device.color]
        
        # Get appropriate data type
        if chart_type == "temperature":
            data_keys = [key for key in hourly_data.keys() if key.endswith('-temp')]
            unit = "°F"
        else:
            data_keys = [key for key in hourly_data.keys() if key.endswith('-grav')]
            unit = ""
            
        if not data_keys:
            return ["No data yet"]
            
        # Sort keys chronologically and take last hours
        data_keys.sort()
        data_keys = data_keys[-width:]  # Last N hours
        
        values = [hourly_data[key] for key in data_keys]
        
        if not values:
            return ["No data"]
            
        lines = []
        lines.append(f"{chart_type.upper()} ({len(values)}h)")
        
        # Create vertical bar chart (6 rows high for compact display)
        chart_height = 6
        chart_width = min(width, len(values))
        
        # Calculate value range for scaling
        if len(values) > 1:
            data_min, data_max = min(values), max(values)
        else:
            data_min, data_max = values[0] * 0.98, values[0] * 1.02
            
        # Ensure we have some range
        if data_max - data_min < 0.1:
            data_center = (data_max + data_min) / 2
            data_min = data_center - 0.5
            data_max = data_center + 0.5
        
        # Create the chart from top to bottom
        for row in range(chart_height, 0, -1):
            # Calculate threshold for this row
            threshold = data_min + (data_max - data_min) * row / chart_height
            
            # Start line with value label
            if chart_type == "temperature":
                line = f"{threshold:4.0f}│"
            else:
                line = f"{threshold:4.3f}│"
            
            # Build bar section WITHOUT color first
            bars = ""
            for i in range(chart_width):
                value_index = len(values) - chart_width + i
                if value_index >= 0 and values[value_index] >= threshold:
                    bars += "█"
                else:
                    bars += " "
            
            # Apply color to entire bar section at once
            line += COLORS['yellow'] + bars + COLORS['green']
                    
            lines.append(line)
            
        # Add bottom axis
        lines.append("     └" + "─" * chart_width)
        
        # Add current value
        if values:
            if chart_type == "temperature":
                lines.append(f"Now: {values[-1]:.1f}{unit}")
            else:
                lines.append(f"Now: {values[-1]:.3f}")
            
        return lines
        
    def display_interface(self):
        # Clear screen and position cursor at top-left
        print('\033[2J\033[1;1H', end='', flush=True)
        
        # Build display as single string to avoid terminal buffering issues
        lines = []
        
        if self.scanner.devices:
            for device in self.scanner.devices.values():
                # Device status with system time
                time_str = datetime.now().strftime('%H:%M:%S')
                if device.last_seen and (datetime.now() - device.last_seen).seconds < 30:
                    status = "[ONLINE]"
                else:
                    status = "[OFFLINE]"
                    
                lines.append(f"{status} {device.color} TILT - {time_str}")
                lines.append("-" * 70)
                lines.append("")
                
                # Get current readings
                temp_f = device.get_calibrated_temperature_f()
                temp_c = device.get_calibrated_temperature_c()
                gravity = device.get_calibrated_gravity()
                
                # Generate actual ASCII numbers from sensor readings
                gravity_lines = self.create_large_number(gravity, 3)
                temp_lines = self.create_large_number(temp_f, 1)
                
                # Define exact box widths - same for both
                GRAVITY_BOX_WIDTH = 33  # Inner width for gravity box
                TEMP_BOX_WIDTH = 33     # Inner width for temperature box (same as gravity)
                
                # Create box borders
                lines.append("┌" + "─" * GRAVITY_BOX_WIDTH + "┐  ┌" + "─" * TEMP_BOX_WIDTH + "┐")
                
                # Header row with centered text
                gravity_header = "GRAVITY"
                temp_header = "TEMPERATURE"
                
                gravity_header_padding = (GRAVITY_BOX_WIDTH - len(gravity_header)) // 2
                temp_header_padding = (TEMP_BOX_WIDTH - len(temp_header)) // 2
                
                gravity_header_line = " " * gravity_header_padding + gravity_header + " " * (GRAVITY_BOX_WIDTH - gravity_header_padding - len(gravity_header))
                temp_header_line = " " * temp_header_padding + temp_header + " " * (TEMP_BOX_WIDTH - temp_header_padding - len(temp_header))
                
                lines.append("│" + gravity_header_line + "│  │" + temp_header_line + "│")
                lines.append("│" + " " * GRAVITY_BOX_WIDTH + "│  │" + " " * TEMP_BOX_WIDTH + "│")
                
                # Display ASCII art (7 rows)
                for i in range(7):
                    # Get the ASCII line without colors
                    gravity_line = gravity_lines[i] if i < len(gravity_lines) else ""
                    temp_line = temp_lines[i] if i < len(temp_lines) else ""
                    
                    # Calculate actual display width (no ANSI codes in these yet)
                    gravity_line_width = len(gravity_line)
                    temp_line_width = len(temp_line)
                    
                    # Center the content in the box
                    gravity_padding_left = (GRAVITY_BOX_WIDTH - gravity_line_width) // 2
                    gravity_padding_right = GRAVITY_BOX_WIDTH - gravity_padding_left - gravity_line_width
                    
                    temp_padding_left = (TEMP_BOX_WIDTH - temp_line_width) // 2
                    temp_padding_right = TEMP_BOX_WIDTH - temp_padding_left - temp_line_width
                    
                    # Build the padded content (still no colors)
                    gravity_padded = " " * gravity_padding_left + gravity_line + " " * gravity_padding_right
                    temp_padded = " " * temp_padding_left + temp_line + " " * temp_padding_right
                    
                    # Apply colors to the entire padded content
                    gravity_colored = COLORS['yellow'] + gravity_padded + COLORS['green']
                    temp_colored = COLORS['yellow'] + temp_padded + COLORS['green']
                    
                    lines.append("│" + gravity_colored + "│  │" + temp_colored + "│")
                
                # Empty row before values
                lines.append("│" + " " * GRAVITY_BOX_WIDTH + "│  │" + " " * TEMP_BOX_WIDTH + "│")
                
                # Actual values in parentheses centered in boxes
                sg_text = f"({gravity:.3f} SG)"
                temp_text = f"({temp_f:.1f}°F / {temp_c:.1f}°C)"
                
                sg_padding_left = (GRAVITY_BOX_WIDTH - len(sg_text)) // 2
                sg_padding_right = GRAVITY_BOX_WIDTH - sg_padding_left - len(sg_text)
                
                temp_text_padding_left = (TEMP_BOX_WIDTH - len(temp_text)) // 2
                temp_text_padding_right = TEMP_BOX_WIDTH - temp_text_padding_left - len(temp_text)
                
                sg_centered = " " * sg_padding_left + sg_text + " " * sg_padding_right
                temp_text_centered = " " * temp_text_padding_left + temp_text + " " * temp_text_padding_right
                
                lines.append("│" + sg_centered + "│  │" + temp_text_centered + "│")
                
                # Bottom border
                lines.append("└" + "─" * GRAVITY_BOX_WIDTH + "┘  └" + "─" * TEMP_BOX_WIDTH + "┘")
                lines.append("")
                
                # Status info
                if device.last_seen:
                    last_update = device.last_seen.strftime('%H:%M:%S')
                else:
                    last_update = "Never"
                lines.append(f"Signal: {device.rssi}dBm | Last Update: {last_update}")
                lines.append("")
                
                # History charts side-by-side
                if device.color in self.logger.hourly_max and self.logger.hourly_max[device.color]:
                    lines.append("HISTORY:")
                    grav_chart = self.create_hourly_chart(device, "gravity", 20)
                    temp_chart = self.create_hourly_chart(device, "temperature", 20)
                    
                    max_chart_lines = max(len(grav_chart), len(temp_chart))
                    for i in range(max_chart_lines):
                        grav_line = grav_chart[i] if i < len(grav_chart) else ""
                        temp_line = temp_chart[i] if i < len(temp_chart) else ""
                        # Strip ANSI codes for length calculation
                        grav_line_clean = self.strip_ansi(grav_line)
                        padding = 35 - len(grav_line_clean)
                        lines.append(grav_line + (' ' * max(0, padding)) + temp_line)
                    lines.append("")
                
                lines.append("-" * 70)
                lines.append("")
        else:
            lines.append("┌" + "─" * 68 + "┐")
            lines.append("│" + " " * 21 + "NO TILT DEVICES DETECTED" + " " * 22 + "│")
            lines.append("│" + " " * 68 + "│")
            lines.append("│  Make sure your Tilt is:" + " " * 41 + "│")
            lines.append("│  - Powered on (LED should blink)" + " " * 33 + "│")
            lines.append("│  - Within 30 feet of this device" + " " * 32 + "│")
            lines.append("│  - Not in sleep mode (shake gently to wake)" + " " * 21 + "│")
            lines.append("│" + " " * 68 + "│")
            lines.append("└" + "─" * 68 + "┘")
            lines.append("")
        
        # Status line
        brewstat_status = "ENABLED" if self.brewstat.enabled else "DISABLED"
        if self.brewstat.enabled and self.brewstat.last_upload:
            last_upload = max(self.brewstat.last_upload.values()).strftime("%H:%M:%S")
            brewstat_status += f" ({last_upload})"
        
        tidbyt_status = ""
        if self.tidbyt:
            tidbyt_status = "ENABLED" if self.tidbyt.enabled else "DISABLED"
            if self.tidbyt.enabled and self.tidbyt.last_push:
                last_push = max(self.tidbyt.last_push.values()).strftime("%H:%M:%S")
                tidbyt_status += f" ({last_push})"
            tidbyt_status = f" | Tidbyt: {tidbyt_status}"
        
        total_readings = sum(len(history) for history in self.logger.history.values())
        lines.append(f"BrewStat.us: {brewstat_status}{tidbyt_status} | CSV: {total_readings} readings | Press: 'q'=quit 'c'=config")
        
        # Print everything as one block with proper line endings for raw mode
        print('\r\n'.join(lines), flush=True)
        
    async def scan_loop(self):
        while self.running:
            try:
                await self.scanner.scan(5)
                
                # Log data and upload
                for device in self.scanner.devices.values():
                    self.logger.log_reading(device)
                    if self.brewstat.enabled:
                        await self.brewstat.upload_reading(device)
                    if self.tidbyt and self.tidbyt.enabled:
                        await self.tidbyt.push_to_tidbyt(device)
                        
                await asyncio.sleep(3)
            except Exception as e:
                await asyncio.sleep(5)
                
    async def display_loop(self):
        while self.running:
            # Handle configuration request
            if self.configure_requested:
                self.configure_requested = False
                
                # Stop the input thread temporarily by setting a flag
                self.in_config_mode = True
                
                # Clear screen and fully restore normal terminal for configuration
                print(COLORS['clear_screen'], end='', flush=True)
                
                # Get and restore normal terminal settings
                try:
                    import subprocess
                    subprocess.run(['stty', 'sane'], check=False)
                except:
                    pass
                
                try:
                    # Run configuration with normal terminal behavior
                    print(COLORS['black_bg'] + COLORS['green'])
                    print(COLORS['bold_white'] + "=" * 60 + COLORS['green'])
                    print("              BREWSTAT.US CONFIGURATION")
                    print(COLORS['bold_white'] + "=" * 60 + COLORS['green'])
                    print("")
                    
                    if self.brewstat.api_key:
                        masked_key = f"{self.brewstat.api_key[:8]}...{self.brewstat.api_key[-4:]}" if len(self.brewstat.api_key) > 12 else self.brewstat.api_key
                        print(f"Current API Key: {masked_key}")
                    else:
                        print("Current API Key: [NOT SET]")
                        
                    print(f"Current Upload Interval: {self.brewstat.upload_interval_seconds} seconds ({self.brewstat.upload_interval_seconds//60} minutes)")
                    print("")
                    
                    print(COLORS['bold_white'] + "=" * 60 + COLORS['green'])
                    print("1. Change API Key")
                    print("2. Change Upload Interval") 
                    print("3. Calibrate Devices")
                    if self.tidbyt:
                        tidbyt_status = "ENABLED" if self.tidbyt.enabled else "DISABLED"
                        print(f"4. Tidbyt Integration ({tidbyt_status})")
                        print("5. Disable BrewStat.us")
                        print("6. Return to monitor")
                    else:
                        print("4. Disable BrewStat.us")
                        print("5. Return to monitor")
                    print(COLORS['bold_white'] + "=" * 60 + COLORS['green'])
                    print("")  # Extra line before prompt
                    
                    try:
                        # Set up signal handler for Ctrl+C during config
                        def config_signal_handler(signum, frame):
                            print("\nConfiguration cancelled")
                            return
                            
                        original_handler = signal.signal(signal.SIGINT, config_signal_handler)
                        
                        try:
                            max_choice = "6" if self.tidbyt else "5"
                            choice = input(f"Select option (1-{max_choice}) > ").strip()
                            
                            if choice == '1':
                                print("\nEnter your BrewStat.us API key:")
                                print("(Get your key from https://www.brewstat.us)")
                                new_key = input("API Key > ").strip()
                                
                                if new_key:
                                    self.brewstat.api_key = new_key
                                    self.brewstat.enabled = True
                                    self.brewstat._save_config(api_key=new_key)
                                    print("✅ BrewStat.us API key updated!")
                                else:
                                    print("API key unchanged")
                                    
                            elif choice == '2':
                                print(f"\nCurrent interval: {self.brewstat.upload_interval_seconds} seconds")
                                try:
                                    minutes = int(input("New interval in minutes (1-60) > ").strip())
                                    if 1 <= minutes <= 60:
                                        self.brewstat.upload_interval_seconds = minutes * 60
                                        self.brewstat._save_config(upload_interval_seconds=self.brewstat.upload_interval_seconds)
                                        print(f"✅ Upload interval set to {minutes} minutes")
                                    else:
                                        print("Invalid interval. Must be 1-60 minutes.")
                                except ValueError:
                                    print("Invalid input. Please enter a number.")
                                    
                            elif choice == '3':
                                # Calibration menu
                                await self._handle_calibration_menu()
                                    
                            elif choice == '4':
                                if self.tidbyt:
                                    # Tidbyt configuration
                                    from tidbyt_integration import configure_interactive
                                    configure_interactive()
                                    # Reload Tidbyt configuration after interactive setup
                                    self.tidbyt._load_config()
                                    print(f"✅ Tidbyt configuration reloaded. Status: {'ENABLED' if self.tidbyt.enabled else 'DISABLED'}")
                                else:
                                    # Disable BrewStat.us
                                    confirm = input("Disable BrewStat.us uploads? (y/N) > ").strip().lower()
                                    if confirm == 'y':
                                        self.brewstat.enabled = False
                                        self.brewstat._save_config(enabled=False)
                                        print("✅ BrewStat.us uploads disabled")
                                    else:
                                        print("BrewStat.us remains enabled")
                                        
                            elif choice == '5':
                                if self.tidbyt:
                                    # Disable BrewStat.us when Tidbyt is available
                                    confirm = input("Disable BrewStat.us uploads? (y/N) > ").strip().lower()
                                    if confirm == 'y':
                                        self.brewstat.enabled = False
                                        self.brewstat._save_config(enabled=False)
                                        print("✅ BrewStat.us uploads disabled")
                                    else:
                                        print("BrewStat.us remains enabled")
                                else:
                                    # Return to monitor
                                    print("Returning to monitor...")
                                    
                            elif choice == '6' and self.tidbyt:
                                print("Returning to monitor...")
                            else:
                                print("Invalid choice")
                                
                            input("\nPress Enter to continue...")
                            
                        finally:
                            # Restore original signal handler
                            signal.signal(signal.SIGINT, original_handler)
                        
                    except (KeyboardInterrupt, EOFError):
                        print("\nConfiguration cancelled")
                        
                except Exception as e:
                    print(f"Configuration error: {e}")
                    
                finally:
                    # Reset the configuration mode flag
                    self.in_config_mode = False
                    
            else:
                self.display_interface()
                
            await asyncio.sleep(3)
            
    async def run(self):
        signal.signal(signal.SIGINT, self.signal_handler)
        
        print(COLORS['black_bg'] + COLORS['green'] + "Starting Easy History Monitor...")
        print("Loading calibration...")
        
        self.scanner.load_calibration()
        
        print("Performing initial scan...")
        await self.scanner.scan(10)
        
        print(f"Found {len(self.scanner.devices)} device(s)")
        print()
        print(COLORS['bold_white'] + "CONTROLS:" + COLORS['green'])
        print("- Press 'q' to quit (no Enter needed)")
        print("- Press 'c' to configure BrewStat.us")
        print("- Use Ctrl+C for emergency quit")
        print()
        print("Starting monitor in 3 seconds...")
        await asyncio.sleep(3)
        
        # Start input thread
        input_thread = threading.Thread(target=self.input_thread, daemon=True)
        input_thread.start()
        
        try:
            await asyncio.gather(
                self.scan_loop(),
                self.display_loop()
            )
        except KeyboardInterrupt:
            pass
        
        print(COLORS['reset'] + "\nEasy History Monitor stopped.")

def main():
    parser = argparse.ArgumentParser(description='Tilt Hydrometer Monitor with ASCII Display')
    parser.add_argument('--tidbyt', action='store_true', 
                       help='Enable Tidbyt integration (requires requirements-tidbyt.txt)')
    args = parser.parse_args()
    
    monitor = EasyHistoryMonitor(enable_tidbyt=args.tidbyt)
    try:
        asyncio.run(monitor.run())
    except KeyboardInterrupt:
        print("\nExiting...")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()