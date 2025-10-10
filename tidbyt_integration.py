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
            
            # Color mapping for Tilt devices - BRIGHTER colors
            color_map = {
                'RED': (255, 100, 100),      # Brighter red
                'GREEN': (100, 255, 100),
                'BLACK': (220, 220, 220),
                'PURPLE': (220, 100, 220),
                'ORANGE': (255, 150, 100),
                'BLUE': (100, 100, 255),
                'YELLOW': (255, 255, 100),
                'PINK': (255, 150, 220)
            }
            
            device_color = color_map.get(device.color, (255, 255, 255))
            temp_f = device.get_calibrated_temperature_f()
            gravity = device.get_calibrated_gravity()
            
            # Try to use a proper sans-serif TrueType font for ALL text
            try:
                # Try common sans-serif fonts available on Linux systems
                font_paths = [
                    '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
                    '/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf',
                    '/usr/share/fonts/TTF/DejaVuSans.ttf',
                    '/System/Library/Fonts/Helvetica.ttc',  # macOS
                ]

                font_header = None
                font_numbers = None

                for font_path in font_paths:
                    try:
                        font_header = ImageFont.truetype(font_path, size=8)   # Header text
                        font_numbers = ImageFont.truetype(font_path, size=10) # Numbers (slightly larger)
                        break
                    except:
                        continue

                # If no TrueType font found, fall back to default
                if not font_header:
                    font_header = ImageFont.load_default()
                if not font_numbers:
                    font_numbers = ImageFont.load_default()

            except:
                font_header = None
                font_numbers = None
            
            # Draw device name - Use device color, NO ANTIALIASING
            device_text = f"{device.color} TILT"

            # Render text on 1-bit image to eliminate antialiasing
            if font_header:
                bbox = font_header.getbbox(device_text)
                text_width = bbox[2] - bbox[0]
                text_height = bbox[3] - bbox[1]

                # Create 1-bit image (black and white only, no gray)
                text_img = Image.new('1', (text_width + 2, text_height + 2), 0)
                text_draw = ImageDraw.Draw(text_img)
                text_draw.text((-bbox[0], -bbox[1]), device_text, fill=1, font=font_header)

                # Copy pixels to main image with solid color (moved down 2 lines)
                x_pos = (64 - text_width) // 2
                for y in range(text_img.height):
                    for x in range(text_img.width):
                        if text_img.getpixel((x, y)):
                            draw.point((x_pos + x, 4 + y), fill=device_color)
            else:
                # Fallback to default font (moved down 2 lines)
                text_width = draw.textlength(device_text, font=font_header) if font_header else len(device_text) * 6
                draw.text(((64 - text_width) // 2, 4), device_text, fill=device_color, font=font_header)
            
            # Draw two boxes side by side (moved down to create space)
            # Left box for Gravity (32x20 pixels) - BRIGHT 1px border
            draw.rectangle((1, 13, 31, 29), outline=(240, 240, 240), width=1)

            # Right box for Temperature (32x20 pixels) - BRIGHT 1px border
            draw.rectangle((33, 13, 62, 29), outline=(240, 240, 240), width=1)
            
            # Gravity box content - centered value (no units), NO ANTIALIASING
            gravity_str = f"{gravity:.3f}"

            if font_numbers:
                # Render gravity text without antialiasing using TrueType font
                bbox = font_numbers.getbbox(gravity_str)
                grav_width = bbox[2] - bbox[0]
                grav_height = bbox[3] - bbox[1]

                # 1-bit rendering for gravity
                grav_img = Image.new('1', (grav_width + 4, grav_height + 4), 0)
                grav_draw = ImageDraw.Draw(grav_img)
                grav_draw.text((-bbox[0] + 2, -bbox[1] + 2), gravity_str, fill=1, font=font_numbers)

                # Copy to main image with solid white (centered vertically in box)
                x_pos = 16 - grav_width // 2
                y_pos = 21 - grav_height // 2  # Center in box (13+29)/2 = 21
                for y in range(grav_img.height):
                    for x in range(grav_img.width):
                        if grav_img.getpixel((x, y)):
                            draw.point((x_pos + x - 2, y_pos + y - 2), fill=(255, 255, 255))
            else:
                # Fallback (centered vertically in box)
                grav_width = len(gravity_str) * 6
                draw.text((16 - grav_width // 2, 18), gravity_str, fill=(255, 255, 255))
            
            # Temperature box content - centered value (no units), NO ANTIALIASING
            temp_str = f"{temp_f:.1f}"

            if font_numbers:
                # Render temperature text without antialiasing using TrueType font
                bbox = font_numbers.getbbox(temp_str)
                temp_width = bbox[2] - bbox[0]
                temp_height = bbox[3] - bbox[1]

                # 1-bit rendering for temperature
                temp_img = Image.new('1', (temp_width + 4, temp_height + 4), 0)
                temp_draw = ImageDraw.Draw(temp_img)
                temp_draw.text((-bbox[0] + 2, -bbox[1] + 2), temp_str, fill=1, font=font_numbers)

                # Copy to main image with orange color (centered vertically in box)
                x_pos = 48 - temp_width // 2
                y_pos = 21 - temp_height // 2  # Center in box (13+29)/2 = 21
                for y in range(temp_img.height):
                    for x in range(temp_img.width):
                        if temp_img.getpixel((x, y)):
                            draw.point((x_pos + x - 2, y_pos + y - 2), fill=(255, 170, 68))
            else:
                # Fallback (centered vertically in box)
                temp_width = len(temp_str) * 6
                draw.text((48 - temp_width // 2, 18), temp_str, fill=(255, 170, 68))
            
            
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