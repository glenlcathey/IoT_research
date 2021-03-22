/*******************************************************************************
 * Copyright (c) 2012, 2020 IBM Corp.
 *
 * All rights reserved. This program and the accompanying materials
 * are made available under the terms of the Eclipse Public License v2.0
 * and Eclipse Distribution License v1.0 which accompany this distribution. 
 *
 * The Eclipse Public License is available at 
 *   https://www.eclipse.org/legal/epl-2.0/
 * and the Eclipse Distribution License is available at 
 *   http://www.eclipse.org/org/documents/edl-v10.php.
 *
 * Contributors:
 *    Ian Craggs - initial contribution
 *******************************************************************************/

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "MQTTClient.h"

#define ADDRESS     "tcp://localhost:1883"
#define CLIENTID    "ESP32"
#define DEVICE_NAME "esp32"  
#define QOS         1
#define TIMEOUT     10000L

volatile MQTTClient_deliveryToken deliveredtoken;

void delivered(void *context, MQTTClient_deliveryToken dt)
{
    printf("Message with token value %d delivery confirmed\n", dt);
    deliveredtoken = dt;
}

int msgarrvd(void *context, char *topicName, int topicLen, MQTTClient_message *message)  //could eventually run into issues because not utf-8 decoding
{
    char[] msg = (char*)message->payload;
    printf("Message arrived\n");
    printf("     topic: %s\n", topicName);
    printf("   message: %.*s\n", message->payloadlen, msg);
    if (strstr(topicName, "delta") != NULL) {
        parseDelta(msg);                        //use separate function for parsing so that other topic functionality could be added to this function later
    }
    MQTTClient_freeMessage(&message);
    MQTTClient_free(topicName);
    return 1;
}

void parseDelta(char* msg)
{
    //add json code here to parse the inc desired state
}

void connlost(void *context, char *cause)
{
    printf("\nConnection lost\n");
    printf("     cause: %s\n", cause);
}

void publishConnected(MQTTClient *client) 
{

}

void setupSubscriptions(MQTTClient *client) //might need to pass client by reference
{
    int check;
    char[29 + strlen(DEVICE_NAME)] topic = "devices/";  //allocate 29 bytes for update delta topic length + length of device name
    strcat(topic, DEVICE_NAME);
    strcat(topic, "/shadow/update/delta");
    if ((check = MQTTClient_subscribe(client, topic, QOS)) != MQTTCLIENT_SUCCESS) {
    	printf("Failed to subscribe to %s, return code %d\n", topic, check);
    }
}

void setupLastWill(MQTTClient_willOptions *lwt)
{
    lwt->retained = 1;
    char[strlen(DEVICE_NAME) + 18] topic = "devices/";        //allocate 18 bytes for connected message topic + length of device name
    strcat(topic, DEVICE_NAME);
    strcat(topic, "/connected");
    strcpy(lwt->topicName, topic);
    strcpy(lwt->message, "0");
}

int main(int argc, char* argv[])
{
    MQTTClient client;
    MQTTClient_connectOptions conn_opts = MQTTClient_connectOptions_initializer;
    MQTTClient_willOptions lwt = MQTTClient_willOptions_initializer;
    setupLastWill(&lwt);
    conn_opts.will = &lwt;
    MQTTClient_message pubmsg = MQTTClient_message_initializer;
    MQTTClient_deliveryToken token;
    int rc;

    if ((rc = MQTTClient_create(&client, ADDRESS, CLIENTID,
        MQTTCLIENT_PERSISTENCE_NONE, NULL)) != MQTTCLIENT_SUCCESS)
    {
        printf("Failed to create client, return code %d\n", rc);
        rc = EXIT_FAILURE;
        goto exit;
    }

    if ((rc = MQTTClient_setCallbacks(client, NULL, connlost, msgarrvd, delivered)) != MQTTCLIENT_SUCCESS)
    {
        printf("Failed to set callbacks, return code %d\n", rc);
        rc = EXIT_FAILURE;
        goto destroy_exit;
    }

    conn_opts.keepAliveInterval = 20;
    conn_opts.cleansession = 1;
    if ((rc = MQTTClient_connect(client, &conn_opts)) != MQTTCLIENT_SUCCESS)
    {
        printf("Failed to connect, return code %d\n", rc);
        rc = EXIT_FAILURE;
        goto destroy_exit;
    }

    setupSubscriptions(&client);

    pubmsg.payload = "1";
    pubmsg.payloadlen = (int)strlen("1");
    pubmsg.retain = 1;
    pubmsg.qos = 1;
    char[strlen(DEVICE_NAME) + 18] connectedTopic = "devices/";
    strcat(connectedTopic, DEVICE_NAME);
    strcat(connectedTopic, "/connected");
    if ((rc = MQTTClient_publishMessage(client, connectedTopic, &pubmsg, &token)) != MQTTCLIENT_SUCCESS)
    {
         printf("Failed to publish connected message, return code %d\n", rc);
         exit(EXIT_FAILURE);
    }

    
destroy_exit:
    MQTTClient_destroy(&client);
exit:
    return rc;
}
