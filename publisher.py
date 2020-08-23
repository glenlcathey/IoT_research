import subprocess
import sys

def install(package):
    subprocess.check_call([sys.executable, "-m", "pip", "install", package])

install("paho-mqtt")

import paho.mqtt.client as mqtt
import random

def on_connect(client, userdata, flags, rc):
    client.publish("$CONNECTED/pi1", 1, retain=True)
    client.will_set("$CONNECTED/pi1", 0, qos=0, retain=True) #set will

def on_publish(client, userdata, mid):
    print("published new value to broker")

random = random.Random()
random.seed()

client = mqtt.Client()
client.on_publish = on_publish
client.on_connect = on_connect
client.connect("localhost", 1883, 60)

client.loop_start()

while True:
    rand = random.getrandbits(5)
    print(str(rand))
    ret = client.publish("ints/rand", rand, 0, False, None)
    ret.wait_for_publish()