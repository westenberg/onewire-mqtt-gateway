#!/usr/bin/python3
import glob
import json
import logging
import paho.mqtt.client as mqttClient
import paho.mqtt.publish as mqttPublish
import stringcase
import time
import yaml

cache = {}
connected = False
disabled = []


with open('config.yml', 'r', encoding='utf-8') as ymlfile:
    cfg = yaml.load(ymlfile)


def on_connect(client, userdata, flags, rc):
    global connected

    if rc == 0:
        print('Connected to broker')
        connected = True
        subscribe()
        hass_autoconf()
        setInitialPresence()
    else:
        connected = False
        logging.warning('Connection failed')


def on_disconnect(client, userdata,rc=0):
    logging.debug("DisConnected result code "+str(rc))
    client.loop_stop()


def on_message(client, userdata, msg):
    global disabled
    global cache

    message = json.loads(msg.payload.decode('utf-8'))
    print('Received message: ' + msg.topic + ' ' + str(message))
    messages = []

    if (type(message) is list):
        for device in message:
            if msg.topic == cfg['pub_topic'] + '/enable' and device in disabled:
                disabled.remove(device)
                messages.append({'topic': cfg['pub_topic'] + '/' + device + '/presence', 'payload': 'online', 'retain': True})
            elif msg.topic == cfg['pub_topic'] + '/disable' and device not in disabled:
                disabled.append(device)
                cache.pop(device)
                messages.append({'topic': cfg['pub_topic'] + '/' + device + '/presence', 'payload': 'offline', 'retain': True})
                messages.append({'topic': cfg['pub_topic'] + '/' + device + '/state', 'payload': '', 'retain': True})

    print('Currently disabled devices: ' + str(disabled))
    sendMessages(messages)
    update()


def read_temp(deviceid):
    device_file = cfg['base_dir'] + deviceid + '/w1_slave'
    valid = False
    temp = 0
    with open(device_file, 'r') as f:
        for line in f:
            if line.strip()[-3:] == 'YES':
                valid = True
            temp_pos = line.find(' t=')
            if temp_pos != -1:
                temp = round(float(line[temp_pos + 3:]) / 1000.0, 1)

    if valid:
        return str(temp)
    else:
        return None


getDeviceKey = lambda name: stringcase.snakecase(name.lower())


def subscribe():
    global client
    print('Subscribing on enable/disable topics')
    client.subscribe(cfg['pub_topic'] + '/disable')
    client.subscribe(cfg['pub_topic'] + '/enable')


def sendMessages(messages):
    global client

    if len(messages) > 0:
        print('Sending messages: ' + str(messages))

        for message in messages:
            client.publish(message['topic'], payload=message['payload'], qos=0, retain=message['retain'])


def setInitialPresence():
    messages = []

    for device in cfg['devices']:
        messages.append({'topic': cfg['pub_topic'] + '/' + getDeviceKey(device['name']) + '/presence', 'payload': 'online'})

    sendMessages(messages)


def getUpdateInterval():
    global connected
    if connected:
        return cfg['update_interval']

    return 5


def hass_autoconf():
    if cfg['enable_autodiscovery'] == True:
        print('Publishing Hass Autodiscovery')
        messages = []

        for device in cfg['devices']:
            devicekey = getDeviceKey(device['name'])

            payload = {
                'platform': 'mqtt',
                'name': device['name'],
                'availability_topic':  cfg['pub_topic'] + '/' + devicekey + '/presence',
                'state_topic':  cfg['pub_topic'] + '/' + devicekey + '/state',
                'icon': device['icon'],
                'device_class': device['device_class'],
                'unit_of_measurement': device['unit_of_measurement']
            }
            topic = cfg['autodiscovery_prefix'] + '/sensor/' + devicekey + '/config'
            messages.append({'topic': topic, 'payload': json.dumps(payload), 'retain': True})
        sendMessages(messages)


def update():
    global cache

    messages = []
    for device in cfg['devices']:
        devicekey = getDeviceKey(device['name'])

        if devicekey not in disabled:
            temp = read_temp(device['id'])
            print('receiving ' + devicekey + ': ' + temp)

            if temp is not None and ((devicekey in cache and temp != cache[devicekey]) or (devicekey in cache) == False):
                print('publishing ' + (devicekey + ': ' + temp))
                messages.append({'topic': cfg['pub_topic'] + '/' + devicekey + '/state', 'payload': temp, 'retain': False})

            cache[devicekey] = temp

    sendMessages(messages)


print('Started onewire-mqtt-gateway')

client = mqttClient.Client(client_id=cfg['clientname'], clean_session=False)

if cfg['username'] and  cfg['password']:
    client.username_pw_set(cfg['username'], cfg['password'])

client.on_connect = on_connect
client.on_disconnect = on_disconnect
client.on_message = on_message
client.connect(cfg['broker'], cfg['port'])
client.loop_start()

try:
    while True:
        if connected:
            update()
        else:
            print('Waiting for connection')
        time.sleep(getUpdateInterval())
except KeyboardInterrupt:
    print('exiting onewire-mqtt-gateway...')
    client.disconnect()
