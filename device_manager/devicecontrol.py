import time
import json,os
import threading,socket
import subprocess
import firebase_admin
from firebase_admin import credentials, db,storage
import logging

env = os.environ.copy()
os.environ["DISPLAY"] = ":0"
os.environ["PULSE_SERVER"] = "unix:/run/user/1000/pulse/native"
os.environ["XDG_RUNTIME_DIR"] = "/run/user/1000"
# def getcwd():
#     cwd = os.getcwd()
#     os.chdir(cwd+"/Atomte/Atomte_raspberrypi")
#     cwd = os.getcwd()
#     return cwd
# cwd=getcwd()

cwd = os.getcwd()
os.system("amixer -c 2 set 'Speaker' 100%")
def read_json_file(file_path):
    with open(file_path, 'r') as file:
        data = json.load(file)
        return data
data = read_json_file(cwd+"/../secrets/details.json")

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Firebase initialization
cred = credentials.Certificate(cwd+"/secrets/key.json")
firebase_admin.initialize_app(cred, {
    'databaseURL': 'https://skilldevelopmentapp-default-rtdb.firebaseio.com/',
    'storageBucket': 'skilldevelopmentapp.appspot.com',
    'httpTimeout':10
})

network_error=False


def run_subprocess(commands):
    try:
        logger.info(f"running: {str(commands)}...")
        result = subprocess.run(commands, 
                                cwd=cwd+"/",
                                capture_output=True, 
                                text=True)
        logger.info(f"Result: {result}")
    except Exception as e:
        logger.error(f"An error occurred during git pull: {e}")
def run_command(command, log_file):
    with open(log_file, 'a') as log:
        log.write(f"\n=== Reboot Triggered at {time.strftime('%Y-%m-%d %H:%M:%S')} ===\n")
        process = subprocess.Popen(command, shell=True, stdout=log, stderr=subprocess.STDOUT)
        process.communicate()
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

def set_volume(volume_percentage):
    try:
        os.system(f"amixer set Master {volume_percentage}%")
    except subprocess.CalledProcessError as e:
        print(f"Failed to set volume: {e}")

def audio(event):
    if(event.data):
        set_volume(event.data)

def mic(event):
    if(event.data):
        os.system(f"amixer set Capture {event.data}%")



listners=[]

while 1:
    try:
        for listner in listners:
            listner.close()
        listners=[]
        listner=printer_ref.child("audio").listen(audio)
        listners.append(listner)
        listner1=printer_ref.child("mic").listen(mic)
        listners.append(listner1)
        while 1:
            time.sleep(10)
            if(network_error):
                time.sleep(10)
                raise Exception("Network error")
            for listner in listners:
                if(listner._thread.is_alive()):
                    continue
                else:
                    raise Exception("listner error")
    except Exception as e:
        logger.error(str(e))
        time.sleep(10)