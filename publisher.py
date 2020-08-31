import subprocess
import sys
import json

def install(package):
    subprocess.check_call([sys.executable, "-m", "pip", "install", package])

install("paho-mqtt")

import paho.mqtt.client as mqtt
#import virtual_device as vd    #discontinued work on local vd client
import random

def on_connect(client, userdata, flags, rc):
    client.publish("$CONNECTED/pi1", 1, retain=True)
    client.will_set("$CONNECTED/pi1", 0, qos=0, retain=True) #set will

def on_publish(client, userdata, mid):
    print("published new value to broker")

random = random.Random()
random.seed()

client = mqtt.Client()
#shadow = vd.device("pi1")
client.on_publish = on_publish
client.on_connect = on_connect
client.connect("localhost", 1883, 60)

data = {
        "state": {
            "reported": {
                "counter": 0
            }
        }
    }

client.loop_start()

while True:
    print(data)
    ret = client.publish("$devices/pi1/shadow/update", str(data), 0, False, None)
    data["state"]["reported"]["counter"] = data["state"]["reported"]["counter"] + 1
    #shadow.generalCallback(client, None, rand, "ints/rand")
    ret.wait_for_publish()