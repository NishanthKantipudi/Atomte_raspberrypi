from flask import Flask, request, jsonify
from flask_cors import CORS
import subprocess
import re

app = Flask(__name__)
CORS(app)

wifi_device = "wlan0"

@app.route('/available_networks', methods=['GET'])
def get_available_networks():
    try:
        # Use nmcli to scan for available networks
        result = subprocess.run(['nmcli', '-f', 'SSID', 'dev', 'wifi', 'list'], 
                                 capture_output=True, 
                                 text=True)
        
        # Parse the output to get unique SSIDs
        if result.returncode == 0:
            # Remove the header and any duplicate networks
            networks = list(set(line.strip() for line in result.stdout.split('\n')[1:] if line.strip()))
            
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
    try:
        # Get SSID and password from request
        # ssid = request.form.get('ssid', '')
        # password = request.form.get('password', '')
        data = request.get_json()
        ssid = data.get('ssid', '')
        password = data.get('password', '')
        
        # Validate inputs
        if not ssid:
            return jsonify({
                'status': 'error',
                'message': 'SSID is required'
            }), 400
        
        # Prepare connection command
        connection_command = [
            "nmcli", 
            "dev", "wifi", 
            "connect", ssid, 
            "ifname", wifi_device
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
            # Verify IP address is obtained
            ip_result = subprocess.run(
                ['ip', 'addr', 'show', wifi_device], 
                capture_output=True, 
                text=True
            )
            
            # Extract IP address
            ip_match = re.search(r'inet (\d+\.\d+\.\d+\.\d+)', ip_result.stdout)
            ip_address = ip_match.group(1) if ip_match else 'N/A'
            
            return jsonify({
                'status': 'success',
                'message': 'Connected successfully',
                'ip_address': ip_address
            })
        else:
            return jsonify({
                'status': 'error',
                'message': result.stderr.strip()
            }), 200
    
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 200

@app.route('/connection_status', methods=['GET'])
def check_connection_status():
    try:
        # Check if connected to WiFi
        result = subprocess.run(
            ['nmcli', '-t', '-f', 'ACTIVE,SSID', 'dev', 'wifi'], 
            capture_output=True, 
            text=True
        )
        
        # Parse the output
        for line in result.stdout.split('\n'):
            if line.startswith('yes:'):
                current_ssid = line.split(':')[1]
                
                # Get IP address
                ip_result = subprocess.run(
                    ['ip', 'addr', 'show', wifi_device], 
                    capture_output=True, 
                    text=True
                )
                
                # Extract IP address
                ip_match = re.search(r'inet (\d+\.\d+\.\d+\.\d+)', ip_result.stdout)
                ip_address = ip_match.group(1) if ip_match else 'N/A'
                
                return jsonify({
                    'status': 'connected',
                    'ssid': current_ssid,
                    'ip_address': ip_address
                })
        
        return jsonify({
            'status': 'disconnected'
        })
    
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=80)

