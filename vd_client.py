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

def compare_dict(x, y):
    for k, v in x:      #iterate through incoming desired state
        for l, m in y:  #iterate through current desired state
            if k == l:      #if key matches indicate match found for key
                match = True
                if v == m:  #if val of key matches as well then break from loop and compare next key
                    break
                else:
                    return False
        if match == False:
            return False    #if a match wasnt found for the incoming key then 

def json_generator():
    empty_dict = {
        'state': {
            'desired': {

            },
            'reported': {

            }
            'delta': {
                
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
        delta(client, device_name)
    
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
                open(name + "_log.json", "w")

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

            with open(name + "_log.json", 'r') as file_in:
                log = json.load(file_in)
            log.update({datetime.now().strftime('%Y-%m-%d %H:%M:%S'): {shadow['state']['reported']}})       #this block updates the log
            with open(name + "_log.json", "w") as file_out:
                json.dump(log, file_out)
            client.publish("$devices/" + name + "/shadow/update/accepted", 1)
            

def delta(client, name):
    #This func should compare desired and reported sub keys and add any differences into the delta key
    #then this should check if the device is connected and if so the keys in delta should be published to the device via the '/update/delta' topic
    #the device will change state to match and the publish a reported update to shadow


client = mqtt.Client()
client.on_message = on_message
client.on_connect = on_connect

client.connect("localhost", 1883, 60)

client.loop_forever()