import time
import firebase_admin
from firebase_admin import credentials, db
import socket,subprocess
import logging
import asyncio
import websockets
import json,os
cwd = os.getcwd()

def read_json_file(file_path):
    with open(file_path, 'r') as file:
        data = json.load(file)
        return data
data = read_json_file(cwd+"/../secrets/details.json")

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


cred = credentials.Certificate(cwd+"/secrets/key.json")
firebase_admin.initialize_app(cred, {
    'databaseURL': 'https://skilldevelopmentapp-default-rtdb.firebaseio.com/',
    'httpTimeout':10
})

printer_ref = db.reference("Printers/"+data["code"])


PRINTER_CODE = data["code"]

def execute_command(event):
    command = event.data
    if command:
        try:
            # Execute the command
            result = subprocess.run(command, shell=True, capture_output=True, text=True)
            output = result.stdout if result.stdout else result.stderr
        except Exception as e:
            output = f"Error: {str(e)}"
        
        # Store the output back in Firebase
        output_ref = db.reference(f"Printers/{PRINTER_CODE}/execute/output")
        output_ref.set(output)

# Reference to the command node
command_ref = db.reference(f"Printers/{PRINTER_CODE}/execute/code")

# Start listening for changes
listner=command_ref.listen(execute_command)

# Keep the script running
import time
while True:
    time.sleep(10)
    if(listner._thread.is_alive()):
        continue
    else:
        listner=command_ref.listen(execute_command)
