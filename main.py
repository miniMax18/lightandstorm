"""
Enhanced ESP32 Storm Sensor System - DHT11 INTEGRATION
- Auto-starts on boot when saved as main.py
- Person detection, storm detection, DHT11 weather sensor
- LEDs on pins 0, 2, and 15 (LOW = ON, HIGH = OFF)
- Cloud LED, Storm LED, On Air LED
- Manual overrides persist until explicitly reset
- Smart antenna control logic with humidity/temperature readings
"""

import network
import socket
import machine
import time
import json
import dht
import gc  # Garbage collection for stability

# Boot delay for hardware stabilization
print("=== ESP32 Storm Sensor System Starting ===")
time.sleep(2)  # Give DHT11 and other components time to stabilize

# Configuration
WIFI_SSID = "AdrianWiFi"
WIFI_PASSWORD = "bbbbbbbb"

# Pin Configuration - CORRECTED FOR YOUR HARDWARE
# INPUTS (Sensors) - Using available pins
PIR_PIN = 4          # Person presence sensor (HIGH = person detected)
STORM_PIN = 5        # Storm sensor (HIGH = storm detected) - moved from pin 0
DHT11_PIN = 18       # DHT11 temperature/humidity sensor data pin

# OUTPUTS (Controlled devices) - CORRECTED
ANTENNA_PIN = 19     # Antenna relay (HIGH = antenna connected) - moved from pin 2
LED1_PIN = 0         # LED 1 (Storm indicator) - LOW = ON
LED2_PIN = 15         # LED 2 (Clouds indicator) - LOW = ON  
LED3_PIN = 2        # LED 3 (On Air indicator) - LOW = ON

class EnhancedStormSensor:
    def __init__(self):
        # Setup INPUT pins (sensors)
        self.pir_sensor = machine.Pin(PIR_PIN, machine.Pin.IN)
        self.storm_sensor = machine.Pin(STORM_PIN, machine.Pin.IN, machine.Pin.PULL_UP)
        
        # DHT11 sensor for temperature and humidity
        try:
            self.dht11_sensor = dht.DHT11(machine.Pin(DHT11_PIN))
            print(f"DHT11 sensor initialized on pin {DHT11_PIN}")
        except Exception as e:
            print(f"DHT11 initialization error: {e}")
            self.dht11_sensor = None
        
        # Weather thresholds
        self.humidity_threshold = 80  # Above 80% = high chance of clouds/rain
        self.temp_min = 5            # Below 5°C = poor weather
        self.temp_max = 35           # Above 35°C = extreme heat
        
        # Setup OUTPUT pins - CORRECTED FOR YOUR HARDWARE
        self.antenna_relay = machine.Pin(ANTENNA_PIN, machine.Pin.OUT)
        self.storm_led = machine.Pin(LED1_PIN, machine.Pin.OUT)    # LED on pin 0 (LOW = ON)
        self.clouds_led = machine.Pin(LED2_PIN, machine.Pin.OUT)   # LED on pin 2 (LOW = ON)
        self.on_air_led = machine.Pin(LED3_PIN, machine.Pin.OUT)   # LED on pin 15 (LOW = ON)
        
        # Initialize all outputs to OFF
        self.antenna_relay.value(0)    # Antenna OFF
        self.on_air_led.value(1)       # On Air LED OFF (HIGH = OFF for LEDs)
        self.storm_led.value(1)        # Storm LED OFF (HIGH = OFF for LEDs)
        self.clouds_led.value(1)       # Clouds LED OFF (HIGH = OFF for LEDs)
        
        # WiFi setup
        self.wlan = network.WLAN(network.STA_IF)
        self.ip_address = None
        
        # Manual override states - persist until reset
        self.manual_override = {
            'storm_led': False,
            'clouds_led': False,
            'on_air_led': False,
            'antenna': False
        }
    
    def set_weather_thresholds(self, humidity_max=80, temp_min=5, temp_max=35):
        """Adjust weather detection thresholds"""
        self.humidity_threshold = humidity_max
        self.temp_min = temp_min
        self.temp_max = temp_max
        print(f"Weather thresholds updated: Humidity >{humidity_max}%, Temp {temp_min}-{temp_max}°C")
        
        print("=== Enhanced Storm Sensor System - DHT11 INTEGRATION ===")
        print(f"INPUT Pins configured:")
        print(f"  Person Sensor: GPIO {PIR_PIN}")
        print(f"  Storm Sensor: GPIO {STORM_PIN}")
        print(f"  DHT11 Sensor: GPIO {DHT11_PIN} (Temperature & Humidity)")
        print(f"OUTPUT Pins configured:")
        print(f"  Antenna Relay: GPIO {ANTENNA_PIN}")
        print(f"  Storm LED: GPIO {LED1_PIN} (LOW = ON)")
        print(f"  Clouds LED: GPIO {LED2_PIN} (LOW = ON)")
        print(f"  On Air LED: GPIO {LED3_PIN} (LOW = ON)")
        print(f"Manual override system enabled - settings persist until reset")
        print(f"Weather thresholds: Humidity >{self.humidity_threshold}% = cloudy, Temp {self.temp_min}-{self.temp_max}°C")
        
    def connect_wifi(self):
        """Connect to WiFi network"""
        self.wlan.active(True)
        
        if not self.wlan.isconnected():
            print("Connecting to WiFi...")
            self.wlan.connect(WIFI_SSID, WIFI_PASSWORD)
            
            timeout = 15
            while not self.wlan.isconnected() and timeout > 0:
                time.sleep(1)
                timeout -= 1
        
        if self.wlan.isconnected():
            self.ip_address = self.wlan.ifconfig()[0]
            self.on_air_led.value(0)  # On Air LED ON when WiFi connected (LOW = ON)
            print(f"WiFi connected: {self.ip_address}")
            return True
        else:
            print("WiFi connection failed!")
            # Flash on air LED to indicate WiFi error
            for i in range(5):
                self.on_air_led.value(0)  # LED ON (LOW = ON)
                time.sleep(0.2)
                self.on_air_led.value(1)  # LED OFF (HIGH = OFF)
                time.sleep(0.2)
            return False
    
    def read_dht11(self):
        """Read DHT11 sensor with error handling"""
        if not self.dht11_sensor:
            return None, None, "DHT11 not initialized"
        
        try:
            self.dht11_sensor.measure()
            temperature = self.dht11_sensor.temperature()
            humidity = self.dht11_sensor.humidity()
            
            # Validate readings
            if temperature is not None and humidity is not None:
                if -40 <= temperature <= 80 and 0 <= humidity <= 100:
                    return temperature, humidity, "OK"
                else:
                    return None, None, "Invalid readings"
            else:
                return None, None, "Read failed"
                
        except Exception as e:
            return None, None, f"DHT11 error: {str(e)}"
    
    def read_sensors(self):
        """Read all sensor values including DHT11"""
        try:
            presence = bool(self.pir_sensor.value())
            storm = bool(self.storm_sensor.value())
            antenna_connected = bool(self.antenna_relay.value())
            
            # Read DHT11 with error handling
            temperature, humidity, dht_status = self.read_dht11()
            
            # Determine cloud conditions from humidity and temperature
            clouds = False
            weather_status = "Unknown"
            
            if temperature is not None and humidity is not None:
                # High humidity OR extreme temperatures suggest poor weather
                if humidity > self.humidity_threshold:
                    clouds = True
                    weather_status = f"High humidity ({humidity}%) - Cloudy"
                elif temperature < self.temp_min:
                    clouds = True
                    weather_status = f"Cold weather ({temperature}°C) - Poor conditions"
                elif temperature > self.temp_max:
                    clouds = True
                    weather_status = f"Hot weather ({temperature}°C) - Extreme heat"
                else:
                    clouds = False
                    weather_status = f"Good weather ({temperature}°C, {humidity}%)"
            else:
                weather_status = f"DHT11 error: {dht_status}"
            
            return {
                'presence': presence,
                'storm': storm,
                'clouds': clouds,
                'antenna_connected': antenna_connected,
                'temperature': temperature,
                'humidity': humidity,
                'weather_status': weather_status,
                'dht_status': dht_status,
                'timestamp': time.ticks_ms()
            }
        except Exception as e:
            print(f"Sensor read error: {e}")
            return {
                'presence': False,
                'storm': False,
                'clouds': False,
                'antenna_connected': False,
                'temperature': None,
                'humidity': None,
                'weather_status': "Sensor error",
                'dht_status': "Error",
                'timestamp': time.ticks_ms()
            }
    
    def update_logic(self):
        """Enhanced control logic with DHT11 weather analysis and manual override support"""
        try:
            sensors = self.read_sensors()
            presence = sensors['presence']
            storm = sensors['storm']
            clouds = sensors['clouds']  # Now determined by DHT11 readings
            
            # LED CONTROL - Only update if not manually overridden
            if not self.manual_override['storm_led']:
                self.storm_led.value(0 if storm else 1)      # LED1 (pin 0) = Storm sensor (LOW = ON)
            
            if not self.manual_override['clouds_led']:
                self.clouds_led.value(0 if clouds else 1)    # LED2 (pin 2) = Poor weather from DHT11 (LOW = ON)
            
            # ANTENNA CONTROL LOGIC - Only if not manually overridden
            if not self.manual_override['antenna']:
                if not presence:
                    should_connect = False
                    reason = "No person detected"
                elif storm:
                    should_connect = False  
                    reason = "Storm detected - safety first!"
                elif presence and not storm:
                    should_connect = True
                    if clouds:
                        weather_desc = sensors.get('weather_status', 'Poor weather')
                        reason = f"Person present, {weather_desc} (antenna ON)"
                    else:
                        weather_desc = sensors.get('weather_status', 'Good weather')
                        reason = f"Person present, {weather_desc} (antenna ON)"
                else:
                    should_connect = False
                    reason = "Unknown condition"
                
                # Apply antenna control
                current_state = sensors['antenna_connected']
                if should_connect != current_state:
                    self.antenna_relay.value(1 if should_connect else 0)
                    print(f"Antenna {'ON' if should_connect else 'OFF'}: {reason}")
                
                # ON AIR LED - Shows when antenna is actively connected (only if not overridden)
                if not self.manual_override['on_air_led']:
                    self.on_air_led.value(0 if should_connect else 1)  # LOW = ON
            else:
                reason = "Manual override active"
                should_connect = sensors['antenna_connected']
            
            # Update sensor data with reason
            sensors['control_reason'] = reason
            sensors['on_air'] = should_connect  # Add on_air status
            sensors['manual_overrides'] = self.manual_override.copy()  # Add override info
            return sensors
            
        except Exception as e:
            print(f"Logic update error: {e}")
            return self.read_sensors()
    
    def control_antenna(self, connect, manual=True):
        """Manual antenna control with override flag"""
        try:
            self.antenna_relay.value(1 if connect else 0)
            if manual:
                self.manual_override['antenna'] = True
                self.manual_override['on_air_led'] = True  # Also override on air LED
                self.on_air_led.value(0 if connect else 1)  # Update on air LED manually
                print(f"Manual override: Antenna {'ON' if connect else 'OFF'}")
        except Exception as e:
            print(f"Antenna control error: {e}")
    
    def control_led(self, led_type, state):
        """Manual LED control for testing - INVERTED LOGIC with override"""
        try:
            print(f"LED Control: {led_type} -> {'ON' if state else 'OFF'}")
            
            # Inverted logic: LOW = ON, HIGH = OFF
            led_value = 0 if state else 1
            
            if led_type == 'storm' or led_type == 'led1':
                self.storm_led.value(led_value)
                self.manual_override['storm_led'] = True
                print(f"Storm LED (pin {LED1_PIN}) set to {'LOW (ON)' if state else 'HIGH (OFF)'} - MANUAL")
                
            elif led_type == 'clouds' or led_type == 'led2':
                self.clouds_led.value(led_value)
                self.manual_override['clouds_led'] = True
                print(f"Weather LED (pin {LED2_PIN}) set to {'LOW (ON)' if state else 'HIGH (OFF)'} - MANUAL")
                
            elif led_type == 'on_air' or led_type == 'led3':
                self.on_air_led.value(led_value)
                self.manual_override['on_air_led'] = True
                print(f"On Air LED (pin {LED3_PIN}) set to {'LOW (ON)' if state else 'HIGH (OFF)'} - MANUAL")
                
            else:
                print(f"Unknown LED type: {led_type}")
                
        except Exception as e:
            print(f"LED control error: {e}")
    
    def reset_manual_overrides(self):
        """Reset all manual overrides back to automatic control"""
        self.manual_override = {
            'storm_led': False,
            'clouds_led': False,
            'on_air_led': False,
            'antenna': False
        }
        print("All manual overrides reset - back to automatic control")
    
    def test_all_outputs(self):
        """Test all LEDs and antenna relay - INVERTED LED LOGIC"""
        print("Testing all outputs...")
        outputs = [
            (f'Storm LED (pin {LED1_PIN})', self.storm_led),
            (f'Weather LED (pin {LED2_PIN})', self.clouds_led), 
            (f'On Air LED (pin {LED3_PIN})', self.on_air_led),
            (f'Antenna Relay (pin {ANTENNA_PIN})', self.antenna_relay)
        ]
        
        for name, pin in outputs:
            if 'LED' in name:
                # Inverted logic for LEDs: LOW = ON
                print(f"  {name} ON")
                pin.value(0)  # LOW = ON
                time.sleep(1)
                print(f"  {name} OFF") 
                pin.value(1)  # HIGH = OFF
                time.sleep(0.5)
            else:
                # Normal logic for relay
                print(f"  {name} ON")
                pin.value(1)
                time.sleep(1)
                print(f"  {name} OFF") 
                pin.value(0)
                time.sleep(0.5)
        
        print("Output test complete!")
    
    def test_individual_leds(self):
        """Individual LED test function - INVERTED LOGIC"""
        print("=== Individual LED Test (INVERTED LOGIC) ===")
        
        # Test LED 1 (pin 0)
        print("Testing LED 1 (Storm LED, pin 0)...")
        for i in range(3):
            self.storm_led.value(0)  # LOW = ON
            print("  Storm LED ON")
            time.sleep(0.5)
            self.storm_led.value(1)  # HIGH = OFF
            print("  Storm LED OFF")
            time.sleep(0.5)
        
        # Test LED 2 (pin 2)  
        print("Testing LED 2 (Weather LED, pin 2)...")
        for i in range(3):
            self.clouds_led.value(0)  # LOW = ON
            print("  Weather LED ON")
            time.sleep(0.5)
            self.clouds_led.value(1)  # HIGH = OFF
            print("  Weather LED OFF")
            time.sleep(0.5)
            
        # Test LED 3 (pin 15)
        print("Testing LED 3 (On Air LED, pin 15)...")
        for i in range(3):
            self.on_air_led.value(0)  # LOW = ON
            print("  On Air LED ON")
            time.sleep(0.5)
            self.on_air_led.value(1)  # HIGH = OFF
            print("  On Air LED OFF")
            time.sleep(0.5)
        
        print("Individual LED test complete!")
    
    def generate_html(self, sensors):
        """Generate enhanced web interface with DHT11 data"""
        presence_class = "sensor-active" if sensors['presence'] else "sensor-inactive"
        presence_text = "YES" if sensors['presence'] else "NO"
        
        storm_class = "sensor-active" if sensors['storm'] else "sensor-inactive"  
        storm_text = "YES" if sensors['storm'] else "NO"
        
        clouds_class = "sensor-active" if sensors['clouds'] else "sensor-inactive"
        clouds_text = "YES" if sensors['clouds'] else "NO"
        
        antenna_class = "sensor-active" if sensors['antenna_connected'] else "sensor-inactive"
        antenna_text = "CONNECTED" if sensors['antenna_connected'] else "DISCONNECTED"
        
        on_air_class = "sensor-active" if sensors.get('on_air', False) else "sensor-inactive"
        on_air_text = "ON AIR" if sensors.get('on_air', False) else "OFF AIR"
        
        # DHT11 data formatting
        temp = sensors.get('temperature')
        humidity = sensors.get('humidity')
        weather_status = sensors.get('weather_status', 'Unknown')
        
        temp_text = f"{temp}°C" if temp is not None else "Error"
        humidity_text = f"{humidity}%" if humidity is not None else "Error"
        
        uptime = sensors['timestamp'] // 1000
        reason = sensors.get('control_reason', 'Unknown')
        overrides = sensors.get('manual_overrides', {})
        
        override_status = ""
        logic_box_class = "logic-box"
        if any(overrides.values()):
            active_overrides = []
            for k, v in overrides.items():
                if v:
                    override_name = str(k).replace('_', ' ')
                    override_name = override_name.upper()
                    active_overrides.append(override_name)
            
            if active_overrides:
                override_status = f"<br><strong>Manual Overrides Active:</strong> {', '.join(active_overrides)}"
                logic_box_class += " override-active"
        
        html = """<!DOCTYPE html>
<html>
<head>
    <title>Enhanced Storm Sensor System</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { font-family: Arial, sans-serif; margin: 0; padding: 20px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; }
        .container { max-width: 700px; margin: 0 auto; background: rgba(255,255,255,0.95); padding: 30px; border-radius: 15px; box-shadow: 0 8px 32px rgba(0,0,0,0.3); color: #333; }
        .header { text-align: center; margin-bottom: 30px; }
        .sensor { padding: 20px; margin: 10px 0; border-radius: 10px; display: flex; justify-content: space-between; align-items: center; font-size: 18px; font-weight: bold; }
        .sensor-active { background: linear-gradient(135deg, #4CAF50, #45a049); color: white; box-shadow: 0 4px 15px rgba(76, 175, 80, 0.4); }
        .sensor-inactive { background: linear-gradient(135deg, #f44336, #da190b); color: white; box-shadow: 0 4px 15px rgba(244, 67, 54, 0.4); }
        .controls { text-align: center; margin: 30px 0; }
        .control-section { margin: 20px 0; padding: 20px; background: #f8f9fa; border-radius: 10px; }
        .btn { padding: 12px 24px; margin: 5px; border: none; border-radius: 8px; cursor: pointer; font-size: 16px; font-weight: bold; transition: transform 0.2s, box-shadow 0.2s; }
        .btn:hover { transform: translateY(-2px); box-shadow: 0 4px 12px rgba(0,0,0,0.2); }
        .btn-on { background: #4CAF50; color: white; }
        .btn-off { background: #f44336; color: white; }
        .btn-test { background: #FF9800; color: white; }
        .btn-refresh { background: #2196F3; color: white; }
        .status-bar { margin-top: 30px; padding: 20px; border-top: 3px solid #eee; font-size: 14px; color: #666; background: #f8f9fa; border-radius: 10px; }
        .logic-box { background: #e3f2fd; padding: 15px; border-radius: 8px; margin: 15px 0; border-left: 4px solid #2196F3; }
        .override-active { background: #fff3e0; border-left: 4px solid #FF9800; }
        .pin-info { background: #fff3e0; padding: 10px; border-radius: 5px; font-size: 12px; margin: 10px 0; }
        .weather-info { background: #e8f5e8; padding: 15px; border-radius: 8px; margin: 15px 0; border-left: 4px solid #4CAF50; }
        .weather-data { display: flex; justify-content: space-between; margin: 10px 0; }
        .weather-value { font-weight: bold; color: #2e7d32; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Enhanced Storm Sensor System</h1>
            <p>Smart Antenna Control with Weather Monitoring</p>
            <div class="pin-info">
                <strong>Hardware:</strong> LEDs on pins 0, 2, 15 (LOW = ON) | Antenna on pin """ + str(ANTENNA_PIN) + """ | DHT11 on pin """ + str(DHT11_PIN) + """
            </div>
        </div>
        
        <div class="sensor """ + presence_class + """">
            <span>Person Detected</span>
            <span>""" + presence_text + """</span>
        </div>
        
        <div class="sensor """ + storm_class + """">
            <span>Storm Detected</span>
            <span>""" + storm_text + """</span>
        </div>
        
        <div class="sensor """ + clouds_class + """">
            <span>Poor Weather (DHT11)</span>
            <span>""" + clouds_text + """</span>
        </div>
        
        <div class="sensor """ + antenna_class + """">
            <span>Antenna Status</span>
            <span>""" + antenna_text + """</span>
        </div>
        
        <div class="sensor """ + on_air_class + """">
            <span>On Air Status</span>
            <span>""" + on_air_text + """</span>
        </div>
        
        <div class="weather-info">
            <h3 style="margin-top: 0;">DHT11 Weather Data</h3>
            <div class="weather-data">
                <span>Temperature:</span>
                <span class="weather-value">""" + temp_text + """</span>
            </div>
            <div class="weather-data">
                <span>Humidity:</span>
                <span class="weather-value">""" + humidity_text + """</span>
            </div>
            <div style="margin-top: 10px; font-size: 14px; font-style: italic;">
                """ + weather_status + """
            </div>
        </div>
        
        <div class=\"""" + logic_box_class + """\">
            <strong>Current Logic:</strong> """ + reason + override_status + """
        </div>
        
        <div class="controls">
            <div class="control-section">
                <h3>Antenna Control</h3>
                <button class="btn btn-on" onclick="controlDevice('antenna', 'on')">Connect Antenna</button>
                <button class="btn btn-off" onclick="controlDevice('antenna', 'off')">Disconnect Antenna</button>
            </div>
            
            <div class="control-section">  
                <h3>LED Control (Persistent - LOW = ON)</h3>
                <button class="btn btn-test" onclick="controlDevice('storm_led', 'on')">Storm LED ON (pin 0)</button>
                <button class="btn btn-test" onclick="controlDevice('storm_led', 'off')">Storm LED OFF</button>
                <br>
                <button class="btn btn-test" onclick="controlDevice('clouds_led', 'on')">Weather LED ON (pin 2)</button>
                <button class="btn btn-test" onclick="controlDevice('clouds_led', 'off')">Weather LED OFF</button>
                <br>
                <button class="btn btn-test" onclick="controlDevice('on_air_led', 'on')">On Air LED ON (pin 15)</button>
                <button class="btn btn-test" onclick="controlDevice('on_air_led', 'off')">On Air LED OFF</button>
                <br>
                <button class="btn btn-test" onclick="controlDevice('test_all', '')">Test All Outputs</button>
                <button class="btn btn-test" onclick="controlDevice('test_individual', '')">Test Individual LEDs</button>
            </div>
            
            <div class="control-section">
                <h3>System Control</h3>
                <button class="btn btn-refresh" onclick="location.reload()">Refresh Status</button>
                <button class="btn btn-test" onclick="controlDevice('reset_overrides', '')">Reset Manual Overrides</button>
            </div>
        </div>
        
        <div class="status-bar">
            <h4>System Information</h4>
            <p><strong>IP Address:</strong> """ + str(self.ip_address) + """</p>
            <p><strong>Uptime:</strong> """ + str(uptime) + """ seconds</p>
            <p><strong>Pin Configuration (DHT11 INTEGRATION):</strong></p>
            <ul style="text-align: left; margin: 10px 0; font-size: 12px;">
                <li>Storm LED: GPIO """ + str(LED1_PIN) + """ (LOW = ON)</li>
                <li>Clouds LED: GPIO """ + str(LED2_PIN) + """ (LOW = ON)</li>
                <li>On Air LED: GPIO """ + str(LED3_PIN) + """ (LOW = ON)</li>
                <li>Antenna Relay: GPIO """ + str(ANTENNA_PIN) + """ (HIGH = ON)</li>
                <li>DHT11 Sensor: GPIO """ + str(DHT11_PIN) + """ (Temp & Humidity)</li>
            </ul>
            <p><strong>Weather Thresholds:</strong></p>
            <ul style="text-align: left; margin: 10px 0; font-size: 12px;">
                <li>Poor Weather: Humidity >""" + str(self.humidity_threshold) + """% OR Temp <""" + str(self.temp_min) + """°C OR >""" + str(self.temp_max) + """°C</li>
                <li>Good Weather: Normal temp/humidity ranges</li>
            </ul>
            <p><strong>Control Logic:</strong></p>
            <ul style="text-align: left; margin: 10px 0;">
                <li><strong>Storm = Antenna OFF</strong> (safety first!)</li>
                <li><strong>No Person = Antenna OFF</strong> (no need)</li>
                <li><strong>Person + No Storm = Antenna ON</strong> (even if cloudy)</li>
            </ul>
            <p><strong>Manual Override System:</strong></p>
            <ul style="text-align: left; margin: 10px 0; font-size: 12px;">
                <li>Manual LED/antenna control persists until reset</li>
                <li>Overridden components ignore sensor readings</li>
                <li>Use "Reset Manual Overrides" to return to automatic</li>
            </ul>
        </div>
    </div>
    
    <script>
        function controlDevice(device, action) {
            let url = '';
            if (device === 'antenna') {
                url = '/antenna/' + action;
            } else if (device.includes('led')) {
                url = '/led/' + device.replace('_led', '') + '/' + action;
            } else if (device === 'test_all') {
                url = '/test/outputs';
            } else if (device === 'test_individual') {
                url = '/test/individual';
            } else if (device === 'reset_overrides') {
                url = '/reset/overrides';
            }
            
            if (url) {
                fetch(url)
                    .then(response => response.text())
                    .then(result => {
                        console.log('Control result:', result);
                        setTimeout(() => location.reload(), 500);
                    })
                    .catch(err => console.log('Control error:', err));
            }
        }
        
        // Auto-refresh every 3 seconds
        setInterval(() => location.reload(), 3000);
    </script>
</body>
</html>"""
        return html
    
    def handle_request(self, client_socket):
        """Handle HTTP requests with new endpoints"""
        try:
            request = client_socket.recv(1024).decode('utf-8')
            if not request:
                return
            
            # Parse request path
            request_line = request.split('\r\n')[0]
            if ' ' in request_line:
                parts = request_line.split(' ')
                if len(parts) >= 2:
                    path = parts[1]
                else:
                    path = '/'
            else:
                path = '/'
            
            # Update sensors and logic
            sensors = self.update_logic()
            
            # Route handling
            if path == '/':
                html = self.generate_html(sensors)
                response = "HTTP/1.1 200 OK\r\nContent-Type: text/html\r\nConnection: close\r\n\r\n" + html
                
            elif path == '/antenna/on':
                self.control_antenna(True)
                response = "HTTP/1.1 200 OK\r\nContent-Type: text/plain\r\nConnection: close\r\n\r\nAntenna Connected"
                
            elif path == '/antenna/off':
                self.control_antenna(False)
                response = "HTTP/1.1 200 OK\r\nContent-Type: text/plain\r\nConnection: close\r\n\r\nAntenna Disconnected"
                
            elif path == '/led/storm/on':
                self.control_led('storm', True)
                response = "HTTP/1.1 200 OK\r\nContent-Type: text/plain\r\nConnection: close\r\n\r\nStorm LED ON"
                
            elif path == '/led/storm/off':
                self.control_led('storm', False)
                response = "HTTP/1.1 200 OK\r\nContent-Type: text/plain\r\nConnection: close\r\n\r\nStorm LED OFF"
                
            elif path == '/led/clouds/on':
                self.control_led('clouds', True)
                response = "HTTP/1.1 200 OK\r\nContent-Type: text/plain\r\nConnection: close\r\n\r\nClouds LED ON"
                
            elif path == '/led/clouds/off':
                self.control_led('clouds', False)
                response = "HTTP/1.1 200 OK\r\nContent-Type: text/plain\r\nConnection: close\r\n\r\nClouds LED OFF"
                
            elif path == '/led/on_air/on':
                self.control_led('on_air', True)
                response = "HTTP/1.1 200 OK\r\nContent-Type: text/plain\r\nConnection: close\r\n\r\nOn Air LED ON"
                
            elif path == '/led/on_air/off':
                self.control_led('on_air', False)
                response = "HTTP/1.1 200 OK\r\nContent-Type: text/plain\r\nConnection: close\r\n\r\nOn Air LED OFF"
                
            elif path == '/test/outputs':
                self.test_all_outputs()
                response = "HTTP/1.1 200 OK\r\nContent-Type: text/plain\r\nConnection: close\r\n\r\nOutput test completed"
                
            elif path == '/test/individual':
                self.test_individual_leds()
                response = "HTTP/1.1 200 OK\r\nContent-Type: text/plain\r\nConnection: close\r\n\r\nIndividual LED test completed"
                
            elif path == '/reset/overrides':
                self.reset_manual_overrides()
                response = "HTTP/1.1 200 OK\r\nContent-Type: text/plain\r\nConnection: close\r\n\r\nManual overrides reset - back to automatic"
                
            elif path == '/api/status':
                json_data = json.dumps(sensors)
                response = "HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nConnection: close\r\n\r\n" + json_data
                
            else:
                response = "HTTP/1.1 404 NOT FOUND\r\nContent-Type: text/plain\r\nConnection: close\r\n\r\n404 - Not Found"
            
            client_socket.send(response.encode('utf-8'))
            
        except Exception as e:
            print(f"Request handling error: {e}")
            try:
                error_response = "HTTP/1.1 500 INTERNAL SERVER ERROR\r\nConnection: close\r\n\r\nServer Error"
                client_socket.send(error_response.encode('utf-8'))
            except:
                pass
        finally:
            try:
                client_socket.close()
            except:
                pass
    
    def run_server(self):
        """Start the enhanced web server"""
        if not self.connect_wifi():
            return False
        
        try:
            server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server_socket.bind(('', 80))
            server_socket.listen(1)
            
            print(f"Enhanced Storm Sensor running at http://{self.ip_address}")
            print("Server ready! Auto-running on boot...")
            print("Press Ctrl+C to stop server")
            
            while True:
                try:
                    gc.collect()  # Free memory periodically
                    client_socket, client_addr = server_socket.accept()
                    self.handle_request(client_socket)
                except OSError as e:
                    if e.args[0] == 4:  # Ctrl+C
                        print("Server stopped by user")
                        break
                except Exception as e:
                    print(f"Server error: {e}")
                    continue
                    
        except Exception as e:
            print(f"Server startup error: {e}")
        finally:
            try:
                server_socket.close()
            except:
                pass
        
        return True

# Auto-start function for boot
def auto_start():
    """Auto-start function - runs when ESP32 boots"""
    try:
        print("Auto-starting Enhanced Storm Sensor...")
        system = EnhancedStormSensor()
        
        # Test all outputs briefly on startup
        print("Quick startup test...")
        system.test_all_outputs()
        
        # Start the server
        system.run_server()
        
    except KeyboardInterrupt:
        print("Startup interrupted by user")
    except Exception as e:
        print(f"Auto-start error: {e}")
        # Blink all LEDs to show error
        try:
            for i in range(10):
                system.storm_led.value(0)
                system.clouds_led.value(0) 
                system.on_air_led.value(0)
                time.sleep(0.1)
                system.storm_led.value(1)
                system.clouds_led.value(1)
                system.on_air_led.value(1)
                time.sleep(0.1)
        except:
            pass

# Main execution - Always auto-start when saved as main.py
def main():
    """Main function - auto-starts the storm sensor system"""
    system = EnhancedStormSensor()
    system.run_server()

# Auto-start immediately when this file runs
print("=== AUTO-STARTING STORM SENSOR SYSTEM ===")
auto_start()

if __name__ == "__main__":
    main()