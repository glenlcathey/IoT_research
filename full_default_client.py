#HOW TO INTERACT WITH THIS FILE:
#call with command line arguements if you want to specify device name, or shadow name
#the first arg should be device name (if not present defaults to 'device')
#the second arg should be shadow name (if not present defaults base unnamed shadow)


import subprocess
import sys
import json
import os
import logging
import datetime

def install(package):
    subprocess.check_call([sys.executable, "-m", "pip", "install", package])

install("paho-mqtt") #ensure mqtt library installed
import paho.mqtt.client as mqtt


#core frequently interacted with variables setup here
curr_state = {}
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

log_file_name = device_name
if shadow:
    log_file_name = log_file_name + "_" + sys.argv[2] #NOTE probably cleaner to remove these cmd line arg calls and just do one at the top
log_file_name = log_file_name + ".log"
    

def setup_logger(name, log_file, level=logging.INFO):
    """Function setup as many loggers as you want"""
    handler = logging.FileHandler(log_file)
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.addHandler(handler)
    return logger

logger = setup_logger('', log_file_name, level=logging.DEBUG)

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
    logger.info("Connected to broker with result code: " + str(rc))
    # Subscribing in on_connect() means that if we lose the connection and
    # reconnect then subscriptions will be renewed.
    subscription_setup(client, device_name)

def on_message(client, userdata, msg):
    #logger.debug("Incoming message: topic = " + str(msg.topic) + " message = " + str(msg.payload))

    if msg.topic.find("update") != -1:          #topic contains update
        msg.payload = msg.payload.decode("utf-8")

        #make list

        StartClock = datetime.datetime.now()                                                    # Starting clock HERE

        update(client, userdata, msg, device_name)
        #logger.debug("State after update function" + json.dumps(curr_state))
        delta(client, device_name)                                                              #NOTE does delta need to be called here or only after desired message received
        parse_tags()

        #potential publish to device 

        EndClock = datetime.datetime.now()
        TIMER = mytimecalculations(StartClock, EndClock)
        logger.info(TIMER)

        print(curr_state)
        logger.info("State after /update message processed: " + json.dumps(curr_state))

    if msg.topic.find("connected") != -1:       #topic contains connected
        global connected
        if msg.payload.decode("utf-8") == '1':
            print('device connected')
            connected = True
            if shadow:
                emp = json_generator() #why does this need to be a string??
                emp['shadow'] = sys.argv[2]
                client.publish(unnamed_base_str + "update/delta", json.dumps(emp))
        if msg.payload.decode("utf-8") == "0":
            connected = False

    
def update(client, userdata, msg, name):
    if msg.topic == named_base_str + "update":  #make sure this is an update for the correct device  #I believe this SHOULD be an extraneous check but dont want to remove it
        
        decoded_str = json.loads(msg.payload)        #load the payload into a json dict

        if 'desired' in decoded_str['state']:          #check if desired is a field in the json dict
            #This should update desired will all passed keys from update message
            #any differences between desired and reported state will be handled in delta function
            print("entered desired")
            for k, v in decoded_str['state']['desired'].items():
                if k in curr_state['state']['reported'] and curr_state['state']['reported'][k] == decoded_str['state']['desired'][k]:
                    continue
                curr_state['state']['desired'][k] = v        #set the desired state of the shadow equal to the received message

        if 'reported' in decoded_str['state']: #load json here, update current state of device, log data, publish to accepted topic so that device knows data got through
            for k, v in decoded_str['state']['reported'].items():         #this block updates the shadow with the new reported state
                curr_state['state']['reported'][k] = v

            behaviors(shadow, client)
            

def delta(client, name):
    #This func should compare desired and reported sub keys and add any differences into the delta key
    #then this should check if the device is connected and if so the keys in delta should be published to the device via the '/update/delta' topic
    #the device will change state to match and then publish a reported update to shadow
    for k, v in curr_state['state']['desired'].copy().items():            #iterate through desired keys
        if k in curr_state['state']['reported']:
            if curr_state['state']['reported'][k][0] != v:                #if key is in reported and desired value doesnt match reported value
                curr_state['state']['delta'][k] = v
        else:
            curr_state['state']['delta'][k] = v
            continue
        if curr_state['state']['delta'][k][0] == curr_state['state']['reported'][k][0]:
            del curr_state['state']['delta'][k]
        if curr_state['state']['reported'][k][0] == curr_state['state']['desired'][k][0]:
            del curr_state['state']['desired'][k]

    #once the curr state has been finalized, call parse_tags() here
    if not shadow:
        parse_tags(client, name)

    global connected
    
    if connected == True and len(curr_state['state']['delta']) != 0:
        str = json.dumps(curr_state['state']['delta'])
        client.publish(unnamed_base_str + "update/delta", str)       #publish keys in delta to device
    
def parse_tags(client, name):
    tag_list = []
    
    for k, v in curr_state['state']['reported'].items():   #DONT modify curr_state in this loop, just generate list of present tags
        if len(v) > 1:  
            for x in v:
                if not str(x).isnumeric():
                    tag_list.append(x)

    print(tag_list)

    for x in tag_list:
        sub_dict = json_generator()
        for k, v in curr_state['state']['reported'].items():
            for i in v:
                if i == x:
                    sub_dict['state']['reported'][k] = v[0]
        print(x)
        print(sub_dict)
        client.publish(unnamed_base_str + "name/" + x + "/update", json.dumps(sub_dict))

def mytimecalculations(StartTime=None, EndTime=None):
    """ This only computes the running time. Returns in milliseconds
    """
    if isinstance(StartTime, str):
        try:
            StartTime = datetime.datetime.strptime(
                StartTime, "%Y-%m-%d %H:%M:%S.%f")
        except:
            StartTime = datetime.datetime.strptime(
                StartTime, "%Y-%m-%d %H:%M:%S,%f")
    if isinstance(EndTime, str):
        try:
            EndTime = datetime.datetime.strptime(
                EndTime, "%Y-%m-%d %H:%M:%S.%f")
        except:
            EndTime = datetime.datetime.strptime(
                EndTime, "%Y-%m-%d %H:%M:%S,%f")
    delta = EndTime - StartTime
    elapsed_ms = (delta.days * 86400000.0) + (delta.seconds *
                                              1000.0) + (delta.microseconds / 1000.0)
    return elapsed_ms

client = mqtt.Client()
client.on_message = on_message
client.on_connect = on_connect
client.username_pw_set(username="counter_shadow", password="counter_password")

#load in last recorded state from json, if json not found then make shadow file
if not shadow:
    if os.path.exists(device_name + "_shadow.json"):
        file_in = open(device_name + "_shadow.json")
        curr_state = json.load(file_in)
        file_in.close()
    else:
        print("shadow not found, making new one")
        logger.info("shadow json not found, creating file " + device_name + "_shadow.json")
        curr_state = json_generator()
        file_out = open(device_name + "_shadow.json", "w")
        json.dump(curr_state, file_out)
        file_out.close
if shadow:
    shadow_file_name = device_name + "_" + sys.argv[2] + "_shadow.json"
    if os.path.exists(shadow_file_name):
        file_in = open(shadow_file_name)
        curr_state = json.load(file_in)
        file_in.close()
    else:
        print("shadow not found, making new one")
        logger.info("shadow json not found, creating file " + shadow_file_name)
        curr_state = json_generator()
        file_out = open(shadow_file_name, "w")
        json.dump(curr_state, file_out)
        file_out.close

client.connect("localhost", 1883, 60)

try:
    client.loop_forever()
except KeyboardInterrupt:
    logger.warning("Exception type - " + str(sys.exc_info()[0]))
    logger.info("Writing current state to json shadow: " + json.dumps(curr_state))     #right before client shutdown, write current state to json
    output_stream = open(device_name + "_shadow.json", "w")
    json.dump(curr_state, output_stream)
    output_stream.close()
except Exception:
    logger.critical("Unexpected exception of type - " + str(sys.exc_info()[0]))
    logger.info("Writing current state to json shadow: " + json.dumps(curr_state))     #right before client shutdown, write current state to json
    output_stream = open(device_name + "_shadow.json", "w")
    json.dump(curr_state, output_stream)
    output_stream.close()