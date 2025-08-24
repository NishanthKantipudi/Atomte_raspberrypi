import os
import json
import time
import socket
import logging
import threading
import subprocess

import requests,shutil

import firebase_admin
from firebase_admin import credentials, db, storage

# Setup
cwd = os.getcwd()
CONFIG_PATH = os.path.join(cwd, "../secrets/details.json")
CRED_PATH = os.path.join(cwd, "secrets/key.json")
KEY_PATH = "/dev/shm/atomte_secrets.json"


# Load configuration
def read_json_file(file_path):
    with open(file_path, 'r') as file:
        return json.load(file)

data = read_json_file(CONFIG_PATH)

# Logging configuration
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Firebase initialization
cred = credentials.Certificate(KEY_PATH)
firebase_admin.initialize_app(cred, {
    'databaseURL': 'https://skilldevelopmentapp-default-rtdb.firebaseio.com/',
    'storageBucket': 'skilldevelopmentapp.appspot.com',
    'httpTimeout': 10
})
bucket = storage.bucket()
printer_ref = db.reference(f"Printers/{data['code']}")

# Global flag
network_error = False
PAMPLETS_FOLDER = cwd + '/ads_manager/pamplets'
# Monitor network connectivity
def check_network():
    global network_error
    while True:
        try:
            socket.create_connection(("8.8.8.8", 53), timeout=5)
            network_error = False
        except Exception as e:
            network_error = True
            logger.error(f"Network check failed: {e}")
        time.sleep(10 if not network_error else 5)

def download_file(url, filename):
    try:
        filepath = os.path.join(PAMPLETS_FOLDER, filename)
        with requests.get(url, stream=True, timeout=30) as r:
            r.raise_for_status()
            with open(filepath, 'wb') as f:
                shutil.copyfileobj(r.raw, f)  # faster streaming
        logger.info(f"Downloaded: {filename}")
        return True
    except requests.exceptions.RequestException as e:
        logger.error(f"Network error downloading {url}: {e}")
        return False
    except Exception as e:
        logger.error(f"Failed to download {url}: {e}")
        return False

def check_pamplets(event):
    if(event.data):
        pamplets_data=printer_ref.child("pamplets_data").get()
        for key,value in pamplets_data:
            download_file(value,key+".pdf")



# Launch background network thread
network_thread = threading.Thread(target=check_network, daemon=True)
network_thread.start()

# Main listener loop
def firebase_listener_loop():
    os.makedirs(PAMPLETS_FOLDER, exist_ok=True)
    listners = []
    while True:
        try:
            # Close old listeners
            for l in listners:
                try:
                    l.close()
                except Exception as e:
                    logger.warning(f"Listener close failed: {e}")
            listners.clear()

            # Add new listeners
            listners.append(printer_ref.child("check_pamplets").listen(restart_pi_listener))
            
            while True:
                time.sleep(10)
                if network_error:
                    raise Exception("Network error detected")
                for listener in listners:
                    if not listener._thread.is_alive():
                        raise Exception("Listener thread dead")

        except Exception as e:
            logger.error(f"Listener loop error: {e}")
            time.sleep(30)

# Run main loop
if __name__ == "__main__":
    firebase_listener_loop()