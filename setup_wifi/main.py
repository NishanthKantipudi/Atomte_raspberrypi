from flask import Flask, request, jsonify
from flask_cors import CORS
import subprocess
import re
import os
import json
import firebase_admin
from firebase_admin import credentials, db

app = Flask(__name__)
CORS(app)

# Constants
WIFI_DEVICE = "wlan0"
CWD = os.getcwd()

# Load configuration
with open(CWD + "/../secrets/details.json", "r") as f:
    CONFIG = json.load(f)

# Firebase initialization
def init_firebase():
    if not firebase_admin._apps:
        cred = credentials.Certificate(CWD + "/secrets/key.json")
        firebase_admin.initialize_app(cred, {
            'databaseURL': 'https://skilldevelopmentapp-default-rtdb.firebaseio.com/',
            'httpTimeout': 10
        })

# Helper functions
def get_ip_address():
    """Get the IP address of the WiFi device"""
    ip_result = subprocess.run(
        ['ip', 'addr', 'show', WIFI_DEVICE], 
        capture_output=True, 
        text=True
    )
    
    ip_match = re.search(r'inet (\d+\.\d+\.\d+\.\d+)', ip_result.stdout)
    return ip_match.group(1) if ip_match else None

def update_firebase_ip(ip_address):
    """Update the IP address in Firebase"""
    init_firebase()
    db.reference('/').child("Printers").child(CONFIG["code"]).child("details").child("device_ip").set(ip_address)

# Routes
@app.route('/check_printer', methods=['POST'])
def check_printer():
    """Get a list of available WiFi networks"""
    try:
        printer_id = request.get_json().get('printer_id', '')
        
        if CONFIG["code"] == printer_id:
            return jsonify({
                'status': 'success'
            })
        else:
            return jsonify({
                'status': 'error'
            }), 500
    
    except Exception as e:
        return jsonify({
            'status': 'error'
        }), 500

@app.route('/get_printer_code', methods=['GET'])
def get_printer_code():
    return jsonify({"code": CONFIG["code"]}), 200

@app.route('/available_networks', methods=['GET'])
def get_available_networks():
    """Get a list of available WiFi networks"""
    try:
        result = subprocess.run(
            ['nmcli', '-f', 'SSID', 'dev', 'wifi', 'list'], 
            capture_output=True, 
            text=True
        )
        
        if result.returncode == 0:
            # Extract unique SSIDs from the output, skipping the header line
            networks = list(set(line.strip() for line in result.stdout.split('\n')[1:] 
                             if line.strip()))
            
            return jsonify({
                'status': 'success',
                'networks': networks
            })
        else:
            return jsonify({
                'status': 'error',
                'message': result.stderr.strip()
            }), 500
    
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/connect_to_wifi', methods=['POST'])
def connect_wifi():
    """Connect to a WiFi network"""
    try:
        # Get SSID and password from JSON request
        data = request.get_json()
        ssid = data.get('ssid', '')
        password = data.get('password', '')
        
        # Validate inputs
        if not ssid:
            return jsonify({
                'status': 'error',
                'message': 'SSID is required'
            }), 400
        
        # Construct connection command
        connection_command = [
            "nmcli", "dev", "wifi", 
            "connect", ssid, 
            "ifname", WIFI_DEVICE
        ]
        
        # Add password if provided
        if password:
            connection_command.extend(['password', password])
        
        # Execute connection command
        result = subprocess.run(
            connection_command, 
            capture_output=True, 
            text=True
        )
        
        # Check connection result
        if result.returncode == 0:
            # Get and update IP address
            ip_address = get_ip_address()
            
            if ip_address:
                update_firebase_ip(ip_address)
                
                return jsonify({
                    'status': 'success',
                    'message': 'Connected successfully',
                    'ip_address': ip_address
                })
            else:
                return jsonify({
                    'status': 'warning',
                    'message': 'Connected but no IP address obtained'
                })
        else:
            return jsonify({
                'status': 'error',
                'message': result.stderr.strip()
            }), 200  # Using 200 to ensure client receives the error message
    
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 200

@app.route('/connection_status', methods=['GET'])
def check_connection_status():
    """Check the current WiFi connection status"""
    try:
        # Check active connections
        result = subprocess.run(
            ['nmcli', '-t', '-f', 'ACTIVE,SSID', 'dev', 'wifi'], 
            capture_output=True, 
            text=True
        )
        
        # Parse output for active connection
        for line in result.stdout.split('\n'):
            if line.startswith('yes:'):
                current_ssid = line.split(':')[1]
                ip_address = get_ip_address()
                
                return jsonify({
                    'status': 'connected',
                    'ssid': current_ssid,
                    'ip_address': ip_address or 'N/A'
                })
        
        # No active connection found
        return jsonify({
            'status': 'disconnected',
            'message': 'Not connected to WiFi'
        })
    
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=80)