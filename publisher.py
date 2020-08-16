import paho.mqtt.client as mqtt
import random

def on_publish(client, userdata, mid):
    print("published new value to broker")

random = random.Random()
random.seed()

client = mqtt.Client()
client.on_publish = on_publish
client.connect("localhost", 1883, 60)

client.loop_start()

while True:
    rand = random.getrandbits(5)
    print(str(rand))
    ret = client.publish("ints/rand", rand, 0, False, None)
    ret.wait_for_publish()