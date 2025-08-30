"""
Enhanced ESP32 Storm Sensor System
- Person detection, storm detection, cloud detection
- Multiple LEDs for different conditions
- Smart antenna control logic
"""

import network
import socket
import machine
import time
import json

# Configuration
WIFI_SSID = "YourWiFiName"
WIFI_PASSWORD = "YourWiFiPassword"

# Pin Configuration
# INPUTS (Sensors)
PIR_PIN = 4          # Person presence sensor (HIGH = person detected)
STORM_PIN = 5        # Storm sensor (HIGH = storm detected) 
CLOUDS_PIN = 18      # Clouds sensor (HIGH = clouds detected)

# OUTPUTS (Controlled devices)
ANTENNA_PIN = 2      # Antenna relay (HIGH = antenna connected)
STATUS_LED_PIN = 23  # WiFi/System status LED (HIGH = system OK)
STORM_LED_PIN = 19   # Storm warning LED (HIGH = storm detected)
CLOUDS_LED_PIN = 21  # Clouds indicator LED (HIGH = clouds detected)

class EnhancedStormSensor:
    def __init__(self):
        # Setup INPUT pins (sensors)
        self.pir_sensor = machine.Pin(PIR_PIN, machine.Pin.IN)
        self.storm_sensor = machine.Pin(STORM_PIN, machine.Pin.IN, machine.Pin.PULL_UP)
        self.clouds_sensor = machine.Pin(CLOUDS_PIN, machine.Pin.IN, machine.Pin.PULL_UP)
        
        # Setup OUTPUT pins (controlled devices)
        self.antenna_relay = machine.Pin(ANTENNA_PIN, machine.Pin.OUT)
        self.status_led = machine.Pin(STATUS_LED_PIN, machine.Pin.OUT)
        self.storm_led = machine.Pin(STORM_LED_PIN, machine.Pin.OUT)
        self.clouds_led = machine.Pin(CLOUDS_LED_PIN, machine.Pin.OUT)
        
        # Initialize all outputs to OFF
        self.antenna_relay.value(0)
        self.status_led.value(0)
        self.storm_led.value(0)
        self.clouds_led.value(0)
        
        # WiFi setup
        self.wlan = network.WLAN(network.STA_IF)
        self.ip_address = None
        
        print("=== Enhanced Storm Sensor System ===")
        print(f"Pins configured:")
        print(f"  Person Sensor: GPIO {PIR_PIN}")
        print(f"  Storm Sensor: GPIO {STORM_PIN}")
        print(f"  Clouds Sensor: GPIO {CLOUDS_PIN}")
        print(f"  Antenna Relay: GPIO {ANTENNA_PIN}")
        print(f"  Status LED: GPIO {STATUS_LED_PIN}")
        print(f"  Storm LED: GPIO {STORM_LED_PIN}")
        print(f"  Clouds LED: GPIO {CLOUDS_LED_PIN}")
        
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
            self.status_led.value(1)  # Status LED ON when WiFi connected
            print(f"WiFi connected: {self.ip_address}")
            return True
        else:
            print("WiFi connection failed!")
            # Flash status LED to indicate WiFi error
            for i in range(5):
                self.status_led.value(1)
                time.sleep(0.2)
                self.status_led.value(0)
                time.sleep(0.2)
            return False
    
    def read_sensors(self):
        """Read all sensor values"""
        try:
            presence = bool(self.pir_sensor.value())
            storm = bool(self.storm_sensor.value())
            clouds = bool(self.clouds_sensor.value())
            antenna_connected = bool(self.antenna_relay.value())
            
            return {
                'presence': presence,
                'storm': storm,
                'clouds': clouds,
                'antenna_connected': antenna_connected,
                'timestamp': time.ticks_ms()
            }
        except Exception as e:
            print(f"Sensor read error: {e}")
            return {
                'presence': False,
                'storm': False,
                'clouds': False,
                'antenna_connected': False,
                'timestamp': time.ticks_ms()
            }
    
    def update_logic(self):
        """Enhanced control logic with multiple conditions"""
        try:
            sensors = self.read_sensors()
            presence = sensors['presence']
            storm = sensors['storm']
            clouds = sensors['clouds']
            
            # LED CONTROL (always show sensor states)
            self.storm_led.value(1 if storm else 0)      # Storm LED = Storm sensor
            self.clouds_led.value(1 if clouds else 0)    # Clouds LED = Clouds sensor
            # Status LED stays on if WiFi connected
            
            # ANTENNA CONTROL LOGIC - Enhanced Rules:
            # 1. Must have person present
            # 2. No storm (highest priority - dangerous!)
            # 3. Clouds are OK but maybe reduce power/sensitivity
            
            if not presence:
                # No person → antenna OFF
                should_connect = False
                reason = "No person detected"
                
            elif storm:
                # Storm detected → antenna OFF (safety first!)
                should_connect = False  
                reason = "Storm detected - safety first!"
                
            elif presence and not storm:
                # Person present + no storm = antenna ON
                # (clouds are acceptable - just weather, not dangerous)
                should_connect = True
                if clouds:
                    reason = "Person present, cloudy weather (antenna ON)"
                else:
                    reason = "Person present, clear weather (antenna ON)"
            else:
                should_connect = False
                reason = "Unknown condition"
            
            # Apply antenna control
            current_state = sensors['antenna_connected']
            if should_connect != current_state:
                self.antenna_relay.value(1 if should_connect else 0)
                print(f"Antenna {'ON' if should_connect else 'OFF'}: {reason}")
            
            # Update sensor data with reason
            sensors['control_reason'] = reason
            return sensors
            
        except Exception as e:
            print(f"Logic update error: {e}")
            return self.read_sensors()
    
    def control_antenna(self, connect, manual=True):
        """Manual antenna control"""
        try:
            self.antenna_relay.value(1 if connect else 0)
            if manual:
                print(f"Manual override: Antenna {'ON' if connect else 'OFF'}")
        except Exception as e:
            print(f"Antenna control error: {e}")
    
    def control_led(self, led_type, state):
        """Manual LED control for testing"""
        try:
            if led_type == 'storm':
                self.storm_led.value(1 if state else 0)
            elif led_type == 'clouds':
                self.clouds_led.value(1 if state else 0)
            elif led_type == 'status':
                self.status_led.value(1 if state else 0)
            print(f"{led_type.title()} LED {'ON' if state else 'OFF'}")
        except Exception as e:
            print(f"LED control error: {e}")
    
    def test_all_outputs(self):
        """Test all LEDs and antenna relay"""
        print("Testing all outputs...")
        outputs = [
            ('Status LED', self.status_led),
            ('Storm LED', self.storm_led), 
            ('Clouds LED', self.clouds_led),
            ('Antenna Relay', self.antenna_relay)
        ]
        
        for name, pin in outputs:
            print(f"  {name} ON")
            pin.value(1)
            time.sleep(1)
            print(f"  {name} OFF") 
            pin.value(0)
            time.sleep(0.5)
        
        print("Output test complete!")
    
    def generate_html(self, sensors):
        """Generate enhanced web interface"""
        presence_class = "sensor-active" if sensors['presence'] else "sensor-inactive"
        presence_text = "YES" if sensors['presence'] else "NO"
        
        storm_class = "sensor-active" if sensors['storm'] else "sensor-inactive"  
        storm_text = "YES" if sensors['storm'] else "NO"
        
        clouds_class = "sensor-active" if sensors['clouds'] else "sensor-inactive"
        clouds_text = "YES" if sensors['clouds'] else "NO"
        
        antenna_class = "sensor-active" if sensors['antenna_connected'] else "sensor-inactive"
        antenna_text = "CONNECTED" if sensors['antenna_connected'] else "DISCONNECTED"
        
        uptime = sensors['timestamp'] // 1000
        reason = sensors.get('control_reason', 'Unknown')
        
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
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Enhanced Storm Sensor System</h1>
            <p>Smart Antenna Control with Weather Monitoring</p>
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
            <span>Clouds Detected</span>
            <span>""" + clouds_text + """</span>
        </div>
        
        <div class="sensor """ + antenna_class + """">
            <span>Antenna Status</span>
            <span>""" + antenna_text + """</span>
        </div>
        
        <div class="logic-box">
            <strong>Current Logic:</strong> """ + reason + """
        </div>
        
        <div class="controls">
            <div class="control-section">
                <h3>Antenna Control</h3>
                <button class="btn btn-on" onclick="controlDevice('antenna', 'on')">Connect Antenna</button>
                <button class="btn btn-off" onclick="controlDevice('antenna', 'off')">Disconnect Antenna</button>
            </div>
            
            <div class="control-section">  
                <h3>LED Testing</h3>
                <button class="btn btn-test" onclick="controlDevice('storm_led', 'on')">Storm LED ON</button>
                <button class="btn btn-test" onclick="controlDevice('storm_led', 'off')">Storm LED OFF</button>
                <br>
                <button class="btn btn-test" onclick="controlDevice('clouds_led', 'on')">Clouds LED ON</button>
                <button class="btn btn-test" onclick="controlDevice('clouds_led', 'off')">Clouds LED OFF</button>
                <br>
                <button class="btn btn-test" onclick="controlDevice('test_all', '')">Test All Outputs</button>
            </div>
            
            <div class="control-section">
                <button class="btn btn-refresh" onclick="location.reload()">Refresh Status</button>
            </div>
        </div>
        
        <div class="status-bar">
            <h4>System Information</h4>
            <p><strong>IP Address:</strong> """ + str(self.ip_address) + """</p>
            <p><strong>Uptime:</strong> """ + str(uptime) + """ seconds</p>
            <p><strong>Control Logic:</strong></p>
            <ul style="text-align: left; margin: 10px 0;">
                <li><strong>Storm = Antenna OFF</strong> (safety first!)</li>
                <li><strong>No Person = Antenna OFF</strong> (no need)</li>
                <li><strong>Person + No Storm = Antenna ON</strong> (even if cloudy)</li>
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
                
            elif path == '/test/outputs':
                self.test_all_outputs()
                response = "HTTP/1.1 200 OK\r\nContent-Type: text/plain\r\nConnection: close\r\n\r\nOutput test completed"
                
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
            print("Ready for connections!")
            
            while True:
                try:
                    client_socket, client_addr = server_socket.accept()
                    self.handle_request(client_socket)
                except OSError as e:
                    if e.args[0] == 4:  # Ctrl+C
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

# Main execution
def main():
    system = EnhancedStormSensor()
    system.run_server()

# Create global instance for manual control
enhanced_system = EnhancedStormSensor()

# Manual commands available in Thonny:
print("\n=== Manual Control Commands ===")
print(">>> enhanced_system.read_sensors()           # Read all sensors")
print(">>> enhanced_system.update_logic()           # Run control logic")
print(">>> enhanced_system.control_antenna(True)    # Manual antenna ON")
print(">>> enhanced_system.control_led('storm', True)  # Manual LED control")
print(">>> enhanced_system.test_all_outputs()       # Test all outputs")
print(">>> enhanced_system.run_server()             # Start web server")
print(">>> main()                                   # Auto-start everything")

if __name__ == "__main__":
    main()