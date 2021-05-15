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
import argparse
import math

def install(package):
    subprocess.check_call([sys.executable, "-m", "pip", "install", package])

install("paho-mqtt") #ensure mqtt library installed
import paho.mqtt.client as mqtt

#timing variables defined here
timing = []                 #list holding the average timing for each number of tags
num_trials = 0              #int holding how many trials to do for each number of tags
trial_counter = 0           #int counter var holding the current number of trials done for the current number of tags (gets reset with each tag addition)
num_trials_modifier = 0.0   #float to use as modifier for each time i.e. if num trials is 5 this will be 0.2. mult each result by this value and add it to the related timing array index
num_tags = 0                #the number of tags to incriment to 
timing_file = ""            #the file to write timing results to
done = False

#core frequently interacted with variables setup here
curr_state = {}
publish_dict = {}
shadow = False
connected = False
device_name = ""   #defaults to 'device'
named_base_str = ""
unnamed_base_str = ""
log_file_name = ""
    
def resolve_publishes(client):
    global publish_dict
    for k, v in publish_dict.items():
        client.publish(k, v)
    publish_dict = {}

def setup_logger(name, log_file, level=logging.INFO):
    """Function setup as many loggers as you want"""
    handler = logging.FileHandler(log_file)
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.addHandler(handler)
    return logger

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

def behaviors():           #Define client specific behaviors in this function.
    global num_tags
    #print("enter behaviours")
    #print(curr_state)

    first_key_str = list(curr_state['state']['reported'].items())[0][0]
    first_key_val = list(curr_state['state']['reported'].items())[0][1]

    if len(first_key_val) <=  num_tags:                                     #change the value of the first key and add another key
        tag_str = "TAG_" + str(len(first_key_val))
        curr_state['state']['desired'][first_key_str] = first_key_val.copy()              
        curr_state['state']['desired'][first_key_str].append(tag_str)

        key_str = "value_"
        key_str = key_str + str(len(curr_state['state']['reported']))
        curr_state['state']['desired'][key_str] = [-1]

    first_key_val = list(curr_state['state']['reported'].items())[0][1]     #update this var now that the value of the first key has changed

    for key, value in curr_state['state']['desired'].items():              #update all other keys present in desired to match the first key value
        if key != first_key_str:
            curr_state['state']['desired'][key] = first_key_val     
    
    """
    for key, value in curr_state['state']['reported'].items():
        if len(value) <=  num_tags:
            tag_str = "TAG_" + str(len(value))
            curr_state['state']['desired'][key] = value.copy()              
            curr_state['state']['desired'][key].append(tag_str)
        #print("key = " + str(key))
        #print("value = " + str(value))
    if len(curr_state['state']['reported']) < num_tags:
        tmp_str = "value_"
        tmp_str = tmp_str + str(len(curr_state['state']['reported']))
        curr_state['state']['desired'][tmp_str] = list(curr_state['state']['reported'].items())[0][1]    #copy the contents of the base value key into the newest key
        #print("this should be the value of the first key: " + str(list(curr_state['state']['reported'].items())[0][1]))
        
    print("leaving behaviours")
    print(curr_state)
    """

def stop_collection():
    global timing
    for x in range(len(timing)):
        print(str(x) + " - " + str(round(timing[x],4)))
    raise KeyboardInterrupt

def parse_args():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "-d",
        "--device_name",
        type=str,
        required=False,
        default='device',
        help="Name of the device. Used for MQTT topics. Defaults to 'device'",
    )
    parser.add_argument(
        "-s",
        "--shadow",
        type=str,
        required=False,
        help="If present, indicates this client is a tag shadow.",
    )
    parser.add_argument(
        "-n",
        "--num_tags",
        type=int,
        required=False,
        help="The number of tags given to each key-value pair",
    )
    parser.add_argument(
        "-t",
        "--num_trials",
        type=int,
        required=False,
        help="The number of trials run for each incrimenting number of tags",
    )
    parser.add_argument(
        "-o",
        "--output_file",
        type=str,
        required=False,
        help="File to write timing results to",
    )
    

    args = parser.parse_args()
    #print(args)

    return args


def subscription_setup(client):      #TODO add the rest of aws api subscription setup
    global named_base_str
    global device_name
    client.subscribe(named_base_str + "update")
    client.subscribe(named_base_str + "get")
    client.subscribe("devices/" + device_name + "/connected")
    print("successfully setup subscriptions")
    
def on_connect(client, userdata, flags, rc):
    logger.info("Connected to broker with result code: " + str(rc))
    # Subscribing in on_connect() means that if we lose the connection and
    # reconnect then subscriptions will be renewed.
    subscription_setup(client)

def on_message(client, userdata, msg):
    #logger.debug("Incoming message: topic = " + str(msg.topic) + " message = " + str(msg.payload))

    if msg.topic.find("update") != -1:          #topic contains update
        msg.payload = msg.payload.decode("utf-8")

        #make list

        StartClock = datetime.datetime.now()                                                    # Starting clock HERE

        update(client, userdata, msg, device_name)
        #logger.debug("State after update function" + json.dumps(curr_state))
        delta(client, device_name)                                                              #NOTE does delta need to be called here or only after desired message received
        parse_tags(client)

        #potential publish to device 

        EndClock = datetime.datetime.now()
        TIMER = mytimecalculations(StartClock, EndClock)
        logger.info(TIMER)

        resolve_publishes(client)

        global trial_counter
        global num_tags
        global num_trials
        global num_trials_modifier
        global unnamed_base_str
        global curr_state

        #print("length of value list")
        #print(len(curr_state['state']['reported']['value']) - 1)

        if trial_counter == 0:          #in the first loop through, populate the list with initial timer values
            timing.append(TIMER*num_trials_modifier)
            print(len(list(curr_state['state']['reported'].items())[0][1]) - 1)
            print(timing[len(list(curr_state['state']['reported'].items())[0][1]) - 1])
        elif trial_counter < num_trials:
            timer_index = len(list(curr_state['state']['reported'].items())[0][1]) - 1             #hardcoded take the length of the 'value' key and subtract one to find the associated timing index
            print(timer_index)
            print(TIMER)
            timing[timer_index] = timing[timer_index] + (TIMER*num_trials_modifier)     #add the amount of time scaled by the number of trials to the list index for that number of tags
        elif trial_counter == num_trials:
            #this means the loop of incrimenting number of tags should stop
            stop_collection()
    
        if (len(curr_state['state']['reported']['value']) - 1) == num_tags:             #this could check len of list for first key or it could check number of key-value pairs present
            trial_counter = trial_counter + 1
            print("trial " + str(trial_counter) + " complete")
            for k,v in curr_state['state']['reported'].items():
                curr_state['state']['reported'][k] = [v[0]]
            curr_state['state']['desired'] = {}
            curr_state['state']['delta'] = {}
            client.publish(unnamed_base_str + "update/delta", json.dumps(curr_state['state']['reported']))



        #print(curr_state)
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
            #print(decoded_str)
            for k, v in decoded_str['state']['reported'].items():         #this block updates the shadow with the new reported state
                curr_state['state']['reported'][k] = v

            behaviors()
            

def delta(client, name):
    #This func should compare desired and reported sub keys and add any differences into the delta key
    #then this should check if the device is connected and if so the keys in delta should be published to the device via the '/update/delta' topic
    #the device will change state to match and then publish a reported update to shadow

    for k, v in curr_state['state']['desired'].copy().items():            #iterate through desired keys
        if k in curr_state['state']['reported']:
            if curr_state['state']['reported'][k] != v:                #if key is in reported and desired value doesnt match reported value
                curr_state['state']['delta'][k] = v
        else:
            curr_state['state']['delta'][k] = v
            continue
        if (k in curr_state['state']['delta']) and (curr_state['state']['delta'][k] == curr_state['state']['reported'][k]):
            del curr_state['state']['delta'][k]
        if curr_state['state']['reported'][k] == curr_state['state']['desired'][k]:
            del curr_state['state']['desired'][k]

    #once the curr state has been finalized, call parse_tags() here
    if not shadow:
        parse_tags(client)

    global connected
    global unnamed_base_str
    global publish_dict
    
    if connected == True and len(curr_state['state']['delta']) != 0:
        str = json.dumps(curr_state['state']['delta'])
        #client.publish(unnamed_base_str + "update/delta", str)       #publish keys in delta to device
        topic_str = unnamed_base_str + "update/delta"
        publish_dict[topic_str] = str
    
def parse_tags(client):
    """
    tag_list = []
    
    for k, v in curr_state['state']['reported'].items():   #DONT modify curr_state in this loop, just generate list of present tags
        if len(v) > 1:  
            for x in v:
                if not str(x).isnumeric():
                    tag_list.append(x)
    """

    tag_list = [x for key, value in curr_state['state']['reported'].items() if (len(value) > 1) for x in value if not str(x).isnumeric()] #I think this will have duplicates
    tag_list = set(tag_list) #remove duplicates

    #print("printing list comprehension result")
    #print(tag_list)
    #print()

    for tag in tag_list:
        sub_dict = json_generator()
        for k, values in curr_state['state']['reported'].items():
            for value in values:
                if value == tag:
                    sub_dict['state']['reported'][k] = values[0]
        #client.publish(unnamed_base_str + "name/" + x + "/update", json.dumps(sub_dict))
        topic_str = unnamed_base_str + "name/" + tag + "/update"
        #print("Printing sub dict for " + tag + ": ")
        #print(sub_dict)
        publish_dict[topic_str] = json.dumps(sub_dict)

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

def main():
    global logger
    global shadow
    global named_base_str
    global unnamed_base_str
    global curr_state
    global device_name
    global num_tags
    global num_trials
    global num_trials_modifier

    args = parse_args()

    if args.num_tags:
        num_tags = args.num_tags
    if args.num_trials:
        num_trials = args.num_trials
        num_trials_modifier = 1.0/(float(args.num_trials))
    if args.output_file:
        timing_file = args.output_file
    else:
        timing_file = "timing_output_" + str(datetime.datetime.now()) + ".txt"
    device_name = args.device_name          #this has a default val, so this assignment doesn't need a check
    named_base_str = "devices/" + device_name + "/shadow/"
    unnamed_base_str = named_base_str
    log_file_name = device_name
    if args.shadow:
        named_base_str = named_base_str + "name/" + args.shadow + "/"
        shadow = True
        log_file_name = log_file_name + "_" + args.shadow
    log_file_name = log_file_name + ".log"

    logger = setup_logger('', log_file_name, level=logging.DEBUG)

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
    """
    except Exception:
        logger.critical("Unexpected exception of type - " + str(sys.exc_info()[0]))
        logger.info("Writing current state to json shadow: " + json.dumps(curr_state))     #right before client shutdown, write current state to json
        output_stream = open(device_name + "_shadow.json", "w")
        json.dump(curr_state, output_stream)
        output_stream.close()
    """

if __name__ == "__main__":
    main()
