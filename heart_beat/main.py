import time
import firebase_admin
from firebase_admin import credentials, db
import socket
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
# Logging configuration
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Firebase initialization
cred = credentials.Certificate(cwd+"/key.json")
firebase_admin.initialize_app(cred, {
    'databaseURL': 'https://skilldevelopmentapp-default-rtdb.firebaseio.com/',
    'httpTimeout':10
})

printer_ref = db.reference("Printers/"+data["code"])
e_c = 0 
def check_internet_connection():
    while True:
        try:
            logger.info("Internet connection established")
            break
        except OSError:
            logger.warning("No internet connection. Retrying in 1 second...")
            time.sleep(1)

def update_heartbeat():
    global e_c
    check_internet_connection()
    while True:
        try:
            current_time = int(time.time())
            printer_ref.child('server/heartbeat').set(current_time)
            # logger.info(current_time)
        except Exception as e:
            logger.error(f"Error updating heartbeat: {str(e)}")
        time.sleep(3)
update_heartbeat()