from umqtt.simple import MQTTClient
import ujson
import utime

data = {                                                                                #NOTE this dict obj holds state data, change keys to reflect device state
    "state": {
        "reported": {
            "value": 0
        }
    }
}

ip = input("enter broker ip, if left blank defaults to saved broker ip: ")                      
if (ip == ""):
    ip = ""     #NOTE put your broker ip here

#port = input("enter the desired port, if left blank defualts to 1883: ")
#if (port == ""):
    #port = 1883
port = 1883     #NOTE this is default mqtt port

name = input("enter the device name for topics, if left blank defaults to : ")          #NOTE change printed message to accurately reflect default val
if (name == ""):
    name = ""   #NOTE put preferred default device name here

base_str = "devices/" + name + "/shadow/"    #this is the classic unnamed shadow
shadow_list = []   #make the list to hold shadow names as they are received             #TODO could be instantiated with values for shadows that should always exist (warning, critical, etc)

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

c = MQTTClient(name, ip, port)                                                      #NOTE must insert username and password if using authenticated broker
c.set_callback(on_message)
c.set_last_will("devices/" + name + "/connected", b"0", qos=0, retain=True)         #informs active clients the device has turned off in event of shutdown
c.connect()
c.publish(b'devices/' + name + '/connected', b'1', retain=True)                     #informs any active clients that device is now active
c.subscribe(bytes(base_str + "update/delta", 'utf-8'))                              #subscribe to classic shadow update delta

while True:                                                                         #NOTE unique device behavior must be defined in this loop in order to continually execute
    state = ujson.dumps(data)
    c.publish(bytes(base_str + "update", 'utf-8'), state, qos=1)                                      #publish curr state to unnamed shadow
    for element in shadow_list:
        c.publish(bytes(base_str + "/name/" + element + "/update", 'utf-8'), state, qos=1)            #publish the current state to every known named shadow
    utime.sleep(1)
    c.check_msg()