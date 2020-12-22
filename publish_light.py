from umqtt.simple import MQTTClient
import ujson
import utime

data = {
    "state": {
        "reported": {
            "light": 0
        }
    }
}

ip = input("enter broker ip, if left blank default to home ip: ")
if (ip == ""):
    ip = "192.168.1.2"

#port = input("enter the desired port, if left blank defualts to 1883: ")
#if (port == ""):
    #port = 1883
port = 1883

name = input("enter the device name for topics, if left blank defaults to esp2: ")
if (name == ""):
    name = "esp2"

base_str = "$devices/" + name + "/shadow/"    #if there are multiple shadows, there will be multiple base strings (one per shadow)

def on_message(topic, msg):
    topic = topic.decode("utf-8")
    msg = msg.decode("utf-8")
    print((topic, msg))
    #if topic.find("accepted") != -1:
    #    if msg != "1":
    #        print("message not accepted by shadow")
    #        print(msg)
    if topic.find("delta") != -1:
        parse_delta(msg)

def parse_delta(str):
    print("delta received" + str)
    x = ujson.loads(str)
    for k, v in x.items():
        data['state']['reported'][k] = v

def process_msg(topic, msg):
    print((topic, msg))

c = MQTTClient(name, ip, port, b"light_esp", b"light_esp_password")
c.set_callback(on_message)
c.set_last_will("$devices/" + name + "/connected", b"0", qos=0, retain=True)
c.connect()
c.publish(b'$devices/' + name + '/connected', b'1', retain=True)                #can incorporate base string into this as well, just have to change connected on client side. 
c.subscribe(bytes(base_str + "update/delta", 'utf-8')

while True:
    str = ujson.dumps(data)
    c.publish(bytes(bytes_str + "update", 'utf-8'), str, qos=1)
    utime.sleep(1)
    c.check_msg()