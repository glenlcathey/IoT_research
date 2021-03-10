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

device_name = input("Enter the device name (this will be used for topics): ")
connected = False
shadow_name = input("Enter the name of this shadow (if left blank, defaults to base shadow): ")       #This sets up shadow and device name attached to the client
base_str = "devices/" + device_name + "/shadow/"
unnamed_str = base_str
if shadow_name != "":
    base_str = base_str + "name/" + shadow_name + "/"

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
    client.subscribe(base_str + "update")
    client.subscribe("devices/" + name + "/connected")
    print("setup subscriptions")
    
def on_connect(client, userdata, flags, rc):
    print("Connected with result code "+str(rc))

    # Subscribing in on_connect() means that if we lose the connection and
    # reconnect then subscriptions will be renewed.
    subscription_setup(client, device_name)

def on_message(client, userdata, msg):
    if msg.topic.find("update") != -1:          #topic contains update
        msg.payload = msg.payload.decode("utf-8")
        update(client, userdata, msg, device_name)
        delta(client, device_name)
    if msg.topic.find("connected") != -1:       #topic contains connected
        global connected
        if msg.payload.decode("utf-8") == "1":
            connected = True
            if shadow_name != "":
                emp = json.dumps(json_generator())
                emp['shadow'] = shadow_name
                client.publish(unnamed_str + "update/delta", emp)
        if msg.payload.decode("utf-8") == "0":
            connected = False

    
def update(client, userdata, msg, name):            #TODO a desired update logic needs to be done, this should also publish to the accepted topic when an update goes through
    if msg.topic == base_str + "update":  #make sure this is an update for the correct device 
        
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
                loaded['state']['desired'][k] = v        #set the desired state of the shadow equal to the received message CHANGED FROM THIS CHANGE BACK FOR INTS -> int(v, 10)
            with open(name + "_shadow.json", 'w') as file_out:
                json.dump(loaded, file_out)
            
            with open(name + "_log.json", "r") as file_in:
                log = json.load(file_in)
            log.update({datetime.now().strftime('%Y-%m-%d %H:%M:%S'): loaded['state']})       #this block updates the log with the current reported state of the shadow
            with open(name + "_log.json", "w") as file_out:
                json.dump(log, file_out)

        
        if 'reported' in decoded_str['state']: #load json here, update current state of device, log data, publish to accepted topic so that device knows data got through
            with open(name + "_shadow.json", "r") as file_in:
                shadow = json.load(file_in)
            for k, v in decoded_str['state']['reported'].items():         #this block updates the shadow with the new reported state
                shadow['state']['reported'][k] = v
            with open(name + "_shadow.json", "w") as file_out:
                json.dump(shadow, file_out)

            with open(name + "_log.json", "r") as file_in:
                log = json.load(file_in)
            log.update({datetime.now().strftime('%Y-%m-%d %H:%M:%S'): shadow['state']})       #this block updates the log with the current reported state of the shadow
            with open(name + "_log.json", "w") as file_out:
                json.dump(log, file_out)
            #client.publish("devices/" + name + "/shadow/update/accepted", 1)
            

def delta(client, name):
    #This func should compare desired and reported sub keys and add any differences into the delta key
    #then this should check if the device is connected and if so the keys in delta should be published to the device via the '/update/delta' topic
    #the device will change state to match and then publish a reported update to shadow
    with open(name + "_shadow.json") as file_in:
        shadow = json.load(file_in)
    for k, v in shadow['state']['desired'].copy().items():            #iterate through desired keys
        if shadow['state']['reported'].get(k) != v:                #if key is in reported and desired value doesnt match reported value
            shadow['state']['delta'][k] = v
        if shadow['state']['delta'].get(k) == shadow['state']['reported'].get(k) and shadow['state']['delta'].get(k) != None:
            del shadow['state']['delta'][k]
        if shadow['state']['reported'].get(k) == shadow['state']['desired'].get(k) and shadow['state']['desired'].get(k) != None:
            del shadow['state']['desired'][k]

    print(shadow)
    print()

    with open(name + "_shadow.json", 'w') as file_out:
        json.dump(shadow, file_out)

    global connected
    
    if connected == True and len(shadow['state']['delta']) != 0:
        str = json.dumps(shadow['state']['delta'])
        client.publish(base_str + "update/delta", str)       #publish keys in delta to device
    


client = mqtt.Client()
client.on_message = on_message
client.on_connect = on_connect
client.username_pw_set(username="light_shadow", password="light_password")

client.connect("localhost", 1883, 60)

client.loop_forever()