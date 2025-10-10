# Installation Guide - Tilt Hydrometer Reader

This guide will walk you through installing the Tilt Hydrometer Reader on a fresh Raspberry Pi, step by step.

## Requirements

- **Raspberry Pi 5** (or Pi 4/3 with Bluetooth LE)
- **Raspberry Pi OS** (Bookworm or newer recommended)
- **Internet connection** (for downloading software)
- **Tilt Hydrometer** device

## Step 1: Download the Software

### Option A: Using Git (Recommended)

**Install Git** (if not already installed):
```bash
sudo apt update
sudo apt install -y git
```

**Download the project:**
```bash
# Navigate to where you want to install (e.g., your home directory)
cd ~

# Download the project from GitHub
git clone https://github.com/kdesch5000/tilt-hydrometer-reader.git

# Enter the project directory
cd tilt-hydrometer-reader
```

### Option B: Download as ZIP (Alternative)

If you don't want to use git:

1. Go to: https://github.com/kdesch5000/tilt-hydrometer-reader
2. Click the green "Code" button
3. Select "Download ZIP"
4. Extract the ZIP file to your home directory
5. Open Terminal and navigate to the folder:
   ```bash
   cd ~/tilt-hydrometer-reader-main
   ```

## Step 2: Install System Dependencies

These are required operating system packages:

```bash
# Update package list
sudo apt update

# Install Bluetooth packages
sudo apt install -y bluetooth bluez pi-bluetooth

# Install Python and build tools
sudo apt install -y python3 python3-pip python3-dev python3-venv

# Install image processing libraries (needed for Tidbyt display)
sudo apt install -y libjpeg-dev zlib1g-dev

# Install TrueType fonts (needed for Tidbyt display)
sudo apt install -y fonts-dejavu-core
```

## Step 3: Configure Bluetooth

### Enable Experimental Bluetooth Features

The project requires experimental BlueZ features for reliable BLE scanning:

```bash
# Edit the Bluetooth configuration
sudo nano /etc/bluetooth/main.conf
```

Add this line at the end of the file (or uncomment if it exists):
```
Experimental = true
```

**To save and exit nano:**
- Press `Ctrl+X`
- Press `Y` to confirm
- Press `Enter` to save

**Restart Bluetooth service:**
```bash
sudo systemctl restart bluetooth
```

**Verify Bluetooth is running:**
```bash
sudo systemctl status bluetooth
```

You should see "active (running)" in green.

### Set Up Bluetooth Permissions

Add your user to the bluetooth group so you can run the scanner:

```bash
# Add your user to bluetooth group
sudo usermod -a -G bluetooth $USER

# Log out and back in for this to take effect
# Or reboot:
sudo reboot
```

**Note:** You'll still need to use `sudo` to run the monitor due to BLE scanning requirements.

## Step 4: Install Python Dependencies

### Create a Virtual Environment (Recommended)

A virtual environment keeps the project's Python packages separate from system packages:

```bash
# Make sure you're in the project directory
cd ~/tilt-hydrometer-reader

# Create virtual environment
python3 -m venv venv

# Activate the virtual environment
source venv/bin/activate
```

You'll see `(venv)` appear at the start of your command prompt.

### Install Required Packages

**Basic functionality (terminal monitor):**
```bash
pip install -r requirements.txt
```

**Tidbyt display integration (optional):**
```bash
pip install -r requirements-tidbyt.txt
```

### Alternative: System-Wide Installation

If you prefer not to use a virtual environment:

```bash
pip install -r requirements.txt --break-system-packages
pip install -r requirements-tidbyt.txt --break-system-packages
```

**Note:** Using `--break-system-packages` is required on modern Raspberry Pi OS but may affect system stability.

## Step 5: Test Your Installation

### Test Bluetooth Scanning

First, make sure your Tilt is floating in water and powered on.

**Run a test scan:**
```bash
sudo python3 tilt_scanner.py
```

You should see output showing your Tilt device being detected. Press `Ctrl+C` to stop.

**Troubleshooting:**
- If you see "Permission denied" errors, make sure you're using `sudo`
- If no devices are found, verify your Tilt is powered on and within range
- Check Bluetooth is enabled: `sudo systemctl status bluetooth`

### Test the Terminal Monitor

**Run the main monitor application:**
```bash
sudo python3 tilt_monitor.py
```

You should see:
- A full-screen ASCII interface
- Your Tilt device name and status
- Real-time gravity and temperature readings
- History charts

**Controls:**
- Press `q` to quit
- Press `c` to configure
- Press `h` for help

### Test Tidbyt Integration (Optional)

If you installed the Tidbyt dependencies and have a Tidbyt device:

**Generate a test image:**
```bash
python3 test_tidbyt_custom.py 1.045 68.5 RED
```

This creates a test image file you can inspect.

**Push to your Tidbyt device:**
```bash
python3 push_test_to_tidbyt.py 1.045 68.5 RED
```

**Note:** You'll need to configure your Tidbyt credentials first (see Tidbyt Setup below).

## Step 6: Configuration

### Basic Configuration

The monitor creates a configuration file automatically on first run.

**To configure BrewStat.us cloud logging:**
1. Run the monitor: `sudo python3 tilt_monitor.py`
2. Press `c` for configuration
3. Select "Change API Key"
4. Enter your BrewStat.us API key
5. Return to monitoring

### Tidbyt Setup (Optional)

See **[TIDBYT_SETUP.md](TIDBYT_SETUP.md)** for complete Tidbyt configuration instructions.

**Quick steps:**
1. Get your Tidbyt credentials from the Tidbyt mobile app:
   - Settings → Developer → Get API Key
2. Run monitor with Tidbyt: `sudo python3 tilt_monitor.py --tidbyt`
3. Press `c` and select "Tidbyt Integration"
4. Enter your Device ID and API Key

### Device Calibration

To calibrate your Tilt for more accurate readings:

```bash
sudo python3 calibrate_tilt.py
```

Follow the on-screen instructions. You'll need:
- Clean water at a known temperature
- An accurate thermometer
- Your Tilt floating in the water

## Step 7: Running Automatically on Boot (Optional)

To have the monitor start automatically when your Raspberry Pi boots:

### Create a Systemd Service

**Create the service file:**
```bash
sudo nano /etc/systemd/system/tilt-monitor.service
```

**Add this content:**
```ini
[Unit]
Description=Tilt Hydrometer Monitor
After=network.target bluetooth.target

[Service]
Type=simple
User=root
WorkingDirectory=/home/YOUR_USERNAME/tilt-hydrometer-reader
ExecStart=/home/YOUR_USERNAME/tilt-hydrometer-reader/venv/bin/python3 /home/YOUR_USERNAME/tilt-hydrometer-reader/tilt_monitor.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**Replace** `YOUR_USERNAME` with your actual username (usually `pi`).

**Enable and start the service:**
```bash
# Enable service to start on boot
sudo systemctl enable tilt-monitor.service

# Start the service now
sudo systemctl start tilt-monitor.service

# Check status
sudo systemctl status tilt-monitor.service
```

**View logs:**
```bash
sudo journalctl -u tilt-monitor.service -f
```

**Stop the service:**
```bash
sudo systemctl stop tilt-monitor.service
```

## Troubleshooting

### No Tilt Devices Found

**Check Bluetooth:**
```bash
# Verify Bluetooth is running
sudo systemctl status bluetooth

# Restart Bluetooth if needed
sudo systemctl restart bluetooth

# Check if Bluetooth can scan
sudo hcitool lescan
```

Press `Ctrl+C` to stop the scan. You should see your Tilt appear.

**Common issues:**
- Tilt not powered on or battery dead
- Tilt out of range (try moving closer)
- WiFi interference (2.4GHz WiFi can interfere with Bluetooth)
- Experimental features not enabled in `/etc/bluetooth/main.conf`

### Permission Errors

If you see "Permission denied" errors:

```bash
# Make sure you're using sudo
sudo python3 tilt_monitor.py

# Verify you're in the bluetooth group
groups

# If "bluetooth" is not listed, add yourself and reboot
sudo usermod -a -G bluetooth $USER
sudo reboot
```

### Python Import Errors

If you see "ModuleNotFoundError":

```bash
# Make sure you're in the virtual environment
source venv/bin/activate

# Reinstall requirements
pip install -r requirements.txt

# For Tidbyt features
pip install -r requirements-tidbyt.txt
```

### Tidbyt Display Issues

**"Tidbyt integration not available":**
```bash
# Install Tidbyt dependencies
pip install -r requirements-tidbyt.txt
```

**"Token is not active" (401 error):**
- Verify your API key is correct and active at https://tidbyt.dev
- Get new credentials from Tidbyt mobile app (Settings → Developer)
- Check Device ID matches your actual Tidbyt

**Display looks wrong or has artifacts:**
- This usually means fonts are missing
- Verify fonts are installed: `ls /usr/share/fonts/truetype/dejavu/`
- Reinstall if needed: `sudo apt install --reinstall fonts-dejavu-core`

### Performance Issues

**Monitor is slow or unresponsive:**
- Reduce scan interval in configuration
- Close other Bluetooth applications
- Check system resources: `htop`

**Bluetooth drops or disconnects:**
- Move Raspberry Pi and Tilt closer together
- Reduce 2.4GHz WiFi interference (switch to 5GHz if possible)
- Update Raspberry Pi firmware: `sudo rpi-update`

### Data Logging Issues

**CSV files not being created:**
- Check the `data/` directory exists and has write permissions
- Create it manually: `mkdir -p data`

**BrewStat.us uploads failing:**
- Verify internet connection
- Check API key is correct
- Test connectivity: `ping www.brewstat.us`

## Updating the Software

To get the latest version from GitHub:

```bash
# Navigate to project directory
cd ~/tilt-hydrometer-reader

# Stop any running monitor
sudo systemctl stop tilt-monitor.service  # If using systemd
# Or press 'q' if running in terminal

# Pull latest changes from GitHub
git pull

# Update Python dependencies
source venv/bin/activate
pip install -r requirements.txt
pip install -r requirements-tidbyt.txt

# Restart monitor
sudo python3 tilt_monitor.py
# Or: sudo systemctl start tilt-monitor.service
```

## Uninstalling

To completely remove the software:

```bash
# Stop the service if running
sudo systemctl stop tilt-monitor.service
sudo systemctl disable tilt-monitor.service
sudo rm /etc/systemd/system/tilt-monitor.service

# Remove the software directory
rm -rf ~/tilt-hydrometer-reader

# Optional: Remove system packages (be careful - may affect other software)
sudo apt remove --purge bluetooth bluez pi-bluetooth
```

## Getting Help

If you encounter issues not covered here:

1. Check the main **[README.md](README.md)** for general information
2. Review **[README_USAGE.md](README_USAGE.md)** for usage details
3. For Tidbyt issues, see **[TIDBYT_SETUP.md](TIDBYT_SETUP.md)**
4. Open an issue on GitHub: https://github.com/kdesch5000/tilt-hydrometer-reader/issues

## Quick Reference

**Start monitoring:**
```bash
cd ~/tilt-hydrometer-reader
source venv/bin/activate  # If using venv
sudo python3 tilt_monitor.py
```

**With Tidbyt:**
```bash
sudo python3 tilt_monitor.py --tidbyt
```

**Calibrate device:**
```bash
sudo python3 calibrate_tilt.py
```

**Test Tidbyt display:**
```bash
python3 test_tidbyt_custom.py 1.045 68.5 RED
```

**Update software:**
```bash
cd ~/tilt-hydrometer-reader
git pull
source venv/bin/activate
pip install -r requirements.txt
```

**View logs (if using systemd):**
```bash
sudo journalctl -u tilt-monitor.service -f
```

---

## Additional Resources

- **Tilt Hydrometer Official Site:** https://tilthydrometer.com/
- **BrewStat.us Cloud Service:** https://www.brewstat.us/
- **Tidbyt Display Device:** https://tidbyt.com/
- **Raspberry Pi Documentation:** https://www.raspberrypi.org/documentation/

---

**Congratulations!** You should now have a fully functional Tilt Hydrometer monitoring system running on your Raspberry Pi! 🍺
