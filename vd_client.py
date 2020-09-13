import subprocess
import sys
import json
import os
from datetime import datetime

def install(package):
    subprocess.check_call([sys.executable, "-m", "pip", "install", package])

install("paho-mqtt") #ensure mqtt library installed

import paho.mqtt.client as mqtt

#reserve topics for virtual device api
#subscribe to physical device for now, will later be direct secure data transfer
#log the data and track connectivity state of physical device

device_name = "pi1"
connected = None

def json_generator():
    empty_dict = {
        'state': {
            'desired': {

            },
            'reported': {

            },
            'delta': {
                
            }
        }
    }
    
    return empty_dict

def subscription_setup(client, name):      #TODO add the rest of aws api subscription setup
    base_str = "$devices/" + name + "/shadow"
    client.subscribe(base_str + "/update")
    client.subscribe("$devices/" + name + "/connected")
    print("setup subscriptions")
    
def on_connect(client, userdata, flags, rc):
    print("Connected with result code "+str(rc))

    # Subscribing in on_connect() means that if we lose the connection and
    # reconnect then subscriptions will be renewed.
    subscription_setup(client, device_name)

def on_message(client, userdata, msg):
    if msg.topic.find("update") != -1:          #topic contains update
        update(client, userdata, msg, device_name)
        delta(client, device_name)
    if msg.topic.find("connected") != -1:       #topic contains connected
        if msg.payload.decode("utf-8") == "1":
            connected = True
        if msg.payload.decode("utf-8") == "0":
            connected = False

    
def update(client, userdata, msg, name):            #TODO a desired update logic needs to be done, this should also publish to the accepted topic when an update goes through
    if msg.topic == "$devices/" + name + "/shadow/update":  #make sure this is an update for the correct device 
        
        decoded_str = json.loads(msg.payload)        #load the payload into a json dict
        
        if not os.path.exists(name + "_shadow.json"):    #check if json shadow file missing, if it is then skeletal json file is made for shadow
                print("shadow not found, making new one")  #this is done here because all following options will require the json
                empty_dict = json_generator()
                with open(name + "_shadow.json", "w") as file_out:
                    json.dump(empty_dict, file_out)
        
        if not os.path.exists(name + "_log.json"):    #check if json shadow file missing, if it is then skeletal json file is made for shadow
                print("log not found, making new one")  #this is done here because all following options will require the json
                empty = {}
                with open(name + "_log.json", "w") as file_out:
                    json.dump(empty, file_out)

        if 'desired' in decoded_str['state']:          #check if desired is a field in the json dict
            #This should update desired will all passed keys from update message
            #any differences betwwen desired and reported state will be handled in delta function
            with open(name + "_shadow.json", "r") as file_in:
                loaded = json.load(file_in)
            for k, v in decoded_str['state']['desired'].items():
                loaded['state']['desired'][k] = v         #set the desired state of the shadow equal to the received message
            with open(name + "_shadow.json", 'w') as file_out:
                json.dump(loaded, file_out)

        
        if 'reported' in decoded_str['state']: #load json here, update current state of device, log data, publish to accepted topic so that device knows data got through
            with open(name + "_shadow.json", "r") as file_in:
                shadow = json.load(file_in)
            for k, v in decoded_str['state']['reported'].items():         #this block updates the shadow with the new reported state
                shadow['state']['reported'][k] = v
            with open(name + "_shadow.json", "w") as file_out:
                json.dump(shadow, file_out)

            with open(name + "_log.json", "r") as file_in:
                log = json.load(file_in)
            print(shadow['state']['reported'])
            log.update({datetime.now().strftime('%Y-%m-%d %H:%M:%S'): shadow['state']['reported']})       #this block updates the log with the current reported state of the shadow
            with open(name + "_log.json", "w") as file_out:
                json.dump(log, file_out)
            client.publish("$devices/" + name + "/shadow/update/accepted", 1)
            

def delta(client, name):
    #This func should compare desired and reported sub keys and add any differences into the delta key
    #then this should check if the device is connected and if so the keys in delta should be published to the device via the '/update/delta' topic
    #the device will change state to match and the publish a reported update to shadow
    with open(name + "_shadow.json") as file_in:
        loader = json.load(file_in)
    desired = loader['state']['desired']
    reported = loader['state']['reported']
    for k, v in desired.items():            #iterate through desired keys
        if k in reported and reported[k] != v:                #if key is in reported and desired value doesnt match reported value
            loader['state']['delta'][k] = v
    
    if connected == True:
        client.publish("$devices/" + name + "/shadow/update/delta", loader['state']['delta'])       #publish keys in delta to device
    


client = mqtt.Client()
client.on_message = on_message
client.on_connect = on_connect

client.connect("localhost", 1883, 60)

client.loop_forever()