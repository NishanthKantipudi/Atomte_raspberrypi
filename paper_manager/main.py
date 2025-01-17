import RPi.GPIO as GPIO
from time import sleep
import time

from gpiozero import Button
from signal import pause

import threading
from statistics import mode,mean


l_s1=Button(17)
DIR1 = 18
STEP1 = 16
CW1 = 0
CWR1=1
GPIO.setup(DIR1, GPIO.OUT)
GPIO.setup(STEP1, GPIO.OUT)


TRIG = 38
ECHO = 40

DIR2 = 10
STEP2 = 8
CW2 = 0
CWR2=1
GPIO.setmode(GPIO.BOARD)
GPIO.setup(DIR2, GPIO.OUT)
GPIO.setup(STEP2, GPIO.OUT)
GPIO.setup(TRIG, GPIO.OUT)
GPIO.setup(ECHO, GPIO.IN)

def goto_home1():
	GPIO.output(DIR1, CWR1)
	while 1:
		if l_s1.is_pressed:
			print("reached")
			break
		GPIO.output(STEP1, GPIO.HIGH)
		sleep(0.000001)
		GPIO.output(STEP1, GPIO.LOW)
		sleep(0.000001)

def move_shifter_to_trays():
    GPIO.output(DIR1, CW1)
    i=0
    while 1:
        if i>0.5:
            print("reached to tray position")
            break
        GPIO.output(STEP1, GPIO.HIGH)
        sleep(0.000001)
        GPIO.output(STEP1, GPIO.LOW)
        sleep(0.000001)
        i+=0.000001
        
def measure_distance():
    GPIO.output(TRIG, True)
    time.sleep(0.00001)
    GPIO.output(TRIG, False)
    start_time=0
    end_time=0
    while GPIO.input(ECHO) == 0:
        start_time = time.time()
    while GPIO.input(ECHO) == 1:
        end_time = time.time()
    duration = end_time - start_time
    distance = (duration * 34300) / 2
    return distance
distance=0
measure_dist=True
def distance_thread_normal():
    global distance,measure_dist
    while measure_dist:
        distance=measure_distance()
        print(distance)
        time.sleep(0.1)
def distance_thread():
    global distance, measure_dist
    buffer_size = 10
    readings = []
    while measure_dist:
        current_distance = measure_distance()
        readings.append(current_distance)
        if len(readings) > buffer_size:
            readings.pop(0)
        distance = mean(readings)
        print(f"Mode Distance: {distance:.2f} cm")
        time.sleep(0.1)
def goto_home2():
    global distance,measure_dist
    distence_t=threading.Thread(target=distance_thread)
    distence_t.start()
    GPIO.output(DIR2, CW2)
    time.sleep(2)
    while 1:
        if(distance<=16 and distance>0):
            print("reached")
            measure_dist=False
            break
        GPIO.output(STEP2, GPIO.HIGH)
        sleep(0.000001)
        GPIO.output(STEP2, GPIO.LOW)
        sleep(0.000001)

def move_pulley_to(dist):
    GPIO.output(DIR2, CW2)
    while 1:
        if(distance<=dist and distance>0):
            print("reached")
            break
        GPIO.output(STEP2, GPIO.HIGH)
        sleep(0.000001)
        GPIO.output(STEP2, GPIO.LOW)
        sleep(0.000001)
def move_pulley_up_little():
    GPIO.output(DIR2, CW2)
    i=0
    while 1:
        GPIO.output(STEP2, GPIO.HIGH)
        sleep(0.000001)
        GPIO.output(STEP2, GPIO.LOW)
        sleep(0.000001)
        i+=0.000001
        if i>0.5:
            print("reached little up")
            break
def goto_home3():
     pass

def close_tray():
     pass


trays={"1":{
            "dist":16,
            "count":1
        },
        "2":{
            "dist":26,
            "count":1
        },
        "3":{
            "dist":36,
            "count":1
        },
        "4":{
            "dist":46,
            "count":1
        },
        "5":{
            "dist":56,
            "count":1
        },
        "6":{
            "dist":66,
            "count":1
        },
        "7":{
            "dist":76,
            "count":1
        },
        "8":{
            "dist":86,
            "count":1
        },
        "9":{
            "dist":96,
            "count":1
        },
        "10":{
            "dist":106,
            "count":1
        }
}
def put_paper():
    goto_home3()
    goto_home1()
    goto_home2()

    tray_no=""
    for tray,value in trays.items():
        if value["count"]>0:
            tray_no=tray
            print("tray : "+tray_no)
            break
    else:
         print("no tray available")
         return

    tray_dist=trays[tray_no]["dist"]
    move_pulley_to(tray_dist)
    move_shifter_to_trays()
    move_pulley_up_little()
    goto_home1()
    move_pulley_to(100)
    close_tray()
    trays[tray_no]["count"]-=1
    

    
        
     
     