# Overview
This project is separated into Client/Publisher architecture and is written in python. The client tracks and manages the state of the device using python dictionary objects 
(very similar to JSON) and the device reports its state to the client. An ACL list manages all permissions for communication between different clients and publishers.

The default_client and default_device files are provided with #NOTE comments indicating what must be changed for any specific implementation. The counter and light 
client/publisher pair can be used as reference for client-publisher as well as client-client communication.

# Interacting with the Client
In order to retrieve the current shadow from the client subscribe to topic 'devices/ "name" /shadow/get' and then publish an empty message to that topic.

In order to update the state of the device publish a desired state JSON to topic 'devices/ "name" /shadow/update'.
The structure of that JSON should reflect the structure described here - https://docs.aws.amazon.com/iot/latest/developerguide/device-shadow-data-flow.html

## Currently utilizes
Paho-MQTT - https://pypi.org/project/paho-mqtt/  
Mosquitto - https://mosquitto.org/  
Mimics AWS shadow API - https://docs.aws.amazon.com/iot/latest/developerguide/device-shadow-mqtt.html
C JSON lib - https://github.com/DaveGamble/cJSON

## Helpful Links
Tutorial for installing MicroPython firmware on ESP32 - https://docs.micropython.org/en/latest/esp32/tutorial/intro.html#esp32-intro  
Starting and stopping mosquitto broker installed with Homebrew - https://stackoverflow.com/questions/31045974/restarting-the-mosquito-broker/31113901  
Mosquitto config file man page - https://mosquitto.org/man/mosquitto-conf-5.html
