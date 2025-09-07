#!/usr/bin/env python3
"""
Tilt Hydrometer Terminal Monitor
Real-time display with ASCII art interface, color scheme, and historical charts
"""

import asyncio
import json
import csv
import os
import time
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass
from pathlib import Path

from rich.console import Console
from rich.layout import Layout
from rich.panel import Panel
from rich.text import Text
from rich.table import Table
from rich.progress import Progress, BarColumn, TextColumn
from rich.live import Live
from rich.align import Align

from tilt_scanner import TiltScanner, TiltDevice

@dataclass
class DataPoint:
    """Single data point for historical tracking"""
    timestamp: datetime
    temperature_f: float
    gravity: float
    rssi: int

class TiltDataLogger:
    """Handles data logging and historical data management"""
    
    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        self.history: Dict[str, List[DataPoint]] = {}
        
    def log_reading(self, device: TiltDevice):
        """Log a reading to CSV and memory"""
        timestamp = datetime.now()
        
        # Add to memory history
        if device.color not in self.history:
            self.history[device.color] = []
            
        data_point = DataPoint(
            timestamp=timestamp,
            temperature_f=device.get_calibrated_temperature_f(),
            gravity=device.get_calibrated_gravity(),
            rssi=device.rssi
        )
        
        self.history[device.color].append(data_point)
        
        # Keep only 14 days of data (15 min intervals = 1344 points max)
        cutoff = timestamp - timedelta(days=14)
        self.history[device.color] = [
            point for point in self.history[device.color] 
            if point.timestamp > cutoff
        ]
        
        # Save to CSV
        self._save_to_csv(device.color, data_point)
        
    def _save_to_csv(self, color: str, data_point: DataPoint):
        """Save data point to CSV file"""
        csv_file = self.data_dir / f"tilt_{color.lower()}_{data_point.timestamp.strftime('%Y-%m')}.csv"
        
        # Check if file exists to write header
        write_header = not csv_file.exists()
        
        with open(csv_file, 'a', newline='') as f:
            writer = csv.writer(f)
            if write_header:
                writer.writerow(['timestamp', 'temperature_f', 'temperature_c', 'gravity', 'rssi'])
            
            writer.writerow([
                data_point.timestamp.isoformat(),
                data_point.temperature_f,
                (data_point.temperature_f - 32) * 5/9,  # Celsius
                data_point.gravity,
                data_point.rssi
            ])

class BrewStatLogger:
    """Handles logging to BrewStat.us API"""
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key
        self.last_upload = {}
        self.upload_interval = timedelta(minutes=15)
        
    def should_upload(self, color: str) -> bool:
        """Check if enough time has passed to upload"""
        if not self.api_key:
            return False
            
        last = self.last_upload.get(color)
        if not last:
            return True
            
        return datetime.now() - last > self.upload_interval
        
    async def upload_reading(self, device: TiltDevice):
        """Upload reading to BrewStat.us"""
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
            else:
                return False
                
        except Exception:
            return False

class TiltMonitorApp:
    """Main terminal monitoring application"""
    
    def __init__(self):
        self.console = Console()
        self.scanner = TiltScanner()
        self.logger = TiltDataLogger()
        self.brewstat = BrewStatLogger()  # Will load API key from config
        self.running = False
        self.last_scan = None
        
        # Load configuration
        self._load_config()
        
    def _load_config(self):
        """Load configuration from config file"""
        try:
            with open('tilt_config.json', 'r') as f:
                config = json.load(f)
                self.brewstat.api_key = config.get('brewstat_api_key')
        except FileNotFoundError:
            # Create default config
            config = {
                'brewstat_api_key': '',
                'temperature_range': {'min': 60, 'max': 80},
                'gravity_range': {'min': 0.990, 'max': 1.100}
            }
            with open('tilt_config.json', 'w') as f:
                json.dump(config, f, indent=2)
                
    def create_header(self) -> Panel:
        """Create header panel"""
        title = Text("🍺 TILT HYDROMETER MONITOR 🍺", style="bold white")
        return Panel(Align.center(title), style="bold white")
        
    def create_device_panel(self, device: TiltDevice) -> Panel:
        """Create panel for a single device"""
        # Device info
        status = "●CONNECTED" if device.last_seen and \
                 (datetime.now() - device.last_seen).seconds < 30 else "●DISCONNECTED"
        status_style = "bold green" if "CONNECTED" in status else "bold red"
        
        last_update = device.last_seen.strftime("%H:%M:%S") if device.last_seen else "Never"
        
        # Create table for device info
        table = Table.grid(padding=1)
        table.add_column(style="green")
        table.add_column(style="green")
        
        table.add_row(f"Device: {device.color} TILT", f"Status: {status}", style=status_style)
        table.add_row(f"Last Update: {last_update}", f"Signal: {device.rssi} dBm")
        
        return Panel(table, title=f"{device.color} TILT", style="green")
        
    def create_readings_panel(self, device: TiltDevice) -> Panel:
        """Create panel showing current readings"""
        table = Table.grid(padding=1)
        table.add_column(justify="center", style="bold white")
        table.add_column(justify="center", style="bold white")
        
        # Temperature section
        temp_f = device.get_calibrated_temperature_f()
        temp_c = device.get_calibrated_temperature_c()
        temp_text = f"{temp_f:.1f}°F\n({temp_c:.1f}°C)"
        
        # Gravity section  
        gravity = device.get_calibrated_gravity()
        gravity_text = f"{gravity:.3f}"
        
        table.add_row("TEMPERATURE", "SPECIFIC GRAVITY")
        table.add_row(temp_text, gravity_text)
        
        # Progress bars (simplified for now)
        temp_bar = "█" * int((temp_f - 60) / 20 * 20) + "░" * (20 - int((temp_f - 60) / 20 * 20))
        gravity_progress = int((gravity - 0.990) / 0.110 * 20)
        gravity_bar = "█" * gravity_progress + "░" * (20 - gravity_progress)
        
        table.add_row(f"[{temp_bar[:20]}]", f"[{gravity_bar[:20]}]")
        table.add_row(f"Min: 60°F  Max: 80°F", f"Range: 0.990 - 1.100")
        
        return Panel(table, style="green")
        
    def create_history_chart(self, device: TiltDevice, chart_type: str = "temperature") -> Panel:
        """Create ASCII chart for historical data"""
        if device.color not in self.logger.history or not self.logger.history[device.color]:
            return Panel("No historical data available", title=f"{chart_type.upper()} HISTORY (14 days)")
        
        data_points = self.logger.history[device.color][-96:]  # Last 24 hours worth (15min intervals)
        
        # Simple vertical bar chart
        chart_lines = []
        if chart_type == "temperature":
            values = [p.temperature_f for p in data_points]
            min_val, max_val = 60, 80
            unit = "°F"
        else:  # gravity
            values = [p.gravity for p in data_points]
            min_val, max_val = 0.990, 1.100
            unit = ""
            
        if not values:
            return Panel("No data", title=f"{chart_type.upper()} HISTORY")
            
        # Create 5-row chart
        chart_height = 5
        for row in range(chart_height, 0, -1):
            line = f"{max_val - (max_val - min_val) * (chart_height - row) / chart_height:.1f}{unit}│"
            
            # Add bars for recent values (last 24 readings)
            for i, value in enumerate(values[-24:]):
                normalized = (value - min_val) / (max_val - min_val)
                if normalized * chart_height >= row - 1:
                    line += "█"
                else:
                    line += " "
                    
            chart_lines.append(line)
            
        # Add time axis
        chart_lines.append(" " * 6 + "└" + "─" * 24)
        chart_lines.append(" " * 7 + "24h  18h  12h   6h   0h")
        
        chart_text = "\n".join(chart_lines)
        
        return Panel(chart_text, title=f"{chart_type.upper()} HISTORY (24h)", style="green")
        
    def create_status_panel(self) -> Panel:
        """Create status panel for cloud and logging info"""
        table = Table.grid(padding=1)
        table.add_column(style="green")
        table.add_column(style="green")
        
        # BrewStat status
        brewstat_status = "●CONNECTED" if self.brewstat.api_key else "●DISABLED"
        brewstat_style = "green" if self.brewstat.api_key else "yellow"
        
        last_upload = "Never"
        if self.brewstat.last_upload:
            last_upload = max(self.brewstat.last_upload.values()).strftime("%H:%M:%S")
            
        table.add_row(f"Cloud Status: BrewStat.us {brewstat_status}", 
                     f"Last Upload: {last_upload}", style=brewstat_style)
        
        # Local logging status
        log_count = sum(len(history) for history in self.logger.history.values())
        table.add_row(f"Local Log: {log_count:,} readings", 
                     f"Storage: data/")
        
        return Panel(table, style="green")
        
    def create_layout(self) -> Layout:
        """Create the main layout"""
        layout = Layout()
        
        layout.split_column(
            Layout(name="header", size=3),
            Layout(name="main"),
            Layout(name="status", size=4),
            Layout(name="footer", size=3)
        )
        
        # Get first device for now (will expand for multi-device)
        device = None
        if self.scanner.devices:
            device = list(self.scanner.devices.values())[0]
            
        # Header
        layout["header"].update(self.create_header())
        
        if device:
            # Main content
            layout["main"].split_row(
                Layout(name="left"),
                Layout(name="right")
            )
            
            layout["left"].split_column(
                Layout(self.create_device_panel(device), size=4),
                Layout(self.create_readings_panel(device), size=8),
            )
            
            layout["right"].split_column(
                Layout(self.create_history_chart(device, "temperature"), size=6),
                Layout(self.create_history_chart(device, "gravity"), size=6),
            )
            
            # Status
            layout["status"].update(self.create_status_panel())
            
        else:
            layout["main"].update(Panel("No Tilt devices detected.\nMake sure your Tilt is powered on and nearby.", 
                                       title="Scanning...", style="yellow"))
            layout["status"].update(Panel("Waiting for devices...", style="yellow"))
        
        # Footer with controls
        footer_text = "Press 'q' to quit | 'r' to reset | 's' to save | 'c' to configure"
        layout["footer"].update(Panel(Align.center(footer_text), style="green"))
        
        return layout
        
    async def scan_devices(self):
        """Continuously scan for devices"""
        while self.running:
            try:
                await self.scanner.scan(5)  # 5-second scans
                self.last_scan = datetime.now()
                
                # Log data for each device
                for device in self.scanner.devices.values():
                    self.logger.log_reading(device)
                    
                    # Upload to BrewStat if configured
                    if self.brewstat.api_key:
                        await self.brewstat.upload_reading(device)
                        
            except Exception as e:
                pass  # Handle errors silently in background
                
    async def run(self):
        """Run the main application"""
        self.running = True
        
        # Load existing calibration
        self.scanner.load_calibration()
        
        # Start background scanning
        scan_task = asyncio.create_task(self.scan_devices())
        
        try:
            with Live(self.create_layout(), refresh_per_second=1, screen=True) as live:
                while self.running:
                    live.update(self.create_layout())
                    await asyncio.sleep(1)
                    
        except KeyboardInterrupt:
            pass
        finally:
            self.running = False
            scan_task.cancel()
            try:
                await scan_task
            except asyncio.CancelledError:
                pass

async def main():
    """Main entry point"""
    app = TiltMonitorApp()
    await app.run()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nTilt Monitor stopped.")
    except Exception as e:
        print(f"Error: {e}")
        print("Make sure to run with: sudo python3 tilt_monitor.py")