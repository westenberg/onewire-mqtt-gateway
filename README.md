# Onewire-MQTT-Gateway
This gateway allows you to read data from multiple 1-wire devices (e.g. a DS18B20 temperature sensor) and the data to a MQTT broker. It comes with Home Assistant Autodiscovery support and you can enable/disable devices with a MQTT command.

**Usage example:**
I use this gateway on a Raspberry Pi Zero with two temperature sensors to read the Delta T of my central heating. Home Assistant enables the devices when the central heating is turned on and switches the devices after the central heating is inactive for 30 min. The temperature data is sent to Home Assistant to the MQTT sensors that are automatically created with the Autodiscovery.

## Installation
```shell
sudo pip3 install -r requirements.txt
```

## Configuration
Copy config.example.yml to config.yml and change the settings

## Running
To test the gateway execute ```shell ./gateway.py```. Continuous background execution can be done using the example Systemd service onewire-mqtt-gateway.service

Configure the service, edit the user and set the right path to the working directory and gateway.py:

```shell
sudo cp onewire-mqtt-gateway.service /etc/systemd/system/
sudo nano /etc/systemd/system/onewire-mqtt-gateway.service
```

Next start and enable the service:

```shell
sudo systemctl daemon-reload
sudo systemctl start onewire-mqtt-gateway
sudo systemctl status onewire-mqtt-gateway
sudo systemctl enable onewire-mqtt-gateway
```

## MQTT

Note: the device_key is a snakecase string generated from the device name in the config. E.g. 'My Temperature Sensor' becomes 'my_temperature_sensor'

**Presence topic**
Presence changes (offline/online) will be published to the topic '<pub_topic>/<device_key>/presence'.

**State topic**
The state of a device is published to the topic '<pub_topic>/<device_key>/state' and is only published when a value is different than the previous one.

**Autodiscovery**
The gateway will publish a retained message for each device when 'enable_autodiscovery: true' is set in the config. You should see the sensors in Home Assistant immediately after starting the gateway. For more information: https://www.home-assistant.io/docs/mqtt/discovery/

**Enable/disable devices**
You can enable or disable one ore multiple devices with a MQTT command. A disabled device will no longer publish messages and the state will be empty.

For example, to disable multiple devices:
```
topic: onewire/disable
retain: false
payload: ["device_key", "device_key"]
```

Enable one device:
```
topic: onewire/enable
retain: false
payload: ["device_key"]
```

In Home Assistant you should escape the double qotes with a backslash, e.g.: "payload": "[\"device_key\"]"