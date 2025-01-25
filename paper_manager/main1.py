import gpiozero
from gpiozero.pins.rpigpio import RPiGPIOFactory
import pigpio

import time
import json,os
import threading,socket
import subprocess
import firebase_admin
from firebase_admin import credentials, db,storage
import logging
cwd = os.getcwd()





servo1=gpiozero.Servo(12, pin_factory=RPiGPIOFactory())



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


def power(event):
    if(event.data):
        pass

def lock1(event):
    if(event.data):
        if(event.data):
            servo1.min()
            time.sleep(1)
            servo1.max()
            time.sleep(1)    

def lock2(event):
    # if(event.data):
    #     if(event.data):
    #         set_angle2(90)
    #     else:
    #         set_angle2(0)
    pass



listners=[]

while 1:
    try:
        for listner in listners:
            listner.close()
        listners=[]
        listner=printer_ref.child("power").listen(power)
        listners.append(listner)
        listner1=printer_ref.child("lock1").listen(lock1)
        listners.append(listner1)
        listner2=printer_ref.child("lock2").listen(lock2)
        listners.append(listner2)
        while 1:
            time.sleep(10)
            if(network_error):
                time.sleep(10)
                raise Exception("Network error")
    except Exception as e:
        logger.error(str(e))
        time.sleep(10)