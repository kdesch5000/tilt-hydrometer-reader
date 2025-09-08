#!/usr/bin/env python3
"""
Tidbyt App Management Tool
Lists all installed apps and allows selective deletion
"""

import requests
import json
from tidbyt_integration import TidbytPusher

def list_installed_apps():
    """List all apps installed on the Tidbyt device"""
    
    pusher = TidbytPusher()
    
    if not pusher.config or not pusher.enabled:
        print("❌ Tidbyt not configured. Please configure first.")
        return None, None, None
    
    device_id = pusher.config.device_id
    api_key = pusher.config.api_key
    
    print(f"📱 Listing apps for Tidbyt device: {device_id}")
    print()
    
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json'
    }
    
    try:
        # Get list of installations
        url = f"https://api.tidbyt.com/v0/devices/{device_id}/installations"
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            # print(f"DEBUG: API Response: {data}")  # Debug line - commented out
            
            # Handle different API response formats
            if isinstance(data, dict):
                installations = data.get('installations', [])
            elif isinstance(data, list):
                installations = data
            else:
                print(f"❌ Unexpected API response format: {type(data)}")
                return None, None, None
            
            if not installations:
                print("ℹ️  No apps currently installed on your Tidbyt")
                return [], device_id, headers
            
            print("📋 Installed Apps:")
            print("=" * 60)
            
            for i, app in enumerate(installations, 1):
                installation_id = app.get('id', app.get('installationID', 'Unknown'))
                app_id = app.get('appID', 'Unknown')
                created = app.get('createdAt', 'Unknown')
                
                # Try to make sense of the app name
                if 'tilt' in installation_id.lower() or 'tilt' in app_id.lower():
                    app_name = "🍺 Tilt Hydrometer"
                elif installation_id.startswith('VqrvNQfRaE'):
                    app_name = "🤷 Unknown Tilt App (API pushed)"
                elif app_id:
                    app_name = f"📱 {app_id}"
                else:
                    app_name = "📱 Unknown App"
                
                print(f"{i:2d}. {app_name}")
                print(f"    Installation ID: {installation_id}")
                print(f"    App ID: {app_id}")
                print(f"    Created: {created}")
                print()
            
            return installations, device_id, headers
            
        else:
            print(f"❌ Failed to get app list: {response.status_code}")
            if response.text:
                print(f"   Error: {response.text}")
            return None, None, None
            
    except Exception as e:
        print(f"❌ Error listing apps: {e}")
        return None, None, None

def delete_installation(installation_id, device_id, headers):
    """Delete a specific installation"""
    
    try:
        url = f"https://api.tidbyt.com/v0/devices/{device_id}/installations/{installation_id}"
        response = requests.delete(url, headers=headers, timeout=10)
        
        if response.status_code in [200, 204]:
            return True
        else:
            print(f"❌ Failed to delete {installation_id}: {response.status_code}")
            if response.text:
                print(f"   Error: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error deleting {installation_id}: {e}")
        return False

def main():
    print("=" * 60)
    print("         TIDBYT APP MANAGEMENT TOOL")
    print("=" * 60)
    print()
    
    # List all apps
    installations, device_id, headers = list_installed_apps()
    
    if not installations:
        return
    
    if not installations:  # Empty list
        print("Nothing to manage!")
        return
    
    print("🗑️  Select apps to delete:")
    print("   Enter numbers separated by spaces (e.g., '1 3 5')")
    print("   Enter 'all' to delete all apps")
    print("   Enter 'q' to quit")
    print()
    
    try:
        selection = input("Your selection > ").strip().lower()
        
        if selection == 'q':
            print("Cancelled")
            return
        
        if selection == 'all':
            print("\n⚠️  This will delete ALL apps from your Tidbyt!")
            confirm = input("Are you sure? Type 'yes' to confirm > ").strip().lower()
            if confirm == 'yes':
                deleted_count = 0
                for app in installations:
                    installation_id = app.get('id', app.get('installationID'))
                    if delete_installation(installation_id, device_id, headers):
                        print(f"✅ Deleted: {installation_id}")
                        deleted_count += 1
                    else:
                        print(f"❌ Failed to delete: {installation_id}")
                
                print(f"\n🎉 Deleted {deleted_count} apps")
            else:
                print("Cancelled")
            return
        
        # Parse individual selections
        try:
            selected_numbers = [int(x) for x in selection.split()]
        except ValueError:
            print("❌ Invalid input. Please enter numbers separated by spaces.")
            return
        
        # Validate selections
        invalid_numbers = [n for n in selected_numbers if n < 1 or n > len(installations)]
        if invalid_numbers:
            print(f"❌ Invalid selections: {invalid_numbers}")
            return
        
        # Delete selected apps
        deleted_count = 0
        for num in selected_numbers:
            app = installations[num - 1]  # Convert to 0-based index
            installation_id = app.get('id', app.get('installationID'))
            
            if delete_installation(installation_id, device_id, headers):
                print(f"✅ Deleted: {installation_id}")
                deleted_count += 1
            else:
                print(f"❌ Failed to delete: {installation_id}")
        
        print(f"\n🎉 Successfully deleted {deleted_count} apps")
        
        if deleted_count > 0:
            print("\nℹ️  Your Tidbyt display will update shortly to reflect the changes.")
        
    except KeyboardInterrupt:
        print("\n\nCancelled by user")
    except Exception as e:
        print(f"\n❌ Error during selection: {e}")

if __name__ == "__main__":
    main()