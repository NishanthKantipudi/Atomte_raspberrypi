import time
import firebase_admin
from firebase_admin import credentials, db,storage
import logging
import json,os
import threading
import subprocess
cwd = os.getcwd()
import socket

def read_json_file(file_path):
    with open(file_path, 'r') as file:
        data = json.load(file)
        return data
data = read_json_file(cwd+"/../secrets/details.json")
# Logging configuration
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Firebase initialization
cred = credentials.Certificate(cwd+"/secrets/key.json")
firebase_admin.initialize_app(cred, {
    'databaseURL': 'https://skilldevelopmentapp-default-rtdb.firebaseio.com/',
    'storageBucket': 'skilldevelopmentapp.appspot.com',
    'httpTimeout':10
})
bucket = storage.bucket()
network_error=False
def check_network():
    global network_error
    network_error=False
    while 1:
        try:
            socket.create_connection(("8.8.8.8", 53))
            network_error=False
            time.sleep(10)
        except Exception as e:
            network_error=True
            logger.error("check network error : "+str(e))
            time.sleep(5)
server_thread1 = threading.Thread(target=check_network)
server_thread1.daemon = True
server_thread1.start()


printer_ref = db.reference("Printers/"+data["code"])
def upload_file_to_firebase(file_path, firebase_path):
    blob = bucket.blob(firebase_path)
    blob.upload_from_filename(file_path)
    blob.make_public()
    print(f"File {file_path} uploaded to {firebase_path} successfully!")
    print(f"Public URL: {blob.public_url}")
def restart_raspberry_pi():
    try:
        # Run the reboot command
        printer_ref.child("restart").set(False)
        subprocess.run(['sudo', 'reboot'], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Failed to restart Raspberry Pi: {e}")
def run_command(command, log_file):
    with open(log_file, 'a') as log:
        log.write(f"\n=== Reboot Triggered at {time.strftime('%Y-%m-%d %H:%M:%S')} ===\n")
        process = subprocess.Popen(command, shell=True, stdout=log, stderr=subprocess.STDOUT)
        process.communicate()
def sendlogs(event):
    if(event.data):
        files={
            "device_manager/printer_restart.log": f"logs/{data["code"]}/device_manager/printer_restart.log",
            "device_manager/restart_device.log": f"logs/{data["code"]}/device_manager/restart_device.log",
            "heart_beat/main.log": f"logs/{data["code"]}/heart_beat/main.log",
            "setup_printer/main.log": f"logs/{data["code"]}/setup_printer/main.log",
            "setup_wifi/main.log": f"logs/{data["code"]}/setup_wifi/main.log",
            "printer_manager/files_from_server.log": f"logs/{data["code"]}/printer_manager/files_from_server.log",
            "printer_manager/prints_manager_for_private.log": f"logs/{data["code"]}/printer_manager/prints_manager_for_private.log",
            "printer_manager/prints_manager_for_public.log": f"logs/{data["code"]}/printer_manager/prints_manager_for_public.log",
        }
        try:
            for file_path, firebase_path in files.items():
                upload_file_to_firebase(file_path, firebase_path)
            printer_ref.child("getlogs").set(False)
        except Exception as e:
            logger.error(str(e))
def restart(event):
    if(event.data):
        restart_raspberry_pi()

def restart_printer(event):
    if(event.data):
        try:
            run_command(cwd + "../venv/bin/python3 device_manager/printer_restart.py", cwd+"/device_manager/printer_restart.log")
        except Exception as e:
            logger.error(str(e))

def reload_website(event):
    if(event.data):
        try:
            run_command(cwd + "../venv/bin/python3 device_manager/printer_restart.py", cwd+"/device_manager/printer_restart.log")
        except Exception as e:
            logger.error(str(e))
listners=[]

while 1:
    try:
        for listner in listners:
            listner.close()
        listners=[]
        listner=printer_ref.child("restart").listen(restart)
        listners.append(listner)
        listner1=printer_ref.child("getlogs").listen(sendlogs)
        listners.append(listner1)
        listner2=printer_ref.child("restart_printer").listen(restart_printer)
        listners.append(listner2)
        listner3=printer_ref.child("website_active").listen(reload_website)
        listners.append(listner3)
        while 1:
            time.sleep(10)
            if(network_error):
                time.sleep(10)
                raise Exception("Network error")
    except Exception as e:
        logger.error(str(e))
        time.sleep(10)
