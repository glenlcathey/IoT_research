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
    
def update(client, userdata, msg, name):            #TODO a desired update logic needs to be done, this should also publish to the accepted topic when an update goes through
    if msg.topic == "$devices/" + name + "/shadow/update":  #make sure this is an update for the correct device 
        decoded_str = json.loads(msg.payload)        #load the payload into a json dict
        if not os.path.exists(name + "_shadow.json"):    #check if json shadow file missing, if it is then skeletal json file is made for shadow
                print("json not found, making new one")  #this is done here because all following options will require the json
                empty_dict = json_generator()
                with open(name + "_shadow.json", "w") as file_out:
                    json.dump(empty_dict, file_out)

        if 'desired' in decoded_str['state']:          #check if desired is a field in the json dict
            #should check if desired differs from reported state (CHECK ALL SUBFIELDS, POSSIBLY CALL RECURSIVE FUNC HERE??) - if it does NOT then function can end
            #if desired DOES differ, if device NOT connected then update desired and end
            #if device IS connected then update desired then publish to device via update/delta, empty the desired fields once device reports it has changed state to match desired state
            with open(name + "_shadow.json", "r") as file_in:
                loaded = json.load(file_in)
            if loaded['state']['desired']['counter'] == decoded_str['state']['reported']['counter']:    #TODO make this compare all subfields, probably call recursive func here or smth
                return
            loaded['state']['desired']['counter'] = decoded_str['state']['reported']['counter'] #TODO this should be abstracted to whatever the state fields are for the device

            
        
        if 'reported' in decoded_str['state']: #load json here, update current state of device, log data, publish to accepted topic so that device knows data got through
            with open(name + "_shadow.json", "r") as file_in:
                loaded = json.load(file_in)
            loaded['state']['reported']['counter'] = decoded_str['state']['reported']['counter']   #update the var in shadow json
            loaded.update({datetime.now().strftime('%Y-%m-%d %H:%M:%S'): {'counter': decoded_str['state']['reported']['counter']}})   #TODO this should probably call a function which expands all reported fields and returns a dict obj 
            with open(name + "_shadow.json", "w") as file_out:
                json.dump(loaded, file_out)                        #write updated json dict back into file
            client.publish("$devices/" + name + "/shadow/update/accepted", 1)

client = mqtt.Client()
client.on_message = on_message
client.on_connect = on_connect

client.connect("localhost", 1883, 60)

client.loop_forever()