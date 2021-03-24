from umqtt.simple import MQTTClient
import ujson
import utime

data = {
    "state": {
        "reported": {
            "counter": 0
        }
    }
}

ip = input("enter broker ip, if left blank defaults to home ip: ")
if (ip == ""):
    ip = "192.168.1.2"

#port = input("enter the desired port, if left blank defualts to 1883: ")
#if (port == ""):
    #port = 1883
port = 1883

name = input("enter the device name for topics, if left blank defaults to esp1: ")
if (name == ""):
    name = "esp1"

base_str = "devices/" + name + "/shadow/"    #this is the classic unnamed shadow
shadow_list = []   #make the list to hold shadow names as they are received             #NOTE could be instantiated with values for shadows that should always exist (warning, critical, etc)

def on_message(topic, msg):
    topic = topic.decode("utf-8")
    msg = msg.decode("utf-8")
    print(topic)
    print(msg)
    if topic.find("delta") != -1:
        x = ujson.loads(msg)
        if 'shadow' in x:
            sub_to_named_shadow(x['shadow'])
            if x['shadow'] not in shadow_list:
                shadow_list.append(x['shadow'])
        else:
            parse_delta(x)

def parse_delta(x):
    for k, v in x.items():
        data['state']['reported'][k] = v

def sub_to_named_shadow(shadow_name):
    c.subscribe(bytes(base_str + "name/" + shadow_name + "/update/delta"))

c = MQTTClient(name, ip, port, b"counter_esp", b"counter_esp_password")
c.set_callback(on_message)
c.set_last_will("devices/" + name + "/connected", b"0", qos=0, retain=True)        #can incorporate base string into this as well, just have to change connected on client side. 
c.connect()
c.publish(b'devices/' + name + '/connected', b'1', retain=True)                    #can incorporate base string into this as well, just have to change connected on client side. 
c.subscribe(bytes(base_str + "update/delta", 'utf-8'))                              #subscribe to classic shadow update delta

while True:
    state = ujson.dumps(data)
    c.publish(bytes(base_str + "update", 'utf-8'), state, qos=1)                                      #publish curr state to unnamed shadow
    for element in shadow_list:
        c.publish(bytes(base_str + "/name/" + element + "/update", 'utf-8'), state, qos=1)            #publish the current state to every known named shadow
    data["state"]["reported"]["counter"] = data["state"]["reported"]["counter"] + 1
    utime.sleep(1)
    c.check_msg()