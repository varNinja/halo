#!/usr/bin/env python
import httplib, urllib
import PCF8591 as ADC
import RPi.GPIO as GPIO
import time
import math
from Queue import Queue
from threading import Thread
import subprocess
import json
from datetime import datetime
THERMISTOR = 17
GAS_SENSOR = 18
BUZZ = 6
RAIN = 13

GPIO.setmode(GPIO.BCM)

HALO_LAMBDA_URL = "https://a9a0t0l599.execute-api.us-east-1.amazonaws.com/prod/Halo"

# queue init
q = Queue(maxsize=0)

def queue_task(q):
    while True:
        updates = q.get()
        print updates
        data = {}
        data['deviceId'] = 1;
        data['updates'] = updates
        print data
        resp = subprocess.call(['curl', '-X', 'POST', '-d', json.dumps(data), HALO_LAMBDA_URL])
        print resp
        q.task_done()


def setup():
    ADC.setup(0x48)
    GPIO.setup(THERMISTOR, GPIO.IN)
    GPIO.setup(GAS_SENSOR, GPIO.IN)
    GPIO.setup(BUZZ, GPIO.OUT)
    GPIO.setup(RAIN, GPIO.OUT)
    GPIO.output(BUZZ, 1)

def print_gas(x):
    if x == 1:
        print ''
        print '   *********'
        print '   * Safe~ *'
        print '   *********'
        print ''
    if x == 0:
        print ''
        print '   ***************'
        print '   * Danger Gas! *'
        print '   ***************'
        print ''

#def

def loop():
    worker = Thread(target=queue_task, args=(q,))
    worker.setDaemon(True)
    worker.start()
    status = 1
    count = 0
    q_count = 0
    now = datetime.now()
    while True:
        # get and convert temperature
        analogTemp = ADC.read(0)
        Vr = 5 * float(analogTemp) / 255
        Rt = 10000 * Vr / (5 - Vr)
        temp = 1/(((math.log(Rt / 10000)) / 3950) + (1 / (273.15 + 25)))
        temp = (temp - 273.15) * 9/5 + 32
        print 'temperature = ', temp, 'F'
        # get and convert gas sensor data
        print 'gas sensor = ', ADC.read(1)
        tmp = GPIO.input(GAS_SENSOR)
        if tmp != status:
            print_gas(tmp)
            status = tmp
        if status == 0:
            count += 1
            if count % 2 == 0:
                GPIO.output(BUZZ, 1)
            else:
                GPIO.output(BUZZ, 0)
        else:
            GPIO.output(BUZZ, 1)
            count = 0

        # raining
        rainVal = ADC.read(2)
        print "rainVal : " + str(rainVal)
        print "GPIO : " + str(GPIO.input(RAIN))
        if GPIO.input(RAIN) == 0:
			print '***************'
			print '* !!RAINING!! *'
			print '***************'
			print ''

        if q_count > 3.5:
            updates = []
            updates.append({'type' : 'temperature', 'value': str(temp), 'timestamp': str(datetime.now())})
            updates.append({'type' : 'gas', 'value': str(ADC.read(1)), 'timestamp': str(datetime.now())})
            updates.append({'type' : 'rain', 'value': str(rainVal), 'timestamp': str(datetime.now())})
            q.put(updates)
            q_count = 0
        q_count = q_count + 1
        time.sleep(2)

def destroy():
    GPIO.output(BUZZ, 1)
    GPIO.cleanup()

if __name__ == '__main__':
    try:
        setup()
        loop()
    except KeyboardInterrupt:
        destroy()