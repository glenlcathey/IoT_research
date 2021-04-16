/* Hello World Example

   This example code is in the Public Domain (or CC0 licensed, at your option.)

   Unless required by applicable law or agreed to in writing, this
   software is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR
   CONDITIONS OF ANY KIND, either express or implied.
*/
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "freertos/FreeRTOS.h"
#include "freertos/event_groups.h"
#include "freertos/task.h"
#include "esp_system.h"
#include "esp_spi_flash.h"
#include "esp_wifi.h"
#include "esp_event.h"
#include "nvs_flash.h"
#include "cJSON.h"
#include "mqtt_client.h"
#include "mqtt_config.h"

void client_start();
void parse_delta(char* msg);
void publish_connected();
void data_json_init();
void setup_subscriptions();
void report_state();

/* These are all definitions pertaining to wifi modules */
#define DEFAULT_SSID "SMD"
#define DEFAULT_PWD "GTX950TI"

/* These definitions pertain to MQTT client setup */
#define BROKER_IP "192.168.1.100"
#define PORT 1883
#define DEVICE_NAME "esp32"


#if CONFIG_EXAMPLE_WIFI_ALL_CHANNEL_SCAN
#define DEFAULT_SCAN_METHOD WIFI_ALL_CHANNEL_SCAN
#elif CONFIG_EXAMPLE_WIFI_FAST_SCAN
#define DEFAULT_SCAN_METHOD WIFI_FAST_SCAN
#else
#define DEFAULT_SCAN_METHOD WIFI_FAST_SCAN
#endif /*CONFIG_EXAMPLE_SCAN_METHOD*/

#if CONFIG_EXAMPLE_WIFI_CONNECT_AP_BY_SIGNAL
#define DEFAULT_SORT_METHOD WIFI_CONNECT_AP_BY_SIGNAL
#elif CONFIG_EXAMPLE_WIFI_CONNECT_AP_BY_SECURITY
#define DEFAULT_SORT_METHOD WIFI_CONNECT_AP_BY_SECURITY
#else
#define DEFAULT_SORT_METHOD WIFI_CONNECT_AP_BY_SIGNAL
#endif /*CONFIG_EXAMPLE_SORT_METHOD*/

#if CONFIG_EXAMPLE_FAST_SCAN_THRESHOLD
#define DEFAULT_RSSI CONFIG_EXAMPLE_FAST_SCAN_MINIMUM_SIGNAL
#if CONFIG_EXAMPLE_FAST_SCAN_WEAKEST_AUTHMODE_OPEN
#define DEFAULT_AUTHMODE WIFI_AUTH_OPEN
#elif CONFIG_EXAMPLE_FAST_SCAN_WEAKEST_AUTHMODE_WEP
#define DEFAULT_AUTHMODE WIFI_AUTH_WEP
#elif CONFIG_EXAMPLE_FAST_SCAN_WEAKEST_AUTHMODE_WPA
#define DEFAULT_AUTHMODE WIFI_AUTH_WPA_PSK
#elif CONFIG_EXAMPLE_FAST_SCAN_WEAKEST_AUTHMODE_WPA2
#define DEFAULT_AUTHMODE WIFI_AUTH_WPA2_PSK
#else
#define DEFAULT_AUTHMODE WIFI_AUTH_OPEN
#endif
#else
#define DEFAULT_RSSI -127
#define DEFAULT_AUTHMODE WIFI_AUTH_OPEN
#endif /*CONFIG_EXAMPLE_FAST_SCAN_THRESHOLD*/

esp_mqtt_client_handle_t global_client;

cJSON *data; /* this cJSON obj holds current state of device with the structure shown below
{                                                                                
    "state": {
        "reported": {
            "key": "value"
        }
    }
}
*/


static void wifi_event_handler(void* arg, esp_event_base_t event_base,
                                int32_t event_id, void* event_data)
{
    if (event_base == WIFI_EVENT && event_id == WIFI_EVENT_STA_START) {
        esp_wifi_connect();
    } else if (event_base == WIFI_EVENT && event_id == WIFI_EVENT_STA_DISCONNECTED) {
        esp_wifi_connect();
    } else if (event_base == IP_EVENT && event_id == IP_EVENT_STA_GOT_IP) {
        client_start(); //only start the client once an IP is received
    }
}

static esp_err_t mqtt_event_handler(esp_mqtt_event_handle_t event)
{
    esp_mqtt_client_handle_t client = event->client;
    int msg_id;
    // your_context_t *context = event->context;
    switch (event->event_id) {
        case MQTT_EVENT_CONNECTED:
            printf("client connected to broker\n");
            printf("calling connected func now\n");
            publish_connected();
            printf("ret from publish func\n");
            setup_subscriptions();
            printf("returned from subscription setup\n");
            break;
        case MQTT_EVENT_DISCONNECTED:
            printf("client disconnected\n");
            break;
        case MQTT_EVENT_SUBSCRIBED:
            break;
        case MQTT_EVENT_UNSUBSCRIBED:
            break;
        case MQTT_EVENT_PUBLISHED:
            printf("\nPrinting cJSON obj after state report: \n%s\n", cJSON_Print(data));
            break;
        case MQTT_EVENT_DATA:
            printf("TOPIC=%.*s\r\n", event->topic_len, event->topic);
            printf("DATA=%.*s\r\n", event->data_len, event->data);
            if (strstr(event->topic, "delta") != NULL) {
                parse_delta(event->data);
                printf("\nPrinting cJSON obj after msg parsing function: \n%s\n", cJSON_Print(data));
            }
            report_state();
            break;
        case MQTT_EVENT_ERROR:
            break;
        default:
            break;
    }
    return ESP_OK;
}


/* Initialize Wi-Fi as sta and set scan method */
static void wifi_connect(void)
{
    ESP_ERROR_CHECK(esp_netif_init());
    ESP_ERROR_CHECK(esp_event_loop_create_default());

    wifi_init_config_t cfg = WIFI_INIT_CONFIG_DEFAULT();
    ESP_ERROR_CHECK(esp_wifi_init(&cfg));

    ESP_ERROR_CHECK(esp_event_handler_instance_register(WIFI_EVENT, ESP_EVENT_ANY_ID, &wifi_event_handler, NULL, NULL));
    ESP_ERROR_CHECK(esp_event_handler_instance_register(IP_EVENT, IP_EVENT_STA_GOT_IP, &wifi_event_handler, NULL, NULL));

    // Initialize default station as network interface instance (esp-netif)
    esp_netif_t *sta_netif = esp_netif_create_default_wifi_sta();
    assert(sta_netif);

    // Initialize and start WiFi
    wifi_config_t wifi_config = {
        .sta = {
            .ssid = DEFAULT_SSID,
            .password = DEFAULT_PWD,
            .scan_method = DEFAULT_SCAN_METHOD,
            .sort_method = DEFAULT_SORT_METHOD,
            .threshold.rssi = DEFAULT_RSSI,
            .threshold.authmode = DEFAULT_AUTHMODE,
        },
    };
    ESP_ERROR_CHECK(esp_wifi_set_mode(WIFI_MODE_STA));
    ESP_ERROR_CHECK(esp_wifi_set_config(ESP_IF_WIFI_STA, &wifi_config));
    ESP_ERROR_CHECK(esp_wifi_start());
}

void data_json_init()
{
    data = cJSON_CreateObject();
    cJSON *reported = cJSON_CreateObject();
    cJSON *keyPair = cJSON_CreateObject();
    cJSON_AddNumberToObject(keyPair, "motor1", 0);
    cJSON_AddNumberToObject(keyPair, "motor2", 0);
    cJSON_AddNumberToObject(keyPair, "motor3", 0);
    cJSON_AddItemToObject(reported, "reported", keyPair);
    cJSON_AddItemToObject(data, "state", reported);
    printf("%s", cJSON_Print(data));
}

void parse_delta(char* msg)
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
            cJSON_SetNumberValue(cJSON_GetObjectItem(data_array, temp->string), temp->valuedouble);
        }
        else
        {
            temp->valuestring = temp->string;
            cJSON_AddItemToArray(data_array, temp);
        }
    }

}

void publish_connected() 
{
    printf("entered func\n");
    char *connected_topic = (char*)malloc((strlen(DEVICE_NAME) + 19) * sizeof(char));
    strcpy(connected_topic, "devices/");
    strcat(connected_topic, DEVICE_NAME);
    strcat(connected_topic, "/connected");
    printf("connected topic: %s\n", connected_topic);
    printf("publish connected message with result code: %d\n", esp_mqtt_client_publish(global_client, connected_topic, "1", (int)strlen("1"), 1, 1));
    //free(connected_topic);
}

void setup_subscriptions()
{
    char *update_topic = (char*)malloc((strlen(DEVICE_NAME) + 29) * sizeof(char));
    strcpy(update_topic, "devices/");
    strcat(update_topic, DEVICE_NAME);
    strcat(update_topic, "/shadow/update/delta");
    printf("subscription return code: %d\n", esp_mqtt_client_subscribe(global_client, update_topic, 1));
    //free(update_topic);
}

void report_state()
{
    char *report_topic = (char*)malloc((strlen(DEVICE_NAME) + 23) * sizeof(char));
    strcpy(report_topic, "devices/");
    strcat(report_topic, DEVICE_NAME);
    strcat(report_topic, "/shadow/update");
    if (esp_mqtt_client_publish(global_client, report_topic, cJSON_PrintUnformatted(data), (int)strlen(cJSON_PrintUnformatted(data)), 1, 1) == -1) {
        printf("state report failed\n");
    }
    //free(report_topic);
}

void client_start() 
{
    char *last_will_topic = (char*)malloc((strlen(DEVICE_NAME) + 19) * sizeof(char));
    strcpy(last_will_topic, "devices/");
    strcat(last_will_topic, DEVICE_NAME);
    strcat(last_will_topic, "/connected");

    char *pass_uri = (char*)malloc((strlen(BROKER_IP) + 8) * sizeof(char)); 
    strcpy(pass_uri, "mqtt://");
    strcat(pass_uri, BROKER_IP);

    const esp_mqtt_client_config_t mqtt_cfg = {
        .uri = pass_uri,
        .event_handle = mqtt_event_handler,
        .lwt_topic = last_will_topic,
        .lwt_msg = "0",
        .lwt_retain = 1,
        .port = PORT
    };
    
    global_client = esp_mqtt_client_init(&mqtt_cfg);
    ESP_ERROR_CHECK( esp_mqtt_client_start(global_client) );
}

void app_main(void)
{
    esp_err_t ret = nvs_flash_init();
    if (ret == ESP_ERR_NVS_NO_FREE_PAGES || ret == ESP_ERR_NVS_NEW_VERSION_FOUND) {
        ESP_ERROR_CHECK(nvs_flash_erase());
        ret = nvs_flash_init();
    }
    ESP_ERROR_CHECK( ret );

    wifi_connect();
    data_json_init();
}
