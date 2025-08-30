"""
ESP32 Storm Sensor System - Clean Version
Reads presence and storm sensors, controls antenna relay via web interface
"""

import network
import socket
import machine
import time
import json

# Configuration
WIFI_SSID = "AdrianWiFi"
WIFI_PASSWORD = "bbbbbbbb"

# Pin Configuration
PIR_PIN = 4
STORM_PIN = 5
ANTENNA_PIN = 2
LED_PIN = 23

class StormSensorSystem:
    def __init__(self):
        # Setup pins
        self.pir_sensor = machine.Pin(PIR_PIN, machine.Pin.IN)
        self.storm_sensor = machine.Pin(STORM_PIN, machine.Pin.IN, machine.Pin.PULL_UP)
        self.antenna_relay = machine.Pin(ANTENNA_PIN, machine.Pin.OUT)
        self.status_led = machine.Pin(LED_PIN, machine.Pin.OUT)
        
        # Initialize outputs
        self.antenna_relay.value(0)
        self.status_led.value(0)
        
        # WiFi connection
        self.wlan = network.WLAN(network.STA_IF)
        self.ip_address = None
        
    def connect_wifi(self):
        """Connect to WiFi network"""
        self.wlan.active(True)
        
        if not self.wlan.isconnected():
            self.wlan.connect(WIFI_SSID, WIFI_PASSWORD)
            
            timeout = 15
            while not self.wlan.isconnected() and timeout > 0:
                time.sleep(1)
                timeout -= 1
        
        if self.wlan.isconnected():
            self.ip_address = self.wlan.ifconfig()[0]
            self.status_led.value(1)
            return True
        return False
    
    def read_sensors(self):
        """Read all sensor values"""
        try:
            presence = bool(self.pir_sensor.value())
            storm = bool(self.storm_sensor.value())
            antenna_connected = bool(self.antenna_relay.value())
            
            return {
                'presence': presence,
                'storm': storm,
                'antenna_connected': antenna_connected,
                'timestamp': time.ticks_ms()
            }
        except:
            return {
                'presence': False,
                'storm': False,
                'antenna_connected': False,
                'timestamp': time.ticks_ms()
            }
    
    def update_logic(self):
        """Apply control logic"""
        try:
            sensors = self.read_sensors()
            should_connect = sensors['presence'] and not sensors['storm']
            
            if should_connect != sensors['antenna_connected']:
                self.antenna_relay.value(1 if should_connect else 0)
            
            return sensors
        except:
            return self.read_sensors()
    
    def control_antenna(self, connect):
        """Manual antenna control"""
        try:
            self.antenna_relay.value(1 if connect else 0)
        except:
            pass
    
    def generate_html(self, sensors):
        """Generate web interface HTML"""
        # Simple string building to avoid f-string issues
        presence_class = "sensor-active" if sensors['presence'] else "sensor-inactive"
        presence_text = "YES" if sensors['presence'] else "NO"
        
        storm_class = "sensor-active" if sensors['storm'] else "sensor-inactive"  
        storm_text = "YES" if sensors['storm'] else "NO"
        
        antenna_class = "sensor-active" if sensors['antenna_connected'] else "sensor-inactive"
        antenna_text = "CONNECTED" if sensors['antenna_connected'] else "DISCONNECTED"
        
        uptime = sensors['timestamp'] // 1000
        
        html = """<!DOCTYPE html>
<html>
<head>
    <title>Storm Sensor System</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { font-family: Arial, sans-serif; margin: 0; padding: 20px; background: #f5f5f5; }
        .container { max-width: 600px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
        .header { text-align: center; margin-bottom: 30px; }
        .sensor { padding: 20px; margin: 10px 0; border-radius: 8px; display: flex; justify-content: space-between; align-items: center; font-size: 18px; font-weight: bold; }
        .sensor-active { background: #4CAF50; color: white; }
        .sensor-inactive { background: #f44336; color: white; }
        .controls { text-align: center; margin: 20px 0; }
        .btn { padding: 12px 24px; margin: 0 10px; border: none; border-radius: 6px; cursor: pointer; font-size: 16px; font-weight: bold; }
        .btn-on { background: #4CAF50; color: white; }
        .btn-off { background: #f44336; color: white; }
        .btn-refresh { background: #2196F3; color: white; }
        .status-bar { margin-top: 30px; padding-top: 20px; border-top: 2px solid #eee; font-size: 14px; color: #666; text-align: center; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Storm Sensor System</h1>
            <p>Automatic Antenna Control</p>
        </div>
        
        <div class="sensor """ + presence_class + """">
            <span>Person Detected</span>
            <span>""" + presence_text + """</span>
        </div>
        
        <div class="sensor """ + storm_class + """">
            <span>Storm Detected</span>
            <span>""" + storm_text + """</span>
        </div>
        
        <div class="sensor """ + antenna_class + """">
            <span>Antenna Status</span>
            <span>""" + antenna_text + """</span>
        </div>
        
        <div class="controls">
            <h3>Manual Control</h3>
            <button class="btn btn-on" onclick="controlAntenna('on')">Connect Antenna</button>
            <button class="btn btn-off" onclick="controlAntenna('off')">Disconnect Antenna</button>
            <br><br>
            <button class="btn btn-refresh" onclick="location.reload()">Refresh Status</button>
        </div>
        
        <div class="status-bar">
            <p><strong>System IP:</strong> """ + str(self.ip_address) + """</p>
            <p><strong>Uptime:</strong> """ + str(uptime) + """ seconds</p>
            <p><strong>Logic:</strong> Antenna connects when person present AND no storm</p>
        </div>
    </div>
    
    <script>
        function controlAntenna(action) {
            fetch('/antenna/' + action)
                .then(response => response.text())
                .then(() => {
                    setTimeout(() => location.reload(), 500);
                })
                .catch(err => console.log('Control error:', err));
        }
        
        // Auto-refresh every 5 seconds
        setInterval(() => location.reload(), 5000);
    </script>
</body>
</html>"""
        return html
    
    def handle_request(self, client_socket):
        """Handle incoming HTTP requests"""
        try:
            request = client_socket.recv(1024).decode('utf-8')
            if not request:
                return
            
            # Parse request - simplified like debug version
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
            
            # Route handling - simple response building like debug version
            if path == '/':
                html = self.generate_html(sensors)
                response = "HTTP/1.1 200 OK\r\nContent-Type: text/html\r\nConnection: close\r\n\r\n" + html
                
            elif path == '/antenna/on':
                self.control_antenna(True)
                response = "HTTP/1.1 200 OK\r\nContent-Type: text/plain\r\nConnection: close\r\n\r\nAntenna Connected"
                
            elif path == '/antenna/off':
                self.control_antenna(False)
                response = "HTTP/1.1 200 OK\r\nContent-Type: text/plain\r\nConnection: close\r\n\r\nAntenna Disconnected"
                
            elif path == '/api/status' or path == '/api/sensors':
                json_data = json.dumps(sensors)
                response = "HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nConnection: close\r\n\r\n" + json_data
                
            else:
                response = "HTTP/1.1 404 NOT FOUND\r\nContent-Type: text/plain\r\nConnection: close\r\n\r\n404 - Not Found"
            
            client_socket.send(response.encode('utf-8'))
            
        except Exception as e:
            try:
                error_response = "HTTP/1.1 500 INTERNAL SERVER ERROR\r\nConnection: close\r\n\r\nError"
                client_socket.send(error_response.encode('utf-8'))
            except:
                pass
        finally:
            try:
                client_socket.close()
            except:
                pass
    
    def run_server(self):
        """Main server loop"""
        if not self.connect_wifi():
            return False
        
        try:
            server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server_socket.bind(('', 80))
            server_socket.listen(1)
            
            print(f"Storm Sensor System running at http://{self.ip_address}")
            
            while True:
                try:
                    client_socket, client_addr = server_socket.accept()
                    self.handle_request(client_socket)
                except OSError as e:
                    if e.args[0] == 4:  # Ctrl+C interrupt
                        break
                except:
                    continue
                    
        except:
            pass
        finally:
            try:
                server_socket.close()
            except:
                pass
        
        return True

# Main execution
def main():
    system = StormSensorSystem()
    system.run_server()

# Auto-start when imported as main
if __name__ == "__main__":
    main()

# For manual control in Thonny
storm_system = StormSensorSystem()

# Manual commands available:
# storm_system.connect_wifi()      # Connect to WiFi
# storm_system.read_sensors()      # Read sensor values  
# storm_system.control_antenna(True)   # Manual antenna control
# storm_system.run_server()        # Start web server