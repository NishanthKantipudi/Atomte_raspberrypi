import os
import json
import time
import socket
import logging
import threading
import subprocess
import datetime
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

# Upload logs to Firebase Storage
def upload_file_to_firebase(local_path, firebase_path):
    try:
        blob = bucket.blob(firebase_path)
        blob.upload_from_filename(local_path)
        blob.make_public()
        logger.info(f"Uploaded {local_path} to {firebase_path}")
    except Exception as e:
        logger.error(f"Upload failed ({local_path}): {e}")

def send_logs(event):
    if not event.data:
        return

    log_files = {
        "device_manager/printer_restart.log": f"logs/{data['code']}/device_manager/printer_restart.log",
        "device_manager/restart_device.log": f"logs/{data['code']}/device_manager/restart_device.log",
        "heart_beat/main.log": f"logs/{data['code']}/heart_beat/main.log",
        "setup_printer/main.log": f"logs/{data['code']}/setup_printer/main.log",
        "setup_wifi/main.log": f"logs/{data['code']}/setup_wifi/main.log",
        "printer_manager/files_from_server.log": f"logs/{data['code']}/printer_manager/files_from_server.log",
        "printer_manager/prints_manager_for_private.log": f"logs/{data['code']}/printer_manager/prints_manager_for_private.log",
        "printer_manager/prints_manager_for_public.log": f"logs/{data['code']}/printer_manager/prints_manager_for_public.log",
        "run/main.log": f"logs/{data['code']}/run/main.log",
    }

    try:
        for local_path, firebase_path in log_files.items():
            if os.path.exists(local_path):
                upload_file_to_firebase(local_path, firebase_path)
        printer_ref.child("getlogs").set(False)
    except Exception as e:
        logger.error(f"Error uploading logs: {e}")

# Restart Raspberry Pi
def restart_raspberry_pi():
    try:
        printer_ref.child("restart").set(False)
        subprocess.run(['sudo', 'reboot'], check=True)
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to reboot: {e}")

def restart_pi_listener(event):
    if event.data:
        restart_raspberry_pi()

# Generic function to run Python commands and log
def run_command(command, log_file):
    with open(log_file, 'a') as log:
        log.write(f"\n=== Triggered at {time.strftime('%Y-%m-%d %H:%M:%S')} ===\n")
        process = subprocess.Popen(command, shell=True, stdout=log, stderr=subprocess.STDOUT)
        process.communicate()

# Restart printer listener
def restart_printer_listener(event):
    if event.data:
        try:
            script_path = os.path.join(cwd, "../venv/bin/python3 device_manager/printer_restart_ir4245.py")
            log_path = os.path.join(cwd, "device_manager/printer_restart.log")
            run_command(script_path, log_path)
            printer_ref.child("printer_restart").set(False)
        except Exception as e:
            logger.error(f"Error restarting printer: {e}")

# Website reload listener (same command reused)
def reload_website_listener(event):
    if event.data:
        try:
            script_path = os.path.join(cwd, "../venv/bin/python3 device_manager/printer_restart.py")
            log_path = os.path.join(cwd, "device_manager/printer_restart.log")
            run_command(script_path, log_path)
        except Exception as e:
            logger.error(f"Error reloading website: {e}")


def take_screenshot_and_upload(event):
    if not event.data:
        return
    screenshot_path = "~/screenshot.png"

    # Take screenshot
    os.system(f"sudo fbgrab {screenshot_path}")

    # Upload to Firebase Storage
    now = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    blob = bucket.blob(f"screenshots/screenshot_{now}.png")
    blob.upload_from_filename(screenshot_path)
    blob.make_public()  # optional: makes the file publicly accessible

    url = blob.public_url
    print("Uploaded screenshot URL:", url)

    # Save URL in Realtime Database
    db.reference("screenshots/latest").set(url)
    printer_ref.child("screenshot").set(False)

# Launch background network thread
network_thread = threading.Thread(target=check_network, daemon=True)
network_thread.start()

# Main listener loop
def firebase_listener_loop():
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
            listners.append(printer_ref.child("restart").listen(restart_pi_listener))
            listners.append(printer_ref.child("getlogs").listen(send_logs))
            listners.append(printer_ref.child("printer_restart").listen(restart_printer_listener))
            # Uncomment when needed
            # listners.append(printer_ref.child("restart_printer").listen(restart_printer_listener))
            # listners.append(printer_ref.child("reload_website").listen(reload_website_listener))

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

