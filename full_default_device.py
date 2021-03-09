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
            "value": [0, "WARNING", "SENSOR"],                                          #NOTE each key value pair will hold an array where the first index is the value and every other is a tag
            "mem_percent": [0]
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
    client.publish('devices/' + name + '/connected', 1, retain=True)

def on_message(client, userdata, msg):
    topic = msg.topic.decode("utf-8")
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
        data['state']['reported'][k] = v                                            #NOTE dont think this should have indeces because the tags should be modifiable as well (?)
                                                                                    #could do a check to see if delta contains tags or just a value
def sub_to_named_shadow(shadow_name):
    client.subscribe(bytes(base_str + "name/" + shadow_name + "/update/delta"))

client = mqtt.Client()
client.on_message = on_message
client.on_connect = on_connect
client.will_set("devices/" + name + "/connected", 0, qos=1, retain=True)
#client.username_pw_set(username="", password="")                                        #NOTE must insert username and password if using authenticated broker

client.connect(ip, port, 60)
#data['state']['reported']['mem_percent'][1] = "SENSOR"
client.loop_start()          

while True:                                                                         #NOTE unique device behavior must be defined in this loop in order to continually execute
    data['state']['reported']['batt_percent'] = psutil.sensors_battery().percent
    data['state']['reported']['mem_percent'][0] = psutil.virtual_memory().percent
    data['state']['reported']['value'][0] = data['state']['reported']['value'][0] + 1

    state = json.dumps(data)
    client.publish(base_str + "update", state, qos=1)                                      #publish curr state to unnamed shadow
    for element in shadow_list:
        client.publish(base_str + "/name/" + element + "/update", state, qos=1)            #publish the current state to every known named shadow
    time.sleep(1)