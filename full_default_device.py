import json
import time
import sys
import os
import subprocess
import psutil

def install(package):
    subprocess.check_call([sys.executable, "-m", "pip", "install", package])

install("paho-mqtt") #ensure mqtt library installed

import paho.mqtt.client as mqtt


data = {                                                                                #NOTE this dict obj holds state data, change keys to reflect device state
    "state": {
        "reported": {
            "value": 0
        }
    }
}

ip = input("enter broker ip, if left blank defaults to saved broker ip: ")                      
if (ip == ""):
    ip = "localhost"     #NOTE put your broker ip here

#port = input("enter the desired port, if left blank defualts to 1883: ")
#if (port == ""):
    #port = 1883
port = 1883     #NOTE this is default mqtt port

name = input("enter the device name for topics, if left blank defaults to 'device': ")          #NOTE change printed message to accurately reflect default val
if (name == ""):
    name = "device"   #NOTE put preferred default device name here

base_str = "devices/" + name + "/shadow/"    #this is the classic unnamed shadow
shadow_list = []   #make the list to hold shadow names as they are received             #TODO could be instantiated with values for shadows that should always exist (warning, critical, etc)

def on_connect(client, userdata, flags, rc):
    print("Connected with result code "+str(rc))

def on_message(client, userdata, msg):
    topic = msg.topic
    msg = msg.payload.decode("utf-8")
    print(topic)
    print(msg)
    if topic.find("delta") != -1:
        x = json.loads(msg)
        if 'shadow' in x:
            sub_to_named_shadow(x['shadow'])
            if x['shadow'] not in shadow_list:
                shadow_list.append(x['shadow'])
        else:
            parse_delta(x)

def parse_delta(x):
    for k, v in x.items():
        data['state']['reported'][k] = v

def sub_to_named_shadow(shadow_name):
    c.subscribe(bytes(base_str + "name/" + shadow_name + "/update/delta"))

c = mqtt.Client()
c.on_message = on_message
c.on_connect = on_connect
c.will_set("devices/" + name + "/connected", 0, qos=1, retain=True)
#c.username_pw_set(username="", password="")                                        #NOTE must insert username and password if using authenticated broker

c.connect(ip, port, 60)
c.publish("devices/" + name + "/connected", 1, qos=1, retain=True)
c.subscribe(base_str + "update/delta")
c.loop_start()          

while True:                                                                         #NOTE unique device behavior must be defined in this loop in order to continually execute
    data['state']['reported']['batt_percent'] = psutil.sensors_battery().percent
    data['state']['reported']['mem_percent'] = psutil.virtual_memory().percent
    data['state']['reported']['value'] = data['state']['reported']['value'] + 1

    state = json.dumps(data)
    c.publish(base_str + "update", state, qos=1)                                      #publish curr state to unnamed shadow
    for element in shadow_list:
        c.publish(base_str + "/name/" + element + "/update", state, qos=1)            #publish the current state to every known named shadow
    time.sleep(1)