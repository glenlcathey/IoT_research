#HOW TO INTERACT WITH THIS FILE:
#python3 full_default_client.py -n 100 -t 20
#-n indicates number of tags
#-t number of trials
#if it throws a json error on run, delete the saved json

import json
import os
import logging
import datetime
import time
import argparse
import parser
import collections
import paho.mqtt.client as mqtt

client_userdata = {}
# list holding the average timing for each number of tags
timing = collections.defaultdict(list)
curr_state = {}
publish_dict = {}
connected = False


def parse_args():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "-d",
        "--device_name",
        type=str,
        required=False,
        default="device",
        help="Name of the device. Used for MQTT topics. Defaults to 'device'",
    )
    parser.add_argument(
        "-s",
        "--shadow",
        dest="shadow",
        required=False,
        default=False,
        action="store_true",
        help="If present `--shadow`, indicates this client is a tag shadow. Requires the shadow_name tag. ",
    )
    parser.add_argument(
        "-sn",
        "--shadow_name",
        dest="shadow_name",
        required=False,
        help="Name of the indicated shadow.",
    )
    parser.add_argument(
        "-nt",
        "--num_tags",
        type=int,
        required=False,
        default=5,
        help="The number of tags given to each key-value pair.",
    )
    parser.add_argument(
        "-np",
        "--num_pairs",
        type=int,
        required=False,
        default=100,
        help="The number of key-value pairs the system will incriment to before emptying the json and starting another trial.",
    )
    parser.add_argument(
        "-t",
        "--num_trials",
        type=int,
        required=False,
        default=10,
        help="The number of trials run for each incrementing number of tags",
    )
    parser.add_argument(
        "-o",
        "--output_file",
        type=str,
        required=False,
        default=f"timing_output_{datetime.datetime.now()}.txt",
        help="File to write timing results to",
    )
    args = parser.parse_args()
    return args


def resolve_publishes(client, publish_dict):
    for k, v in publish_dict.items():
        # print(f"KEY: {k}\nVALUE: {v}\n\n")
        client.publish(k, v)
    publish_dict = {}
    return publish_dict


def setup_logger(name, log_file, level=logging.INFO):
    """Function setup as many loggers as you want"""
    handler = logging.FileHandler(log_file)
    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    handler.setFormatter(formatter)
    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.addHandler(handler)
    return logger


def json_generator():
    empty_dict = {"state": {"desired": {}, "reported": {}, "delta": {}}}
    return empty_dict


def stop_collection(file_name, timing):
    with open(file_name, "w") as f:
        json.dump(timing, f)
    print(f"FINAL TIMING AT STOP_COLLECTION: {timing}")
    raise KeyboardInterrupt


def behaviors(client):  # Define client specific behaviors in this function.
    # print(f"NUM_TAGS: {client_userdata['num_tags']}")
    # print("enter behaviours")
    # print(f"BEHAVIORS CLIENT CURR_STATE: {client_userdata['curr_state']}")
    """

    first_key_str = list(client_userdata["curr_state"]["state"]["reported"].items())[0][
        0
    ]
    first_key_val = list(client_userdata["curr_state"]["state"]["reported"].items())[0][
        1
    ]

    # change the value of the first key and add another key
    if (len(first_key_val) <= client_userdata["num_tags"]):
        tag_str = f"TAG_{len(first_key_val)}"
        client_userdata["curr_state"]["state"]["desired"][first_key_str] = first_key_val.copy()
        client_userdata["curr_state"]["state"]["desired"][first_key_str].append(tag_str)

        # print(f"LENGTH_ IS FROM: {client_userdata['curr_state']['state']['reported']}")
        key_str = f"value_{len(client_userdata['curr_state']['state']['reported'])}"
        client_userdata["curr_state"]["state"]["desired"][key_str] = [-1]

    # update this var now that the value of the first key has changed
    first_key_val = list(client_userdata["curr_state"]["state"]["reported"].items())[0][1]

    # update all other keys present in desired to match the first key value
    for key, value in client_userdata["curr_state"]["state"]["desired"].items():
        if key != first_key_str:
            client_userdata["curr_state"]["state"]["desired"][key] = first_key_val
    """

    #================================================================================================================================================================
    #print(client_userdata["curr_state"]["state"]["reported"])
    
    first_key_str = list(client_userdata["curr_state"]["state"]["reported"].items())[0][
        0
    ]
    first_key_val = list(client_userdata["curr_state"]["state"]["reported"].items())[0][
        1
    ]
    if len(list(client_userdata["curr_state"]["state"]["reported"].items())[0][1]) != (client_userdata["num_tags"] + 1): # if the first k-v pair does not have correct tags then add tags
        print("THIS SHOULD ONLY BE ENTERED AFTER A TRIAL RESET")
        print(client_userdata["curr_state"]["state"]["reported"])
        client_userdata["curr_state"]["state"]["reported"][first_key_str] = [0] #if we are in this conditional then the value attached to this pair needs to be emptied
        client_userdata["curr_state"]["state"]["desired"][first_key_str] = first_key_val.copy()
        for x in range(0, client_userdata["num_tags"]):
            tag_str = f"TAG_{x}"
            client_userdata["curr_state"]["state"]["desired"][first_key_str].append(tag_str)
        return
    #first k-v pair is verified to be correct at this point. should only need to copy the first k-v pair and append it to the end of the desired below here
    first_key_val = list(client_userdata["curr_state"]["state"]["reported"].items())[0][
        1
    ]
    append_key_str = f"value_{len(client_userdata['curr_state']['state']['reported'])}"
    client_userdata["curr_state"]["state"]["desired"][append_key_str] = first_key_val # add a k-v pair that is equivalent to the first k-v pair



def subscription_setup(client):  # TODO add the rest of aws api subscription setup
    client.subscribe(client_userdata["named_base_str"] + "update")
    client.subscribe(client_userdata["named_base_str"] + "get")
    client.subscribe(f"devices/{client_userdata['device_name']}/connected")
    print(
        f"successfully setup subscriptions to: devices/{client_userdata['device_name']}/connected"
    )


def on_connect(client, userdata, flags, rc):
    logger.info(f"Connected to broker with result code: {rc}")
    # Subscribing in on_connect() means that if we lose the connection and
    # reconnect then subscriptions will be renewed.
    subscription_setup(client)


def on_message(client, userdata, msg):
    # print(f"Incoming message:\n\ttopic = {msg.topic}\n\tmessage = {msg.payload}")
    if msg.topic.find("update") != -1:  # topic contains update
        msg.payload = msg.payload.decode("utf-8")

        StartClock = datetime.datetime.now()  # Starting clock HERE

        update(client, userdata, msg, client_userdata["device_name"])
        # logger.debug("State after update function" + json.dumps(curr_state))
        # NOTE does delta need to be called here or only after desired message received
        delta(client, client_userdata["device_name"])
        parse_tags(client)

        # potential publish to device

        EndClock = datetime.datetime.now()
        TIMER = mytimecalculations(StartClock, EndClock)
        logger.info(TIMER)

        resolve_publishes(client, publish_dict)

        if client_userdata["trial_counter"] < client_userdata["num_trials"]:
            # hardcoded take the length of the 'value' key and subtract one to find the associated timing index
            timer_index = (
                len(client_userdata["curr_state"]["state"]["reported"])
            )
            if timer_index == 1 and len(client_userdata["curr_state"]["state"]["reported"]["value"]) != (client_userdata["num_tags"] + 1):
                timer_index = 0
            print(
                f"\tTIME: {TIMER}ms\tfor TIMING INDEX: {timer_index} of {client_userdata['num_pairs']} and "
                f"TRIAL: {client_userdata['trial_counter']} of {client_userdata['num_trials']}"
            )
            # add the amount of time scaled by the number of trials to the list index for that number of tags
            timing[timer_index].append(TIMER)
        elif client_userdata["trial_counter"] == client_userdata["num_trials"]:
            stop_collection(f"{userdata['timing_file']}", timing)

        # this could check len of list for first key or it could check number of key-value pairs present
        if (
            len(client_userdata["curr_state"]["state"]["reported"])
        ) == client_userdata["num_pairs"]:
            print("ENTERED THE IF CHECK WHERE THE SYSTEM SHOULD RESET")
            client_userdata["trial_counter"] += 1
            print(f"Trial {client_userdata['trial_counter']} complete")
            client_userdata["curr_state"]["state"]["reported"] = {}
            client_userdata["curr_state"]["state"]["reported"]['value'] = [0]
            client_userdata["curr_state"]["state"]["desired"] = {}
            client_userdata["curr_state"]["state"]["delta"] = {}
            print(client_userdata["curr_state"]["state"]["reported"])
            client.publish(
                client_userdata["unnamed_base_str"] + "update/delta",
                json.dumps(client_userdata["curr_state"]["state"]["reported"]),
            )

        # print(client_userdata['curr_state'])
        # logger.info(f"State after /update message processed: {json.dumps(client_userdata['curr_state'])}")

    if msg.topic.find("connected") != -1:  # topic contains connected
        global connected
        if msg.payload.decode("utf-8") == "1":
            print(f"<{client_userdata['device_name']}> connected")
            connected = True
            print(f"IS THERE A SHADOW?: {client_userdata['shadow']}")
            if client_userdata["shadow"]:
                emp = json_generator()  # why does this need to be a string??
                emp["shadow"] = client_userdata["shadow_name"]
                client.publish(f"{client_userdata['unnamed_base_str']}update/delta",
                    json.dumps(emp))
        if msg.payload.decode("utf-8") == "0":
            connected = False


def update(client, userdata, msg, name):
    # make sure this is an update for the correct device  #I believe this SHOULD be an extraneous check but dont want to remove it
    if (msg.topic == client_userdata["named_base_str"] + "update"):
        decoded_str = json.loads(msg.payload)  # load the payload into a json dict

        if ("desired" in decoded_str["state"]):
            # This should update desired will all passed keys from update message
            # any differences between desired and reported state will be handled in delta function
            print("entered desired")
            for k, v in decoded_str["state"]["desired"].items():
                if (
                    k in client_userdata["curr_state"]["state"]["reported"]
                    and client_userdata["curr_state"]["state"]["reported"][k]
                    == decoded_str["state"]["desired"][k]
                ):
                    continue
                # set the desired state of the shadow equal to the received message
                client_userdata["curr_state"]["state"]["desired"][k] = v

        # load json here, update current state of device, log data, publish to accepted topic so that device knows data got through
        if "reported" in decoded_str["state"]:
            # print(f"DECODED STR: {decoded_str['state']['reported']}")
            # print(f"CURR STR: {client_userdata['curr_state']}")

            # this block updates the shadow with the new reported state
            for k, v in decoded_str["state"]["reported"].items():
                client_userdata["curr_state"]["state"]["reported"][k] = v

            behaviors(client)


def delta(client, name):
    # This func should compare desired and reported sub keys and add any differences into the delta key
    # then this should check if the device is connected and if so the keys in delta should be published to the device via the '/update/delta' topic
    # the device will change state to match and then publish a reported update to shadow

    for k, v in (
        client_userdata["curr_state"]["state"]["desired"].copy().items()
    ):  # iterate through desired keys
        if k in client_userdata["curr_state"]["state"]["reported"]:
            # if key is in reported and desired value doesnt match reported value
            if client_userdata["curr_state"]["state"]["reported"][k] != v:
                client_userdata["curr_state"]["state"]["delta"][k] = v
        else:
            client_userdata["curr_state"]["state"]["delta"][k] = v
            continue
        if (k in client_userdata["curr_state"]["state"]["delta"]) and (
            client_userdata["curr_state"]["state"]["delta"][k]
            == client_userdata["curr_state"]["state"]["reported"][k]
        ):
            del client_userdata["curr_state"]["state"]["delta"][k]
        if (
            client_userdata["curr_state"]["state"]["reported"][k]
            == client_userdata["curr_state"]["state"]["desired"][k]
        ):
            del client_userdata["curr_state"]["state"]["desired"][k]

    # once the curr state has been finalized, call parse_tags() here
    if not client_userdata["shadow"]:
        parse_tags(client)

    global connected
    global publish_dict

    if (connected is True) and (
        len(client_userdata["curr_state"]["state"]["delta"]) != 0
    ):
        str = json.dumps(client_userdata["curr_state"]["state"]["delta"])
        # client.publish(unnamed_base_str + "update/delta", str)       # publish keys in delta to device
        topic_str = client_userdata["unnamed_base_str"] + "update/delta"
        publish_dict[topic_str] = str


def parse_tags(client):
    tag_list = [
        x
        for key, value in client_userdata["curr_state"]["state"]["reported"].items()
        if (len(value) > 1)
        for x in value
        if not str(x).isnumeric()
    ]  # I think this will have duplicates
    tag_list = set(tag_list)  # remove duplicates

    # print("printing list comprehension result")
    # print(tag_list)

    for tag in tag_list:
        sub_dict = json_generator()
        for k, values in client_userdata["curr_state"]["state"]["reported"].items():
            for value in values:
                if value == tag:
                    sub_dict["state"]["reported"][k] = values[0]
        # client.publish(unnamed_base_str + "name/" + x + "/update", json.dumps(sub_dict))
        topic_str = f"{client_userdata['unnamed_base_str']}name/{tag}/update"
        publish_dict[topic_str] = json.dumps(sub_dict)


def mytimecalculations(StartTime=None, EndTime=None):
    """This only computes the running time. Returns in milliseconds"""
    if isinstance(StartTime, str):
        try:
            StartTime = datetime.datetime.strptime(StartTime, "%Y-%m-%d %H:%M:%S.%f")
        except:
            StartTime = datetime.datetime.strptime(StartTime, "%Y-%m-%d %H:%M:%S,%f")
    if isinstance(EndTime, str):
        try:
            EndTime = datetime.datetime.strptime(EndTime, "%Y-%m-%d %H:%M:%S.%f")
        except:
            EndTime = datetime.datetime.strptime(EndTime, "%Y-%m-%d %H:%M:%S,%f")
    delta = EndTime - StartTime
    elapsed_ms = (
        (delta.days * 86400000.0)
        + (delta.seconds * 1000.0)
        + (delta.microseconds / 1000.0)
    )
    return elapsed_ms


def main():
    global logger
    args = parse_args()

    if args.shadow and (args.shadow_name is None):
        raise parser.ParserError("--shadow requires --shadow_name.")
    if args.num_tags:
        client_userdata["num_tags"] = args.num_tags
    else:
        client_userdata["num_tags"] = 0
    if args.num_pairs:
        client_userdata["num_pairs"] = args.num_pairs
    if args.num_trials:
        client_userdata["num_trials"] = args.num_trials
        client_userdata["num_trials_modifier"] = 1.0 / (float(args.num_trials))
    if args.output_file:
        client_userdata["timing_file"] = args.output_file

    device_name = (
        args.device_name
    )  # this has a default val, so this assignment doesn't need a check
    client_userdata["trial_counter"] = 0
    client_userdata["shadow"] = args.shadow
    client_userdata["shadow_name"] = args.shadow_name
    client_userdata["device_name"] = device_name
    client_userdata[
        "named_base_str"
    ] = f"devices/{client_userdata['device_name']}/shadow/"
    client_userdata["unnamed_base_str"] = client_userdata["named_base_str"]

    log_file_name = client_userdata["device_name"]
    if client_userdata["shadow"]:
        client_userdata[
            "named_base_str"
        ] = f"{client_userdata['named_base_str']}name/{client_userdata['shadow_name']}/"
        log_file_name = f"{log_file_name}_{client_userdata['shadow_name']}"
    log_file_name = f"{log_file_name}.log"
    logger = setup_logger("", log_file_name, level=logging.DEBUG)

    client = mqtt.Client(userdata=client_userdata)
    client.on_message = on_message
    client.on_connect = on_connect
    client.username_pw_set(username="counter_shadow", password="counter_password")

    # load in last recorded state from json, if json not found then make shadow file
    if client_userdata["shadow"] is False:
        if os.path.exists(f"{client_userdata['device_name']}_shadow.json"):
            with open(f"{client_userdata['device_name']}_shadow.json", "r") as f:
                client_userdata["curr_state"] = json.load(f)
        else:
            print("shadow not found, making new one")
            logger.info(
                f"shadow json not found, creating file {client_userdata['device_name']}_shadow.json"
            )
            client_userdata["curr_state"] = json_generator()
            with open(client_userdata["device_name"] + "_shadow.json", "w") as f:
                json.dump(curr_state, f)
    if client_userdata["shadow"]:
        shadow_file_name = f"{client_userdata['device_name']}_{client_userdata['shadow_name']}_shadow.json"
        if os.path.exists(shadow_file_name):
            with open(shadow_file_name, "r") as f:
                client_userdata["curr_state"] = json.load(f)
        else:
            print("shadow not found, making new one")
            logger.info(f"shadow json not found, creating file {shadow_file_name}")
            client_userdata["curr_state"] = json_generator()
            with open(shadow_file_name, "w") as f:
                json.dump(client_userdata["curr_state"], f)
    client.connect("localhost", 1883, 60)

    try:
        client.loop_forever()
    except KeyboardInterrupt:
        logger.warning(f"Exception type - Keyboard Interrupt")
        # right before client shutdown, write current state to json
        logger.info(
            f"Writing current state to json shadow: {json.dumps(client_userdata['curr_state'])}"
        )
        with open(f"{client_userdata['device_name']}_shadow.json", "w") as f:
            json.dump(client_userdata["curr_state"], f)


if __name__ == "__main__":
    main()
