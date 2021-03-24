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
#include <unistd.h>
#include "cJSON.h"

#define ADDRESS     "tcp://localhost:1883"
#define CLIENTID    "ESP32"
#define DEVICE_NAME "esp32"  
#define QOS         1
#define TIMEOUT     10000L

cJSON *data; /* this cJSON obj holds current state of device with the structure shown below
{                                                                                
    "state": {
        "reported": {
            "key": "value"
        }
    }
}
*/

volatile MQTTClient_deliveryToken deliveredtoken;

void delivered(void *context, MQTTClient_deliveryToken dt)
{
    printf("Message with token value %d delivery confirmed\n", dt);
    deliveredtoken = dt;
}

void parseDelta(char* msg)
{
    cJSON *msg_json = cJSON_Parse(msg); //load inc msg into json struct  NOTE: need to delete this object before exiting function
    if (msg_json == NULL) 
    {
        printf("Error parsing the received desired state into cJSON obj.");
        return;
    }
    cJSON *data_array = cJSON_GetObjectItem(data, "state");
    data_array = cJSON_GetObjectItem(data_array, "reported");
    while (cJSON_GetArraySize(msg_json) > 0) 
    {
        cJSON *temp = cJSON_DetachItemFromArray(msg_json, 0);
        if (temp == NULL) 
        {
            printf("Error retrieving array item from desired JSON. Breaking from loop.\n");
            break;
        }
        if (cJSON_HasObjectItem(data_array, temp->string)) //check if desired key is in reported already. If so, use cJSON update function
        {
            cJSON_SetNumberValue(cJSON_GetObjectItem(data_array, temp->string), cJSON_GetNumberValue(temp));
        }
        else
        {
            cJSON_SetValuestring(temp, temp->string);
            cJSON_AddItemToArray(data_array, temp);
        }
    }

}

int msgarrvd(void *context, char *topicName, int topicLen, MQTTClient_message *message)  //could eventually run into issues because not utf-8 decoding
{
    char* msg = (char*)message->payload;
    printf("Message arrived\n");
    printf("     topic: %s\n", topicName);
    printf("   message: %.*s\n", message->payloadlen, msg);
    if (strstr(topicName, "delta") != NULL) {
        parseDelta(msg);                        //use separate function for parsing so that other topic functionality could be added to this function later
        printf("\nPrinting cJSON obj after msg parsing function: \n%s\n\n", cJSON_Print(data));
    }
    MQTTClient_freeMessage(&message);
    MQTTClient_free(topicName);
    return 1;
}

void dataJsonInit()
{
    data = cJSON_CreateObject();
    cJSON *reported = cJSON_CreateObject();
    cJSON *keyPair = cJSON_CreateObject();
    cJSON_AddNumberToObject(keyPair, "value", 0);
    cJSON_AddItemToObject(reported, "reported", keyPair);
    cJSON_AddItemToObject(data, "state", reported);
    printf("%s", cJSON_Print(data));
}

void connlost(void *context, char *cause)
{
    printf("\nConnection lost\n");
    printf("     cause: %s\n", cause);
}

void publishConnected(MQTTClient *client, MQTTClient_message *pubmsg, MQTTClient_deliveryToken *token) 
{
    int check;
    pubmsg->payload = "1";
    pubmsg->payloadlen = (int)strlen("1");
    pubmsg->retained = 1;
    pubmsg->qos = 1;
    char connectedTopic[strlen(DEVICE_NAME) + 19] = "devices/";
    strcat(connectedTopic, DEVICE_NAME);
    strcat(connectedTopic, "/connected");
    if ((check = MQTTClient_publishMessage(*client, connectedTopic, pubmsg, token)) != MQTTCLIENT_SUCCESS)
    {
         printf("Failed to publish connected message, return code %d\n", check);
         exit(EXIT_FAILURE);
    }
}

void setupSubscriptions(MQTTClient *client) //might need to pass client by reference
{
    int check;
    char topic[29 + strlen(DEVICE_NAME)] = "devices/";  //allocate 29 bytes for update delta topic length + length of device name
    strcat(topic, DEVICE_NAME);
    strcat(topic, "/shadow/update/delta");
    if ((check = MQTTClient_subscribe(*client, topic, QOS)) != MQTTCLIENT_SUCCESS) {
    	printf("Failed to subscribe to %s, return code %d\n", topic, check);
    }
}

void setupLastWill(MQTTClient_willOptions *lwt)
{
    lwt->retained = 1;
    char *topic = (char*)malloc((strlen(DEVICE_NAME) + 19) * sizeof(char));     //dynamically allocate 19 bytes for connected message topic + length of device name
    strcpy(topic, "devices/");        
    strcat(topic, DEVICE_NAME);
    strcat(topic, "/connected");
    lwt->topicName = topic;
    lwt->message = "0";
}

void reportState(MQTTClient *client, MQTTClient_message *pubmsg, MQTTClient_deliveryToken *token)
{
    int check;
    pubmsg->payload = cJSON_PrintUnformatted(data);
    pubmsg->payloadlen = (int)strlen(cJSON_PrintUnformatted(data));
    pubmsg->retained = 0;
    pubmsg->qos = 0;
    char topic[23 + strlen(DEVICE_NAME)] = "devices/";  //allocate 23 bytes for update topic length + length of device name
    strcat(topic, DEVICE_NAME);
    strcat(topic, "/shadow/update");
    if ((check = MQTTClient_publishMessage(*client, topic, pubmsg, token)) != MQTTCLIENT_SUCCESS) {
    	printf("Failed to publish state to %s, return code %d\n", topic, check);
    }
}

int main(int argc, char* argv[])
{
    dataJsonInit();
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
    publishConnected(&client, &pubmsg, &token);
    
    while (1) 
    {
        reportState(&client, &pubmsg, &token);
        sleep(1);
    }

destroy_exit:
    free(conn_opts.will->topicName); //need to free dynamically allocated topic mem from setupLastWill func
    MQTTClient_destroy(&client);
exit:
    return rc;
}
