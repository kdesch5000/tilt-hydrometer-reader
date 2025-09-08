#!/usr/bin/env python3
"""
Tidbyt Integration for Tilt Hydrometer Reader
Pushes formatted Tilt data to Tidbyt displays via Push API
"""

import json
import requests
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Optional
from dataclasses import dataclass

from tilt_scanner import TiltDevice


@dataclass
class TidbytConfig:
    device_id: str
    api_key: str
    installation_id: str
    enabled: bool = False
    push_interval_seconds: int = 300  # 5 minutes default
    

class TidbytPusher:
    def __init__(self):
        self.config = None
        self.last_push = {}
        self.enabled = False
        self._load_config()
    
    def _load_config(self):
        """Load Tidbyt configuration from tilt_config.json"""
        try:
            with open('tilt_config.json', 'r') as f:
                config = json.load(f)
                tidbyt_config = config.get('tidbyt', {})
                
                if tidbyt_config and all(key in tidbyt_config for key in ['device_id', 'api_key', 'installation_id']):
                    self.config = TidbytConfig(
                        device_id=tidbyt_config['device_id'],
                        api_key=tidbyt_config['api_key'],
                        installation_id=tidbyt_config['installation_id'],
                        enabled=tidbyt_config.get('enabled', False),
                        push_interval_seconds=tidbyt_config.get('push_interval_seconds', 300)
                    )
                    self.enabled = self.config.enabled
        except (FileNotFoundError, json.JSONDecodeError):
            pass
    
    def _save_config(self):
        """Save Tidbyt configuration to tilt_config.json"""
        try:
            with open('tilt_config.json', 'r') as f:
                config = json.load(f)
        except FileNotFoundError:
            config = {}
        
        if self.config:
            config['tidbyt'] = {
                'device_id': self.config.device_id,
                'api_key': self.config.api_key,
                'installation_id': self.config.installation_id,
                'enabled': self.config.enabled,
                'push_interval_seconds': self.config.push_interval_seconds
            }
        else:
            config.pop('tidbyt', None)
        
        with open('tilt_config.json', 'w') as f:
            json.dump(config, f, indent=2)
    
    def configure_tidbyt(self, device_id: str, api_key: str, installation_id: str, 
                        enabled: bool = True, push_interval_seconds: int = 300):
        """Configure Tidbyt integration settings"""
        self.config = TidbytConfig(
            device_id=device_id,
            api_key=api_key,
            installation_id=installation_id,
            enabled=enabled,
            push_interval_seconds=push_interval_seconds
        )
        self.enabled = enabled
        self._save_config()
    
    def disable_tidbyt(self):
        """Disable Tidbyt integration"""
        if self.config:
            self.config.enabled = False
            self.enabled = False
            self._save_config()
    
    def should_push(self, device_color: str) -> bool:
        """Check if enough time has passed to push new data"""
        if not self.enabled or not self.config:
            return False
        
        last = self.last_push.get(device_color)
        if not last:
            return True
        
        return (datetime.now() - last).total_seconds() > self.config.push_interval_seconds
    
    def _create_webp_payload(self, device: TiltDevice) -> bytes:
        """Create WebP image for Tidbyt display (64x32 pixels)"""
        try:
            from PIL import Image, ImageDraw, ImageFont
            import io
            
            # Create 64x32 image with black background
            img = Image.new('RGB', (64, 32), color=(0, 0, 0))
            draw = ImageDraw.Draw(img)
            
            # Color mapping for Tilt devices
            color_map = {
                'RED': (255, 68, 68),
                'GREEN': (68, 255, 68),
                'BLACK': (200, 200, 200),
                'PURPLE': (204, 68, 204),
                'ORANGE': (255, 136, 68),
                'BLUE': (68, 68, 255),
                'YELLOW': (255, 255, 68),
                'PINK': (255, 136, 204)
            }
            
            device_color = color_map.get(device.color, (255, 255, 255))
            temp_f = device.get_calibrated_temperature_f()
            gravity = device.get_calibrated_gravity()
            
            # Try to use default font, and create a smaller font for units
            try:
                font_small = ImageFont.load_default()
                font_large = ImageFont.load_default()
                # Try to create a smaller font (75% of default size for units)
                try:
                    font_tiny = ImageFont.load_default().font_variant(size=int(11 * 0.75))
                except:
                    font_tiny = font_small  # Fallback to small if variant doesn't work
            except:
                font_small = None
                font_large = None  
                font_tiny = None
            
            # Draw device name higher up with more spacing (moved up 3 rows)
            device_text = f"{device.color} TILT"
            text_width = draw.textlength(device_text, font=font_small) if font_small else len(device_text) * 6
            draw.text(((64 - text_width) // 2, 1), device_text, fill=device_color, font=font_small)
            
            # Draw two boxes side by side (moved down to create space)
            # Left box for Gravity (32x20 pixels)
            draw.rectangle((1, 13, 31, 29), outline=(100, 100, 100), width=1)
            
            # Right box for Temperature (32x20 pixels) 
            draw.rectangle((33, 13, 62, 29), outline=(100, 100, 100), width=1)
            
            # Gravity box content - value moved up 2 rows, units smaller on line 3
            gravity_str = f"{gravity:.3f}"
            # Center gravity value in left box (moved up 2 rows)
            grav_width = draw.textlength(gravity_str, font=font_small) if font_small else len(gravity_str) * 6
            draw.text((16 - grav_width // 2, 15), gravity_str, fill=(255, 255, 255), font=font_small)
            # Units on line 3 with smaller font (25% smaller)
            sg_width = draw.textlength("SG", font=font_tiny) if font_tiny else 12
            draw.text((16 - sg_width // 2, 24), "SG", fill=(204, 204, 204), font=font_tiny)
            
            # Temperature box content - value moved up 2 rows, units smaller on line 3
            temp_str = f"{temp_f:.1f}"
            # Center temperature value in right box (moved up 2 rows)
            temp_width = draw.textlength(temp_str, font=font_small) if font_small else len(temp_str) * 6
            draw.text((48 - temp_width // 2, 15), temp_str, fill=(255, 170, 68), font=font_small)
            # Units on line 3 with smaller font (25% smaller)
            f_width = draw.textlength("°F", font=font_tiny) if font_tiny else 12
            draw.text((48 - f_width // 2, 24), "°F", fill=(204, 204, 204), font=font_tiny)
            
            # Draw status bar at bottom
            draw.rectangle((0, 31, 63, 31), fill=device_color)
            
            # Convert to WebP
            img_buffer = io.BytesIO()
            img.save(img_buffer, format='WebP', quality=85)
            return img_buffer.getvalue()
            
        except ImportError:
            # Fallback: return simple JSON if PIL not available
            display_data = {
                "color": device.color,
                "temperature": f"{temp_f:.1f}°F",
                "gravity": f"{gravity:.3f}",
                "timestamp": datetime.now().strftime("%H:%M")
            }
            return json.dumps(display_data).encode('utf-8')
    
    async def push_to_tidbyt(self, device: TiltDevice) -> bool:
        """Push Tilt data to Tidbyt device"""
        if not self.should_push(device.color):
            return False
        
        try:
            # Tidbyt Push API endpoint
            url = f"https://api.tidbyt.com/v0/devices/{self.config.device_id}/push"
            
            headers = {
                'Authorization': f'Bearer {self.config.api_key}',
            }
            
            # Create display payload with consistent Installation ID
            image_data = self._create_webp_payload(device)
            
            # Use alphanumeric installation ID (no hyphens allowed by Tidbyt API)
            # Format: tilthydrometer{color}v2024
            consistent_id = f"tilthydrometer{device.color.lower()}v2024"
            
            # If we have binary WebP data, encode it properly
            if isinstance(image_data, bytes):
                import base64
                image_b64 = base64.b64encode(image_data).decode('utf-8')
                headers['Content-Type'] = 'application/json'
                payload = {
                    'installationID': consistent_id,
                    'image': image_b64,
                    'background': False
                }
            else:
                # Fallback JSON data
                headers['Content-Type'] = 'application/json'
                payload = {
                    'installationID': consistent_id,
                    'image': image_data.decode('utf-8') if isinstance(image_data, bytes) else image_data,
                    'background': False
                }
            
            response = requests.post(url, json=payload, headers=headers, timeout=10)
            
            if response.status_code == 200:
                self.last_push[device.color] = datetime.now()
                return True
            else:
                print(f"Tidbyt push failed: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            print(f"Tidbyt push error: {e}")
            return False
    
    def get_status(self) -> Dict:
        """Get current Tidbyt integration status"""
        status = {
            'enabled': self.enabled,
            'configured': self.config is not None
        }
        
        if self.config:
            status.update({
                'device_id': self.config.device_id,
                'push_interval': self.config.push_interval_seconds,
                'last_pushes': {}
            })
            
            for color, timestamp in self.last_push.items():
                status['last_pushes'][color] = timestamp.isoformat()
        
        return status


def configure_interactive():
    """Interactive configuration for Tidbyt integration"""
    pusher = TidbytPusher()
    
    print("\n" + "=" * 60)
    print("              TIDBYT INTEGRATION SETUP")
    print("=" * 60)
    print()
    print("To set up Tidbyt integration, you need:")
    print("1. Tidbyt Device ID (from Tidbyt mobile app)")
    print("2. Tidbyt API Key (from https://tidbyt.dev)")
    print("3. Installation ID (generated when you install the app)")
    print()
    
    if pusher.config:
        print("Current Configuration:")
        print(f"  Device ID: {pusher.config.device_id}")
        print(f"  API Key: {pusher.config.api_key[:8]}...")
        print(f"  Installation ID: {pusher.config.installation_id}")
        print(f"  Enabled: {pusher.config.enabled}")
        print(f"  Push Interval: {pusher.config.push_interval_seconds}s")
        print()
    
    print("Options:")
    print("1. Configure Tidbyt integration")
    print("2. Change push interval")
    print("3. Disable Tidbyt integration")
    print("4. Return")
    print()
    
    try:
        choice = input("Select option (1-4) > ").strip()
        
        if choice == '1':
            print("\nEnter your Tidbyt configuration:")
            device_id = input("Device ID > ").strip()
            api_key = input("API Key > ").strip()
            installation_id = input("Installation ID (or press Enter for auto-generate) > ").strip()
            
            if not installation_id:
                # Generate a unique installation ID
                import uuid
                installation_id = f"tilt-{uuid.uuid4().hex[:8]}"
                print(f"Generated Installation ID: {installation_id}")
            
            if device_id and api_key:
                pusher.configure_tidbyt(device_id, api_key, installation_id)
                print("✅ Tidbyt integration configured!")
            else:
                print("❌ Device ID and API Key are required")
        
        elif choice == '2':
            if not pusher.config:
                print("❌ Tidbyt not configured yet")
                return
            
            try:
                interval = int(input(f"Push interval in seconds (current: {pusher.config.push_interval_seconds}) > "))
                if interval > 0:
                    pusher.config.push_interval_seconds = interval
                    pusher._save_config()
                    print(f"✅ Push interval updated to {interval} seconds")
                else:
                    print("❌ Interval must be positive")
            except ValueError:
                print("❌ Invalid number")
        
        elif choice == '3':
            if pusher.config:
                confirm = input("Disable Tidbyt integration? (y/N) > ").strip().lower()
                if confirm == 'y':
                    pusher.disable_tidbyt()
                    print("✅ Tidbyt integration disabled")
                else:
                    print("Not disabled")
            else:
                print("Tidbyt integration not configured")
        
        elif choice == '4':
            return
        else:
            print("Invalid choice")
    
    except KeyboardInterrupt:
        print("\nConfiguration cancelled")
    
    input("\nPress Enter to continue...")


if __name__ == "__main__":
    configure_interactive()