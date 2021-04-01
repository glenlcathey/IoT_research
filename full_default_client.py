#HOW TO INTERACT WITH THIS FILE:
#call with command line arguements if you want to specify device name, or shadow name
#the first arg should be device name (if not present defaults to 'device')
#the second arg should be shadow name (if not present defaults base unnamed shadow)


import subprocess
import sys
import json
import os
import logging
from datetime import datetime

def install(package):
    subprocess.check_call([sys.executable, "-m", "pip", "install", package])

install("paho-mqtt") #ensure mqtt library installed
import paho.mqtt.client as mqtt

#core frequently interacted with variables setup here
shadow = False
connected = False
device_name = 'device'   #defaults to 'device'
if len(sys.argv) > 1:
    device_name = sys.argv[1]
    
named_base_str = "devices/" + device_name + "/shadow/"
unnamed_base_str = named_base_str
if len(sys.argv) > 2:
    named_base_str = named_base_str + "name/" + sys.argv[2] + "/"
    shadow = True

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

def behaviors(cur_state, client):           #Define client specific behaviors in this function.
    pass

def subscription_setup(client, name):      #TODO add the rest of aws api subscription setup
    client.subscribe(named_base_str + "update")
    client.subscribe(named_base_str + "get")
    client.subscribe("devices/" + name + "/connected")
    print("successfully setup subscriptions")
    
def on_connect(client, userdata, flags, rc):
    print("Connected to broker with result code "+str(rc))
    # Subscribing in on_connect() means that if we lose the connection and
    # reconnect then subscriptions will be renewed.
    subscription_setup(client, device_name)

def on_message(client, userdata, msg):
    print("Received message: " + msg.payload.decode("utf-8"))
    print()
    if msg.topic.find("update") != -1:          #topic contains update
        msg.payload = msg.payload.decode("utf-8")
        update(client, userdata, msg, device_name)
        delta(client, device_name)
    if msg.topic.find("connected") != -1:       #topic contains connected
        global connected
        if msg.payload.decode("utf-8") == '1':
            print('device connected')
            connected = True
            if shadow:
                emp = json.dumps(json_generator())
                emp['shadow'] = shadow_name
                client.publish(unnamed_base_str + "update/delta", emp)
        if msg.payload.decode("utf-8") == "0":
            connected = False

    
def update(client, userdata, msg, name):            #TODO a desired update logic needs to be done, this should also publish to the accepted topic when an update goes through
    if msg.topic == named_base_str + "update":  #make sure this is an update for the correct device 
        
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
            print("entered desired")
            with open(name + "_shadow.json", "r") as file_in:
                loaded = json.load(file_in)
            for k, v in decoded_str['state']['desired'].items():
                loaded['state']['desired'][k] = v        #set the desired state of the shadow equal to the received message
            with open(name + "_shadow.json", 'w') as file_out:
                json.dump(loaded, file_out)

        if 'reported' in decoded_str['state']: #load json here, update current state of device, log data, publish to accepted topic so that device knows data got through
            with open(name + "_shadow.json", "r") as file_in:
                shadow = json.load(file_in)
            for k, v in decoded_str['state']['reported'].items():         #this block updates the shadow with the new reported state
                shadow['state']['reported'][k] = v
            with open(name + "_shadow.json", "w") as file_out:
                json.dump(shadow, file_out)

            behaviors(shadow, client)

            with open(name + "_log.json", "r") as file_in:
                log = json.load(file_in)
            log.update({datetime.now().strftime('%Y-%m-%d %H:%M:%S'): shadow['state']['reported']})       #this block updates the log with the current reported state of the shadow
            with open(name + "_log.json", "w") as file_out:
                json.dump(log, file_out)
            

def delta(client, name):
    #This func should compare desired and reported sub keys and add any differences into the delta key
    #then this should check if the device is connected and if so the keys in delta should be published to the device via the '/update/delta' topic
    #the device will change state to match and then publish a reported update to shadow
    with open(name + "_shadow.json") as file_in:
        shadow = json.load(file_in)
    for k, v in shadow['state']['desired'].copy().items():            #iterate through desired keys
        if shadow['state']['reported'][k][0] != v:                #if key is in reported and desired value doesnt match reported value
            shadow['state']['delta'][k] = v
        if shadow['state']['delta'][k][0] == shadow['state']['reported'][k][0]:
            del shadow['state']['delta'][k]
        if shadow['state']['reported'][k][0] == shadow['state']['desired'][k][0]:
            del shadow['state']['desired'][k]

    print(shadow)
    print()

    with open(name + "_shadow.json", 'w') as file_out:
        json.dump(shadow, file_out)

    global connected
    
    if connected == True and len(shadow['state']['delta']) != 0:
        print("items in delta")
        str = json.dumps(shadow['state']['delta'])
        print(named_base_str + "update/delta")
        client.publish(named_base_str + "update/delta", str)       #publish keys in delta to device
    


client = mqtt.Client()
client.on_message = on_message
client.on_connect = on_connect
client.username_pw_set(username="counter_shadow", password="counter_password")


client.connect("localhost", 1883, 60)

client.loop_forever()