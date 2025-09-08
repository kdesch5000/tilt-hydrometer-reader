"""
Tilt Hydrometer Display for Tidbyt
Shows current gravity, temperature, and trend for Tilt hydrometers
"""

load("render.star", "render")
load("http.star", "http")
load("schema.star", "schema")
load("cache.star", "cache")
load("encoding/json.star", "json")
load("time.star", "time")

# Default configuration
DEFAULT_API_URL = "http://localhost:8000/api/tilt/data"
DEFAULT_DEVICE_COLOR = "RED"
DEFAULT_UPDATE_INTERVAL = "300"  # 5 minutes in seconds

def main(config):
    """Main function to generate the Tidbyt display"""
    
    # Get configuration
    api_url = config.get("api_url", DEFAULT_API_URL)
    device_color = config.get("device_color", DEFAULT_DEVICE_COLOR).upper()
    update_interval = int(config.get("update_interval", DEFAULT_UPDATE_INTERVAL))
    
    # Try to fetch data from the Python API
    data = get_tilt_data(api_url, device_color)
    
    if not data:
        return render_error("No Tilt Data")
    
    return render_tilt_display(data, device_color)

def get_tilt_data(api_url, device_color):
    """Fetch Tilt data from the Python API"""
    
    # Check cache first
    cache_key = "tilt_data_" + device_color.lower()
    cached_data = cache.get(cache_key)
    
    if cached_data:
        return json.decode(cached_data)
    
    # Fetch fresh data
    try:
        response = http.get(api_url + "/" + device_color.lower(), ttl_seconds=300)
        
        if response.status_code == 200:
            data = response.json()
            
            # Cache the data for 5 minutes
            cache.set(cache_key, json.encode(data), ttl_seconds=300)
            
            return data
        else:
            print("Failed to fetch data: " + str(response.status_code))
            return None
            
    except Exception as e:
        print("Error fetching data: " + str(e))
        return None

def render_tilt_display(data, device_color):
    """Render the main Tilt display"""
    
    # Extract data
    temperature = data.get("temperature", 0.0)
    gravity = data.get("gravity", 1.000)
    timestamp = data.get("timestamp", "")
    trend = data.get("trend", "stable")
    
    # Color scheme based on Tilt color
    color_schemes = {
        "RED": "#FF4444",
        "GREEN": "#44FF44", 
        "BLACK": "#CCCCCC",
        "PURPLE": "#CC44CC",
        "ORANGE": "#FF8844",
        "BLUE": "#4444FF",
        "YELLOW": "#FFFF44",
        "PINK": "#FF88CC"
    }
    
    tilt_color = color_schemes.get(device_color, "#FFFFFF")
    
    # Create trend indicator
    trend_icon = "→"
    if trend == "rising":
        trend_icon = "↗"
    elif trend == "falling":
        trend_icon = "↘"
    
    # Format values for display
    temp_str = "{:.1f}°F".format(temperature)
    gravity_str = "{:.3f}".format(gravity)
    
    # Get current time for display
    now = time.now()
    time_str = now.format("15:04")
    
    return render.Root(
        child=render.Box(
            color="#000000",
            child=render.Column(
                expanded=True,
                main_align="space_around",
                children=[
                    # Header with device color only (centered)
                    render.Row(
                        expanded=True,
                        main_align="center",
                        children=[
                            render.Text(
                                content=device_color + " TILT",
                                font="tom-thumb",
                                color=tilt_color,
                            ),
                        ],
                    ),
                    
                    # Side-by-side boxes for Gravity and Temperature
                    render.Row(
                        expanded=True,
                        main_align="space_evenly",
                        children=[
                            # Left box - Gravity
                            render.Box(
                                width=30,
                                height=20,
                                color="#000000",
                                child=render.Column(
                                    main_align="center",
                                    cross_align="center",
                                    children=[
                                        render.Text(
                                            content=gravity_str,
                                            font="tom-thumb",
                                            color="#FFFFFF",
                                        ),
                                        render.Text(
                                            content="SG " + trend_icon,
                                            font="tom-thumb",
                                            color="#CCCCCC",
                                        ),
                                    ],
                                ),
                            ),
                            
                            # Right box - Temperature  
                            render.Box(
                                width=30,
                                height=20,
                                color="#000000",
                                child=render.Column(
                                    main_align="center",
                                    cross_align="center",
                                    children=[
                                        render.Text(
                                            content="{:.1f}".format(temperature),
                                            font="tom-thumb",
                                            color="#FFAA44",
                                        ),
                                        render.Text(
                                            content="°F",
                                            font="tom-thumb",
                                            color="#CCCCCC",
                                        ),
                                    ],
                                ),
                            ),
                        ],
                    ),
                    
                    # Status bar
                    render.Box(
                        width=64,
                        height=1,
                        color=tilt_color,
                    ),
                ],
            ),
        ),
    )

def render_error(message):
    """Render error message when data is unavailable"""
    return render.Root(
        child=render.Box(
            color="#000000",
            child=render.Column(
                expanded=True,
                main_align="center",
                cross_align="center",
                children=[
                    render.Text(
                        content="TILT",
                        font="6x13",
                        color="#FF4444",
                    ),
                    render.Text(
                        content=message,
                        font="tom-thumb",
                        color="#CCCCCC",
                    ),
                ],
            ),
        ),
    )

def get_schema():
    """Configuration schema for the Tidbyt app"""
    return schema.Schema(
        version="1",
        fields=[
            schema.Text(
                id="api_url",
                name="API URL",
                desc="URL of your Tilt data API",
                icon="globe",
                default=DEFAULT_API_URL,
            ),
            schema.Dropdown(
                id="device_color",
                name="Tilt Color",
                desc="Color of your Tilt hydrometer",
                icon="palette",
                default=DEFAULT_DEVICE_COLOR,
                options=[
                    schema.Option(
                        display="Red",
                        value="RED",
                    ),
                    schema.Option(
                        display="Green", 
                        value="GREEN",
                    ),
                    schema.Option(
                        display="Black",
                        value="BLACK",
                    ),
                    schema.Option(
                        display="Purple",
                        value="PURPLE",
                    ),
                    schema.Option(
                        display="Orange",
                        value="ORANGE",
                    ),
                    schema.Option(
                        display="Blue",
                        value="BLUE",
                    ),
                    schema.Option(
                        display="Yellow",
                        value="YELLOW",
                    ),
                    schema.Option(
                        display="Pink",
                        value="PINK",
                    ),
                ],
            ),
            schema.Text(
                id="update_interval",
                name="Update Interval (seconds)",
                desc="How often to refresh data",
                icon="clock",
                default=DEFAULT_UPDATE_INTERVAL,
            ),
        ],
    )