import subprocess
import sys
import json
import time

def install(package):
    subprocess.check_call([sys.executable, "-m", "pip", "install", package])

install("paho-mqtt")

import paho.mqtt.client as mqtt
#import virtual_device as vd    #discontinued work on local vd client
import random

name = input("Enter the device name (this will be used for topics): ")
data = {
        "state": {
            "reported": {
                "counter": 0
            }
        }
}

def on_connect(client, userdata, flags, rc):
    client.publish("$devices/" + name + "/connected", 1, retain=True)
    client.will_set("$devices/" + name + "/connected", 0, qos=0, retain=True) #set will
    client.subscribe("$devices/" + name + "/shadow/update/accepted")
    client.subscribe("$devices/" + name + "/shadow/update/delta")

def on_message(client, userdata, msg):
    msg.payload = msg.payload.decode("utf-8")
    if msg.topic.find("accepted") != -1:
        if msg.payload != "1":
            print("message not accepted by shadow")
            print(msg.payload)
    if msg.topic.find("delta") != -1:
        parse_delta(client, msg.payload)

def parse_delta(client, str):
    print("delta received" + str)
    x = json.loads(str)
    for k, v in x.items():
        data['state']['reported'][k] = v
    

random = random.Random()
random.seed()

client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message
client.connect("localhost", 1883, 60)

client.loop_start()

while True:
    str = json.dumps(data)
    ret = client.publish("$devices/" + name + "/shadow/update", str, 0, False, None)
    data["state"]["reported"]["counter"] = data["state"]["reported"]["counter"] + 1
    #shadow.generalCallback(client, None, rand, "ints/rand")
    ret.wait_for_publish()
    time.sleep(1)