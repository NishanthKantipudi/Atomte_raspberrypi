import RPi.GPIO as GPIO
import pigpio

import time
import json,os
import threading
import subprocess
import firebase_admin
from firebase_admin import credentials, db,storage
import logging
cwd = os.getcwd()



# servo1_pin = 12
# servo2_pin = 13
# GPIO.setmode(GPIO.BCM)
# GPIO.setup(servo1_pin, GPIO.OUT)
# pwm1 = GPIO.PWM(servo1_pin, 50)
# pwm1.start(0)

# GPIO.setup(servo2_pin, GPIO.OUT)
# pwm2 = GPIO.PWM(servo2_pin, 50)
# pwm2.start(0)

# def set_angle1(angle):
#     duty = 2 + (angle / 18)
#     GPIO.output(servo1_pin, True)
#     pwm1.ChangeDutyCycle(duty)
#     time.sleep(0.5)
#     GPIO.output(servo1_pin, False)
#     pwm1.ChangeDutyCycle(0)

# def set_angle2(angle):
#     duty = 2 + (angle / 18)
#     GPIO.output(servo2_pin, True)
#     pwm2.ChangeDutyCycle(duty)
#     time.sleep(0.5)
#     GPIO.output(servo2_pin, False)
#     pwm2.ChangeDutyCycle(0)


servo_pin = 12  # GPIO 0 (BCM)

# Initialize pigpio
pi = pigpio.pi()

if not pi.connected:
    print("Could not connect to pigpio daemon")
    exit()

# Set servo pulse range
pi.set_servo_pulsewidth(servo_pin, 0)


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
            try:
                while True:
                    # Move servo to 0 degrees
                    pi.set_servo_pulsewidth(servo_pin, 1000)  # 1000 µs pulse
                    time.sleep(2)

                    # Move servo to 90 degrees
                    pi.set_servo_pulsewidth(servo_pin, 1500)  # 1500 µs pulse
                    time.sleep(2)

                    # Move servo to 180 degrees
                    pi.set_servo_pulsewidth(servo_pin, 2000)  # 2000 µs pulse
                    time.sleep(2)
            except KeyboardInterrupt:
                pi.set_servo_pulsewidth(servo_pin, 0)  # Stop servo
                pi.stop()  # Stop pigpio daemon       

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