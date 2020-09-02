import subprocess
import sys
import json

def install(package):
    subprocess.check_call([sys.executable, "-m", "pip", "install", package])

install("paho-mqtt") #ensure mqtt library installed

import paho.mqtt.client as mqtt

#reserve topics for virtual device api
#subscribe to physical device for now, will later be direct secure data transfer
#log the data and track connectivity state of physical device

device_name = "pi1"

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
        if "desired" in decoded_str:          #check if desired is a field in the json dict
            #evaluate desired state, publish to device, update json if device updates (device will publish acceptance msg)
            int = 5 #this is to make compiler happy
        if "reported" in decoded_str:
            print("entered reported")
            #load json here, update current state of device, log data, publish to accepted topic so that device knows data got through
            with open(name + "_shadow.json", "r") as r:
                loaded = json.load(r)
            print(str["state"]["reported"]["counter"])
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