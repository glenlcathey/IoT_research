import subprocess
import sys
from json import JSONEncoder
import json


#def install(package):
    #subprocess.check_call([sys.executable, "-m", "pip", "install", package])      NOT SURE IF MQTT REQUIRED BECAUSE THERE WILL BE INSTANCE OF DEVICE IN CLIENT FILE SCRIPT

#install("paho-mqtt")

#import paho.mqtt.client as mqtt

class device:
    name = None
    connected = None
    last_state = None
    #things this class needs to do:
    #manage(update) device state in json
    #log device data to json
    #act as middleman for device data - publish to topics
    def __init__(self, srcName):
        self.name = srcName
        #with open("data_file.json", "w") as write_file:
        print(deviceEncoder().encode(self))

    def generalCallback(self, client, userdata, message, topic):
        print(str(message))
        #with open("data_file.json", "w") as write_file:
        #    json.dump(str(message), write_file)
        self.appendJson(message, "data_file.json")
        #msg data pushed to json here

    def appendJson(self, data, filename):
        with open(filename, 'r') as json_file:
            temp = json.load(json_file)
            temp = temp + str(data)
        with open(filename, 'w') as json_file:
            json.dump(temp, json_file)

class deviceEncoder(JSONEncoder):
    def default(self, object):
        if isinstance(object, device):
            return object.__dict__
        else:
            return json.JSONEncoder.default(self, object)
