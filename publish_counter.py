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

#port = input("enter the desired port, if left blank defualts to 1883")
#if (port == ""):
    #port = 1883
port = 1883

name = input("enter the device name for topics, if left blank defaults to esp1: ")
if (name == ""):
    name = "esp1"

base_str = "$devices/" + name + "/shadow/"    #this is the classic unnamed shadow
shadow_list = []   #make the list to hold shadow names as they are received

def on_message(topic, msg):
    topic = topic.decode("utf-8")
    msg = msg.decode("utf-8")
    print((topic, msg))
    #if topic.find("accepted") != -1:
    #    if msg != "1":
    #        print("message not accepted by shadow")
    #        print(msg)
    if topic.find("name") != -1:            #check if msg came from named shadow
        y = topic.split('/')
        print(y[4])
        shadow_list.append(y[4])
    if topic.find("delta") != -1:
        parse_delta(msg)

def parse_delta(str):
    print("delta received" + str)
    x = ujson.loads(str)
    for k, v in x.items():
        data['state']['reported'][k] = v

c = MQTTClient(name, ip, port, b"counter_esp", b"counter_esp_password")
c.set_callback(on_message)
c.set_last_will("$devices/" + name + "/connected", b"0", qos=0, retain=True)        #can incorporate base string into this as well, just have to change connected on client side. 
c.connect()
c.publish(b'$devices/' + name + '/connected', b'1', retain=True)                    #can incorporate base string into this as well, just have to change connected on client side. 
c.subscribe(bytes(base_str + "update/delta", 'utf-8'))                              #subscribe to classic shadow update delta
c.subscribe(bytes(base_str + "/name/+/update/delta", 'utf-8'))                      #subscribe to any named shadows here

while True:
    str = ujson.dumps(data)
    c.publish(bytes(base_str + "update", 'utf-8'), str, qos=1)                                      #publish curr state to unnamed shadow
    for element in shadow_list:
        c.publish(bytes(base_str + "/name/" + element + "/update", 'utf-8'), str, qos=1)            #publish the current state to every known named shadow
    data["state"]["reported"]["counter"] = data["state"]["reported"]["counter"] + 1
    utime.sleep(1)
    c.check_msg()