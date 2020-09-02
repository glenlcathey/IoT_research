import subprocess
import sys
import json
import os.path
from os import path
from datetime import datetime

def install(package):
    subprocess.check_call([sys.executable, "-m", "pip", "install", package])

install("paho-mqtt") #ensure mqtt library installed

import paho.mqtt.client as mqtt

#reserve topics for virtual device api
#subscribe to physical device for now, will later be direct secure data transfer
#log the data and track connectivity state of physical device

device_name = "pi1"

def json_generator():
    empty_dict = {
        'state': {
            'desired': {

            },
            'reported': {

            }
        }
    }
    
    return empty_dict

def subscription_setup(client, name):      #TODO add the rest of aws api subscription setup
    base_str = "$devices/" + name + "/shadow"
    client.subscribe(base_str + "/update")
    print("setup subscriptions")
    
def on_connect(client, userdata, flags, rc):
    print("Connected with result code "+str(rc))

    # Subscribing in on_connect() means that if we lose the connection and
    # reconnect then subscriptions will be renewed.
    subscription_setup(client, device_name)

def on_message(client, userdata, msg):
    if msg.topic.find("update") != -1:
        update(client, userdata, msg, device_name)
    
def update(client, userdata, msg, name):
    if msg.topic == "$devices/" + name + "/shadow/update":  #make sure this is an update for the correct device 
        str = msg.payload
        decoded_str = json.loads(str)        #load the payload into a json dict
        if 'desired' in decoded_str['state']:          #check if desired is a field in the json dict
            #evaluate desired state, publish to device, update json if device updates (device will publish acceptance msg)
            int = 5 #this is to make compiler happy
        if 'reported' in decoded_str['state']: #load json here, update current state of device, log data, publish to accepted topic so that device knows data got through
            if !os.path.exists(name + "_shadow_json"):    #check if json shadow file missing
                int = 2
                #call function that makes skeletal json file
                                                                                                                                                #TODO json_generator() - makes and returns empty json dict w reported/desired/delta structure
        #if os.path.exists(name + "_shadow_json"):  #check if json for device exists in directory with client
            with open(name + "_shadow_json", "r") as file_in:       #TODO this should be wrapped in try/catch in case json file creation failed
                loaded = json.load(file_in)
            loaded['state']['reported']['counter'] = decoded_str['state']['reported']['counter']   #update the var in shadow json
            loaded.update({datetime.now().strftime('%Y-%m-%d %H:%M:%S'): {'counter': decoded_str['state']['reported']['counter']}})   #TODO this should probably call a function which expands all reported fields and returns a dict obj 
            with open(name + "_shadow_json", "w") as file_out:
                json.dump(loaded, file_out)                        #write updated json dict back into file




"""
def on_message(client, userdata, msg):   #this on message function could be abstracted to 3 ifs: receiving device data, receiving requests for device, and receiving device state
    if msg.topic.find("CONNECTED") != -1:     
        reported_connectivity = msg.payload
        #call update connected state json function here
    elif msg.topic.find("ints") != -1:    #making sure the topic of the message matches expected val
        #call log data json function here
    elif msg.topic.find("desired") != -1:
        #a change state request will be published to the device in this case
    else:
        #throw error here, or default to something
"""


client = mqtt.Client()
client.on_message = on_message
client.on_connect = on_connect

client.connect("localhost", 1883, 60)

client.loop_forever()