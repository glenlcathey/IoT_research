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

DEVICE_NAME = "device"
IP = "localhost"
PORT = 1883
BASE_STR = "devices/" + DEVICE_NAME + "/shadow/"    #this is the classic unnamed shadow
shadow_list = []

data = {                                                                                #NOTE this dict obj holds state data, change keys to reflect device state
    "state": {
        "reported": {
            "value": [0]
        }
    }
}

def tag_behaviors():
    pass

def on_connect(client, userdata, flags, rc):
    print("Connected to broker with result code "+str(rc))
    client.publish('devices/' + DEVICE_NAME + '/connected', 1, retain=True)


def on_message(client, userdata, msg):
    print("received msg")
    if msg.topic.find("delta") != -1:
        x = json.loads(msg.payload)
        if 'shadow' in x:
            sub_to_named_shadow(x['shadow'])
            if x['shadow'] not in shadow_list:
                shadow_list.append(x['shadow'])
        else:
            parse_delta(x)


def parse_delta(x):
    print(x)
    for k, v in x.items():
        if k in data['state']['reported']:
            data['state']['reported'][k] = v                                            #NOTE only the desired value is modifiable as the tag behavior is defined at the device level
        else:
            temp_dict = [v]
            data['state']['reported'][k] = temp_dict
    
    state = json.dumps(data)
    client.publish(BASE_STR + "update", state, qos=1)                               # once the device state is updated to match the desired state, report updated the device state


def sub_to_named_shadow(shadow_name):
    client.subscribe(BASE_STR + "name/" + shadow_name + "/update/delta")


client = mqtt.Client()
client.on_message = on_message
client.on_connect = on_connect
client.will_set("devices/" + DEVICE_NAME + "/connected", 0, qos=1, retain=True)
#client.username_pw_set(username="", password="")                                        #NOTE must insert username and password if using authenticated broker

client.connect(IP, PORT, 60)
client.subscribe(BASE_STR + "update/delta")
client.loop_start()          

while True:                                                                         #NOTE unique device behavior must be defined in this loop in order to continually execute
    tag_behaviors()

    print(data)
    state = json.dumps(data)
    client.publish(BASE_STR + "update", state, qos=1)                                      #publish curr state to unnamed shadow
    time.sleep(5)