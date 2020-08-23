import subprocess
import sys

#def install(package):
    #subprocess.check_call([sys.executable, "-m", "pip", "install", package])      NOT SURE IF MQTT REQUIRED BECAUSE THERE WILL BE INSTANCE OF DEVICE IN CLIENT FILE SCRIPT

#install("paho-mqtt")

#import paho.mqtt.client as mqtt

class device:
    #things this class needs to do:
    #manage(update) device state in json
    #log device data to json
    #act as middleman for device data - publish to topics
    def __init__(self, srcName):
        self.name = srcName

    def generalCallback(self, client, userdata, message):
        currentTopic = message.topic
        payload = message.payload
        print(str(payload))

    
