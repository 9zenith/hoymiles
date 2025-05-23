__author__ = 'dmslabs'
__version__ = '0.23'

from os.path import realpath
from pyexpat import version_info
import requests
from requests.models import HTTPBasicAuth, Response, StreamConsumedError
from requests import Request, Session
import hashlib 
from string import Template
import json
import configparser
import logging
import dmslibs as dl
import comum
from dmslibs import Color, IN_HASSIO, mostraErro, log, pega_url, pega_url2, printC
from datetime import datetime, timezone
import paho.mqtt.client as mqtt
from paho.mqtt import client
import uuid
import time
import os
import sys
import ssl

from flask import Flask
from flask import render_template
import webserver
import multiprocessing

from multiprocessing import Process, Pipe

# CONFIG Secrets
HOYMILES_USER = "user"
HOYMILES_PASSWORD = "pass"
HOYMILES_PLANT_ID = 00000
MQTT_HOST = "mqtt.eclipse.org" 
MQTT_USERNAME  = "MQTT_USERNAME"
MQTT_PASSWORD  = "MQTT_PASSWORD"
MQTT_PORT = 1883
INTERVALO_MQTT = 240   #   How often to send data to the MQTT server?
INTERVALO_HASS = 1200   # How often to send device information in a format compatible with Home Asssistant MQTT discovery?
INTERVALO_GETDATA = 480 # How often do I read site data
SECRETS = 'secrets.ini'
WEB_SERVER = False
Use_kW_instead_W = True
External_MQTT_Server = False
External_MQTT_Host = "nda"
External_MQTT_User = "nda"
External_MQTT_Pass = "nda"
External_MQTT_TLS = False
External_MQTT_TLS_PORT = 8883

# HASS
HASS_TIMEZONE = "America/Sao_Paulo"
LOCAL_TIMEZONE = datetime.now(timezone.utc).astimezone().tzinfo   #  I guess it is the same of Hass Server

# Contants
VERSAO = __version__
DEVELOPERS_MODE = True
MANUFACTURER = 'dmslabs'
APP_NAME = 'Hoymiles Gateway'
SHORT_NAME = 'solarH'
SOLAR_MODEL = "DTU-W100" # mudar para pegar
TOKEN = ''
COOKIE_UID = "'uid=fff9c382-389f-4a47-8dc9-c5486fc3d9f5"
COOKIE_EGG_SESS = "EGG_SESS=XHfAhiHWwU__OUVeKh0IiITBnmwA-IIXEzTCHgHgww6ZYYddOPntPSwVz4Gx7ISbfU0WrvzOLungThcL-9D2KxavrtyPk8Mr2YXLFzJwvM0usPvhzYdt2Y2S9Akt5sjP"
URL1 = "https://global.hoymiles.com/platform/api/gateway/iam/auth_login"
URL2 = "https://global.hoymiles.com/platform/api/gateway/pvm-data/data_count_station_real_data"
URL3 = 'https://global.hoymiles.com/platform/api/gateway/iam/user_me'
URL4 = 'https://global.hoymiles.com/platform/api/gateway/pvm/statistics_count_station_state'
URL5 = 'https://global.hoymiles.com/platform/api/gateway/pvm/station_select_by_page'
URL6 = 'https://global.hoymiles.com/platform/api/gateway/pvm/station_find'
UUID = str(uuid.uuid1())
MQTT_PUB = "home/solar"
SID = 'solar'
MQTT_HASS = "homeassistant"
DEFAULT_MQTT_PASS = "MQTT_PASSWORD"
INTERVALO_EXPIRE = int(INTERVALO_GETDATA) * 1.5
NODE_ID = 'dmslabs'

# mqqt SSL
MQTTversion = mqtt.MQTTv31
TLS_protocol_version = ssl.PROTOCOL_TLSv1_2

paho_erro_codes = {0: "Connection successful",
    1: "Connection refused – incorrect protocol version",
    2: "Connection refused – invalid client identifier",
    3: "Connection refused – server unavailable",
    4: "Connection refused – bad username or password",
    5: "Connection refused – not authorised",
    100: "Connection refused - other things"
}


PAYLOAD_T1= '''
   {
       "ERROR_BACK":true,
       "LOAD":{
           "loading":true
        },
        "body":{
            "password":"$password",
            "user_name":"$user"
        },
        "WAITING_PROMISE":true
    }
'''

PAYLOAD_T2 = '''
{
    "body": {
        "sid": $sid
    },
    "WAITING_PROMISE": true
}
'''

headers_h1 = {
  'Content-Type': 'application/json',
  'Cookie': '' # 'uid=fff9c382-389f-4a47-8dc9-c5486fc3d9f5; EGG_SESS=XHfAhiHWwU__OUVeKh0IiITBnmwA-IIXEzTCHgHgww6ZYYddOPntPSwVz4Gx7ISbfU0WrvzOLungThcL-9D2KxavrtyPk8Mr2YXLFzJwvM0usPvhzYdt2Y2S9Akt5sjP'
}

headers_h2 = {
  'Content-Type': 'application/json;charset=UTF-8',
  'Cache-Control': 'no-cache',
  'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:60.0) Gecko/20100101 Firefox/60.0',
  'Host': 'global.hoymiles.com',
  'Connection': 'keep-alive',
  'Accept': 'application/json, text/plain, */*',
  'Accept-Encoding': 'gzip, deflate, br',
  'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 11_2_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/89.0.4389.90 Safari/537.36',
  'Accept-Language': 'pt-BR,pt;q=0.9,it-IT;q=0.8,it;q=0.7,es-ES;q=0.6,es;q=0.5,en-US;q=0.4,en;q=0.3',
  'Cookie': 'hm_token_language=en_us; ' # 'uid=fff9c382-389f-4a47-8dc9-c5486fc3d9f5; EGG_SESS=XHfAhiHWwU__OUVeKh0IiITBnmwA-IIXEzTCHgHgww6ZYYddOPntPSwVz4Gx7ISbfU0WrvzOLungThcL-9D2KxavrtyPk8Mr2YXLFzJwvM0usPvhzYdt2Y2S9Akt5sjP'
}

json_hass = {"sensor": '''
{ 
  "stat_t": "home/$sid/json_$plant_id",
  "name": "$name",
  "uniq_id": "$uniq_id",
  "val_tpl": "{{ value_json.$val_tpl }}",
  "icon": "$icon",
  "device_class": "$device_class",
  "state_class": "$state_class",
  "unit_of_measurement": "$unit_of_measurement",
  "expire_after": "$expire_after",
  "last_reset_topic": "$last_reset_topic",
  "last_reset_value_template": "{{ value_json.reset_$val_tpl }}",
  "device": { $device_dict }
}'''}

device_dict = ''' "name": "$device_name",
    "manufacturer": "$manufacturer",
    "model": "$model",
    "sw_version": "$sw_version",
    "via_device": "$via_device",
    "identifiers": [ "$identifiers" ] '''


# # GLOBAL VARS
version_expected = {"dmslibs":1}
token = ""
status = {"ip":"?",
          "mqtt": False}

gDevices_enviados = { 'b': False, 't':datetime.now() }  # Global - Controla quando enviar novamente o cabeçalho para autodiscovery
gMqttEnviado = { 'b': False, 't':datetime.now() }  # Global - Controla quando publicar novamente

statusLast = status.copy()
gDadosSolar = dict()
gConnected = False #global variable for the state of the connection

gEnvios = {'last_time': datetime.today().strftime('%Y-%m-%d %H:%M:%S'),
          'load_cnt': 0,
          'load_time': datetime.today().strftime('%Y-%m-%d %H:%M:%S')}   # conta envios e ultimo envio.  Ajuda ver se travou.

sensor_dic = dict() # {}

gLastReset = {'dtMes': "1970-01-01T00:00:00+00:00",
              'valMes': 0,
              'dtDia': "1970-01-01T00:00:00+00:00",
              'valDia':0,
              }


def pega_url_jsonDic(url, payload, headers, qualPega):
    # recebe o dic da url
    if qualPega == 1 :
        resposta, sCode = pega_url(url, payload, headers, DEVELOPERS_MODE)
    else:
        resposta, sCode = pega_url2(url, payload, headers, DEVELOPERS_MODE)
    ret = dict()
    if sCode == 200:
        json_res = json.loads(resposta)
        ret = json_res
    return ret

def pega_token():
   # pega o token
   global token
   global TOKEN
   global HOYMILES_PASSWORD
   global HOYMILES_USER

   pass_hash = hashlib.md5(HOYMILES_PASSWORD.encode()) # b'senhadohoymiles' 
   pass_hex = pass_hash.hexdigest()
   # print(pass_hex) 
   ret = False
   T1 = Template(PAYLOAD_T1)
   payload_T1 = T1.substitute(user = HOYMILES_USER, password = pass_hex)
   #print(payload_T1)
   header = headers_h1
   header['Cookie'] = "'" + COOKIE_UID + "; " + COOKIE_EGG_SESS + "'"
   login, sCode = pega_url(URL1, payload_T1, header)
   if sCode == 200:
        json_res = json.loads(login)
        if json_res['status'] == '0':
            data_body = json_res['data']
            token = json_res['data']['token']
            TOKEN = token
            ret = True
            printC(Color.F_Blue, 'I got the token!!  :-)')
            if token == "":
                print ('erro na resposta')
                ret = False
        elif json_res['status'] == '1':
            TOKEN = ''
            token = ''
            print (Color.F_Red + "Wrong user/password" + Color.F_Default)
   else:
        TOKEN = ''
        token = ''
        print (Color.F_Red + "HTTP Error: " + str(sCode) + Color.F_Default + " " + dl.httpStatusCode(sCode))
   return ret

def pega_solar(uid):
    # pega dados da usina
    ret = False
    T2 = Template(PAYLOAD_T2)
    payload_t2 = T2.substitute(sid = uid)
    header = headers_h2
    # header['Cookie'] = COOKIE_UID + "; " + COOKIE_EGG_SESS + "; hm_token=" + token + "; Path=/; Domain=.global.hoymiles.com; Expires=Sat, 19 Mar 2022 22:11:48 GMT;" + "'"
    header['Cookie'] = COOKIE_UID + "; hm_token=" + token + "; Path=/; Domain=.global.hoymiles.com; Expires=Sat, 30 Mar 2024 22:11:48 GMT;" + "'"
    solar = pega_url_jsonDic(URL2, payload_t2, header, 2)
    if 'status' in solar.keys():
        solar_status = solar['status']
        if solar_status == "0":
            ret = solar.copy()
        if solar_status != "0":
            ret = solar_status
            if DEVELOPERS_MODE:
                printC(Color.B_Red, 'Solar Status Error: ' + str(solar_status) )
        if solar_status == "100":
            # erro no token
            # pede um novo  
            if (pega_token()):
                # chama pega solar novamente
                ret = pega_solar(uid)
    else:
        print(Color.B_Red + "I can't connect!"  + Color.B_Default)
    return ret

def get_secrets():
    ''' GET configuration data '''
    global HOYMILES_USER
    global HOYMILES_PASSWORD
    global HOYMILES_PLANT_ID
    global MQTT_HOST
    global MQTT_PASSWORD
    global MQTT_USERNAME
    global MQTT_PORT
    global DEVELOPERS_MODE
    global WEB_SERVER
    global Use_kW_instead_W
    global External_MQTT_Server
    global External_MQTT_Host
    global External_MQTT_User
    global External_MQTT_Pass
    global External_MQTT_TLS
    global External_MQTT_TLS_PORT

    config = dl.getConfigParser(SECRETS)

    printC (Color.F_LightGreen, "Reading secrets.ini")

    # le os dados
    HOYMILES_USER  = dl.get_config(config, 'secrets', 'HOYMILES_USER', HOYMILES_USER)
    HOYMILES_PASSWORD = dl.get_config(config, 'secrets', 'HOYMILES_PASSWORD', HOYMILES_PASSWORD)
    HOYMILES_PLANT_ID = dl.get_config(config, 'secrets','HOYMILES_PLANT_ID', HOYMILES_PLANT_ID, getInt=True)
    MQTT_PASSWORD = dl.get_config(config, 'secrets', 'MQTT_PASS', MQTT_PASSWORD)
    MQTT_USERNAME  = dl.get_config(config, 'secrets', 'MQTT_USER', MQTT_USERNAME)
    MQTT_HOST = dl.get_config(config, 'secrets', 'MQTT_HOST', MQTT_HOST)
    dev_mode = dl.get_config(config, 'developers', 'DEVELOPERS_MODE', "")
    if bool(dev_mode) == True:
        DEVELOPERS_MODE = True
    else:
        DEVELOPERS_MODE = False
    WEB_SERVER = dl.get_config(config, 'secrets', 'WEB_SERVER', WEB_SERVER)
    # external server
    External_MQTT_Server = dl.get_config(config, 'external', 'External_MQTT_Server', External_MQTT_Server, getBool=True)
    if (External_MQTT_Server):
        External_MQTT_Host = dl.get_config(config, 'external', 'External_MQTT_Host', External_MQTT_Host)
        External_MQTT_User = dl.get_config(config, 'external', 'External_MQTT_User', External_MQTT_User)
        External_MQTT_Pass = dl.get_config(config, 'external', 'External_MQTT_Pass', External_MQTT_Pass)
        External_MQTT_TLS = dl.get_config(config, 'external', 'External_MQTT_TLS', External_MQTT_TLS, getBool=True)
        External_MQTT_TLS_PORT = dl.get_config(config, 'external', 'External_MQTT_TLS_PORT', External_MQTT_TLS_PORT, getInt=True)
    if (External_MQTT_Server):
        MQTT_HOST = External_MQTT_Host
        MQTT_PASSWORD = External_MQTT_Pass
        MQTT_USERNAME = External_MQTT_User
        printC(Color.B_Green, "Using External MQTT Server: " + str(MQTT_HOST))
        if (External_MQTT_TLS):
            MQTT_PORT = External_MQTT_TLS_PORT
            printC(Color.B_Green, "Using External MQTT TLS PORT: " + str(MQTT_PORT))
    else:
        External_MQTT_TLS = False



def substitui_secrets():
    "No HASS.IO ADD-ON substitui os dados do secrets.ini pelos do options.json"
    global HOYMILES_USER
    global HOYMILES_PASSWORD
    global HOYMILES_PLANT_ID
    global MQTT_HOST
    global MQTT_PASSWORD
    global MQTT_USERNAME
    global MQTT_PORT
    global DEVELOPERS_MODE
    global FILE_COMM
    global WEB_SERVER
    global Use_kW_instead_W
    global External_MQTT_Server
    global External_MQTT_Host
    global External_MQTT_User
    global External_MQTT_Pass
    global External_MQTT_TLS
    global External_MQTT_TLS_PORT
    global HASS_TIMEZONE

    log().debug ("Loading env data....")
    HOYMILES_USER = dl.pegaEnv("HOYMILES_USER")
    HOYMILES_PASSWORD = dl.pegaEnv("HOYMILES_PASSWORD")
    HOYMILES_PLANT_ID = dl.pegaEnv("HOYMILES_PLANT_ID")
    MQTT_HOST = dl.pegaEnv("MQTT_HOST")
    MQTT_PASSWORD = dl.pegaEnv("MQTT_PASSWORD")
    MQTT_USERNAME = dl.pegaEnv("MQTT_USER")
    DEVELOPERS_MODE = dl.pegaEnv("DEVELOPERS_MODE")
    DEVELOPERS_MODE = dl.onOff(DEVELOPERS_MODE, True, False)
    if dl.IN_HASSIO():
        WEB_SERVER = True
        FILE_COMM = '/data/' + comum.FILE_COMM
    #Use_kW_instead_W = dl.pegaEnv("Use_kW_instead_W")
    External_MQTT_Server = dl.pegaEnv("External_MQTT_Server")
    External_MQTT_Server = dl.onOff(External_MQTT_Server, True, False)

    External_MQTT_Host = dl.pegaEnv("External_MQTT_Host")
    External_MQTT_User = dl.pegaEnv("External_MQTT_User")
    External_MQTT_Pass = dl.pegaEnv("External_MQTT_Pass")

    #v0.22
    External_MQTT_TLS = dl.pegaEnv("External_MQTT_TLS")
    External_MQTT_TLS = dl.onOff(External_MQTT_TLS, True, False)
    External_MQTT_TLS_PORT = dl.pegaEnv("External_MQTT_TLS_PORT")
    printC(Color.B_Red, "MQTT Server: " + str(MQTT_HOST))
    printC(Color.B_Green, "Using External MQTT Server: " + str(External_MQTT_Server == True))

    HASS_TIMEZONE = dl.pegaEnv("HASS_TIMEZONE")

    if (External_MQTT_Server):
        MQTT_HOST = External_MQTT_Host
        MQTT_PASSWORD = External_MQTT_Pass
        MQTT_USERNAME = External_MQTT_User
        printC(Color.B_Green, "Using External MQTT Server: " + str(MQTT_HOST))
        if (External_MQTT_TLS):
            MQTT_PORT = External_MQTT_TLS_PORT
            printC(Color.B_Green, "Using External MQTT TLS PORT: " + str(MQTT_PORT))

    #printC(Color.B_Red, "mqtt_extenal: " + str(External_MQTT_Host))
    #printC(Color.B_Red, "Use_kW_instead_W: " + str(Use_kW_instead_W))
    #printC(Color.B_Red, "External_MQTT: " + str(External_MQTT_User))

    log().debug ("Env data loaded.")


def mqttStart():
    ''' Start MQTT '''
    global client
    global clientOk
    # MQTT Start
    # client = mqtt.Client(transport="tcp") # "websockets"
    client = mqtt.Client(client_id = '', clean_session = True, userdata = None, protocol = MQTTversion, transport="tcp" ) # mqtt.MQTTv31

    log().info("Starting MQTT " + MQTT_HOST)
    printC(Color.B_Blue, "Starting MQTT Client " + MQTT_HOST)
    if DEVELOPERS_MODE:
        printC(Color.F_Blue, "SSL: " + ssl.OPENSSL_VERSION)
        log().debug("mqttStart External: " + str(External_MQTT_Server) + ' ' + str(type(External_MQTT_Server)))
        log().debug("mqttStart TLS: " + str(External_MQTT_TLS) + ' ' + str(type(External_MQTT_TLS)) )
        log().debug("mqttStart MQTT_USERNAME: " + str(MQTT_USERNAME) + ' ' + str(type(MQTT_USERNAME) ))
        log().debug("mqttStart MQTT_PASSWORD: " + str(MQTT_PASSWORD) + ' ' + str(type(MQTT_PASSWORD) ))
        log().debug("mqttStart MQTT_PORT: " + str(MQTT_PORT) + ' ' + str(type(MQTT_PORT) ))
    client.username_pw_set(username=MQTT_USERNAME, password=MQTT_PASSWORD)
    client.on_connect = on_connect
    # client.on_message = on_message
    client.on_disconnect = on_disconnect
    client.on_publish = on_publish
    if DEVELOPERS_MODE:
        client.on_log = on_log

    #v.0.22 TLS
    if (External_MQTT_TLS):
        log().debug("Trying TLS: " + str(MQTT_PORT))
        printC( Color.F_Green, "Trying TLS: " + str(MQTT_PORT) + " " + str(type(MQTT_PORT) ))
        # ssl._create_default_https_context = ssl._create_unverified_context

        if DEVELOPERS_MODE:
            printC( Color.F_Magenta, "TLS_protocol_version: " + str( TLS_protocol_version ) )
        
        context = ssl.SSLContext(protocol = TLS_protocol_version) # ssl.PROTOCOL_TLSv1  ,  ssl.PROTOCOL_TLS_CLIENT
        
        #context.check_hostname = False
        client.tls_set_context(context)
        #ssl._create_default_https_context = ssl._create_unverified_context
        #ssl.create_default_context()
        #client.tls_set()
        #client.tls_set_context(ssl._create_unverified_context)
        #client.tls_insecure_set(True)
        #import certifi
        #client.tls_set(certifi.where())
    try:
        clientOk = True
        #rc = client.connect(MQTT_HOST, MQTT_PORT, 60) # 1883
        rc = client.connect(host = MQTT_HOST,
            port = int(MQTT_PORT),
            keepalive = 60)  # 1883

    except Exception as e:  # OSError
        if e.__class__.__name__ == 'OSError':
            clientOk = False
            log().warning("Can't start MQTT")
            print (Color.F_Red + "Can't start MQTT" + Color.F_Default)  # e.errno = 51 -  'Network is unreachable'
            mostraErro(e,20, "MQTT Start")
        else:
            clientOk = False
            mostraErro(e,30, "MQTT Start")
    if clientOk:  client.loop_start()  # start the loop


# The callback for when the client receives a CONNACK response from the server.
def on_connect(client, userdata, flags, rc):
    global gConnected
    global status
    if rc == 0:
        cor = Color.F_Blue 
    else:
        cor = Color.F_Red
    print(cor + "MQTT connected with result code " + str(rc) + Color.F_Default)
    log().debug("MQTT connected with result code " + str(rc))
    if rc == 0:
        print ("Connected to " + MQTT_HOST)
        gConnected = True
        status['mqtt'] = "on"
        client.connected_flag = True
        # Mostra clientes
        status['publish_time'] = dl.strDateTimeZone('now').isoformat() 
        send_clients_status()
    else:
        gConnected = False
        status['mqtt'] = "off"
        if rc>5: rc=100
        #print (str(rc) + str(tp_c[rc]))
        print (str(rc) + dl.MQTT_STATUS_CODE[rc])
        log().error(str(rc) + str(dl.MQTT_STATUS_CODE[rc]))
        # tratar quando for 3 e outros
        if rc == 4 or rc == 5:
            # senha errada
            print(Color.F_Magenta + "APP EXIT" + str(rc) + Color.F_Default)
            time.sleep(60000)
            #raise SystemExit(0)
            #sys.exit()
            #quit()

def on_log(client, userdata, level, buf):
  print("log: ",buf)#connect

def on_publish(client, userdata, mid):
    # fazer o que aqui? 
    # fazer uma pilha para ver se foi publicado ou não
    # aparentemente só vem aqui, se foi publicado.
    if 1==2:
        print("Published mid: " + str(mid), "last: " + str(gLastMidMqtt))
        if gLastMidMqtt-1 != mid:
            print ("Erro mid:" + str(mid) + " não publicado.")

def on_disconnect(client, userdata, rc):
    global gConnected
    global gDevices_enviados
    global status
    gConnected = False
    print("disconnecting reason  "  + str(rc))
    if rc>5: rc=100
    print("disconnecting reason  "  + str(client) +  str(dl.MQTT_STATUS_CODE[rc]))
    client.connected_flag = False
    client.disconnect_flag = True
    gDevices_enviados['b'] = False # Force sending again
    status['mqtt'] = "off"
    # mostra cliente desconectado
    try:
        send_clients_status()
    except Exception as e:
        mostraErro(e, 30, "on_disconnect")

def send_clients_status():
    ''' send connected clients status '''
    global status
    dadosEnviar = status.copy()
    mqtt_topic = MQTT_PUB + "/clients/" + status['ip']
    dadosEnviar.pop('ip')
    dadosEnviar['UUID'] = UUID
    dadosEnviar['version'] = VERSAO
    dadosEnviar['plant_id'] = HOYMILES_PLANT_ID
    dadosEnviar['inHass'] = dl.IN_HASSIO()
    gEnvios['last_time'] = dl.strDateTimeZone('now').isoformat()  #datetime.today().strftime('%Y-%m-%d %H:%M:%S')
    dadosEnviar['last_time'] = gEnvios['last_time']  
    dadosEnviar['load_cnt'] = gEnvios['load_cnt']
    dadosEnviar['load_time'] = gEnvios['load_time']
    jsonStatus = json.dumps(dadosEnviar)
    (rc, mid) = publicaMqtt(mqtt_topic, jsonStatus)
    return rc

def publicaMqtt(topic, payload):
    "Publica no MQTT atual"
    global gLastMidMqtt
    (rc, mid) = client.publish(topic, payload)
    # if DEVELOPERS_MODE:
        # print (Color.F_Cyan, topic, Color.F_Default)
        # print (Color.F_Blue, payload, Color.F_Default)
    gLastMidMqtt = mid
    if rc == mqtt.MQTT_ERR_NO_CONN:
        print ("mqtt.MQTT_ERR_NO_CONN")
    if rc == mqtt.MQTT_ERR_SUCCESS:
        # certo, sem erro.
        #print ("mqtt.MQTT_ERR_SUCCESS")
        gLastMidMqtt = mid
    if rc == mqtt.MQTT_ERR_QUEUE_SIZE:
        print ("mqtt.MQTT_ERR_QUEUE_SIZE")
    return rc, mid

def send_hass():
    ''' Envia parametros para incluir device no hass.io '''
    global sensor_dic
    global gDevices_enviados

    # var comuns
    varComuns = {'sw_version': VERSAO,
                 'model': SOLAR_MODEL,
                 'manufacturer': MANUFACTURER,
                 'device_name': APP_NAME,
                 'identifiers': SHORT_NAME + "_" + str(HOYMILES_PLANT_ID),
                 'via_device': SOLAR_MODEL,
                 'sid': SID,
                 'plant_id': HOYMILES_PLANT_ID,
                 'last_reset_topic': 'home/$sid/json_$plant_id',
                 'uniq_id': UUID } 
    
    if DEVELOPERS_MODE:
        log().debug('Sensor_dic: ' + str(len(sensor_dic)))
    if len(sensor_dic) == 0:
        for k in json_hass.items():
            json_file_path = k[0] + '.json'
            if dl.IN_HASSIO():
                json_file_path = '/' + json_file_path  # to run on HASS.IO
            if not os.path.isfile(json_file_path):
                log().error(json_file_path + " not found!")
            printC(Color.F_Cyan, json_file_path)
            json_file = open(json_file_path)
            if not json_file.readable():
                printC(Color.B_Red,"I can't read file")
            json_str = json_file.read()
            sensor_dic[k[0]] = json.loads(json_str)

    if len(sensor_dic) == 0:
        printC(Color.B_Red, "Sensor_dic error")
    rc = 0
    for k in sensor_dic.items():
        # print('Componente:' + k[0])
        rc = monta_publica_topico(k[0], sensor_dic[k[0]], varComuns)
        if not rc == 0:
            printC(Color.B_LightRed, 'Hass publish error: ' + str(rc) )

    if rc == 0:
        gDevices_enviados['b'] = True
        gDevices_enviados['t'] = datetime.now()
        log().debug('Hass Sended')


def publicaDadosWeb(gDadosSolar, plant_id):
    # publica dados na web por meio do webserver via JSON
    jsonx = publicaDados(gDadosSolar, plant_id)
    # add new data
    json_load = json.loads(jsonx)
    json_load['last_time'] = gEnvios['last_time']  
    json_load['load_cnt'] = gEnvios['load_cnt']
    json_load['load_time'] = gEnvios['load_time']
    json_x = json.dumps(json_load)
    return json_x


def publicaDados(solarData, plant_id):
    # publica dados no MQTT  - MQTT_PUB/json
    global status
    global gMqttEnviado
    jsonUPS = json.dumps(solarData)
    (rc, mid) = publicaMqtt(MQTT_PUB + "/json" + '_' + str(plant_id), jsonUPS)
    gMqttEnviado['b'] = True
    gMqttEnviado['t'] = datetime.now()
    print (Color.F_Blue + "Dados Solares Publicados..." + Color.F_Default + str(datetime.now()))
    if status['mqtt'] == 'on': 
        status[APP_NAME] = "on"
    else:
        status[APP_NAME] = "off"
    send_clients_status()
    return jsonUPS

def monta_publica_topico(component, sDict, varComuns):
    ''' monta e envia topico - sensores'''
    ret_rc = 0
    key_todos = sDict['todos']
    newDict = sDict.copy()
    newDict.pop('todos')
    for key,dic in newDict.items():
        # print(key,dic)
        if key[:1] != '#':
            varComuns['uniq_id']=varComuns['identifiers'] + "_" + key
            if not('val_tpl' in dic):
                dic['val_tpl'] = dic['name']
            dic['name'] = varComuns['uniq_id']
            dic['device_dict'] = device_dict
            dic['publish_time'] = datetime.today().strftime('%Y-%m-%d %H:%M:%S')
            dic['expire_after'] = int(INTERVALO_EXPIRE) # quando deve expirar
            dados = Template(json_hass[component]) # sensor
            dados = Template(dados.safe_substitute(dic))
            varComuns_template = Template( json.dumps(varComuns) )
            varComuns_template = varComuns_template.safe_substitute(varComuns) 
            #dados = Template(dados.safe_substitute(varComuns)) # faz ultimas substituições
            dados = Template(dados.safe_substitute(json.loads( varComuns_template)) ) # faz ultimas substituições
            dados = dados.safe_substitute(key_todos) # remove os não substituidos.
            topico = MQTT_HASS + "/" + component + "/" + NODE_ID + "/" + varComuns['uniq_id'] + "/config"
            # print(topico)
            # print(dados)
            dados = dl.json_remove_vazio(dados)
            (rc, mid) = publicaMqtt(topico, dados)
            if rc == 0:
                if DEVELOPERS_MODE:
                    topicoResumo = topico.replace(MQTT_HASS + "/" + component + "/" + NODE_ID, '...')
                    topicoResumo = topicoResumo.replace("/config", '')
                    printC (Color.F_Cyan, topicoResumo)
                    printC (Color.F_Red, dados)
            else:
                # deu erro na publicação
                printC (Color.B_Red, "Erro monta_publica_topico")
                printC (Color.F_Red, topico)
            ret_rc = ret_rc + rc
            # print ("rc: ", rc)
    return rc

def ajustaDadosSolar():
    ''' ajusta dados solar '''
    global gDadosSolar
    global gLastReset
    realPower = dl.float2number(gDadosSolar['real_power'],0)
    capacidade = dl.float2number(gDadosSolar['capacitor'])
    plant_tree = dl.float2number(gDadosSolar['plant_tree'], 0)
    today_eqW = dl.float2number(gDadosSolar['today_eq'])
    today_eq = dl.float2number(gDadosSolar['today_eq']) / 1000
    today_eq = round(today_eq, 2)
    month_eq = dl.float2number(gDadosSolar['month_eq']) / 1000
    month_eq = round(month_eq, 2)
    total_eq = dl.float2number(gDadosSolar['total_eq']) / 1000
    total_eq = round(total_eq, 2)
    co2 = dl.float2number(gDadosSolar['co2_emission_reduction']) / 1000000
    co2 = round(co2,2)
    last_data_time = gDadosSolar['last_data_time']
    # corrige escala e digitos
    if capacidade > 0 and capacidade < 100:
        capacidade = capacidade * 1000
        capacidade = round(capacidade)
    power = (realPower / capacidade) * 100
    power = round(power,1)
    if realPower == 0: 
        printC (Color.F_Magenta, "realPower = 0")
        printC (Color.B_LightMagenta, dl.hoje() )
        if DEVELOPERS_MODE:
            #printC ('parada 1/0', str(1/0))
            printC(Color.B_Red,'parada')
    gDadosSolar['real_power'] = str( realPower )
    gDadosSolar['real_power_measurement'] = str( realPower )
    gDadosSolar['real_power_total_increasing'] = str( realPower )
    gDadosSolar['power_ratio'] = str( power )
    gDadosSolar['capacitor'] =  str( capacidade )
    gDadosSolar['capacitor_kW'] =  str( capacidade / 1000) 
    gDadosSolar['co2_emission_reduction'] = str( co2 )
    gDadosSolar['plant_tree'] = str( plant_tree )
    gDadosSolar['today_eq'] = str( today_eq )
    gDadosSolar['today_eq_Wh'] = str( today_eqW )
    gDadosSolar['month_eq'] = str( month_eq )
    gDadosSolar['total_eq'] = str( total_eq )
    #last_data_time = datetime.strptime(last_data_time, '%Y-%m-%d %H:%M:%S')
    #last_data_time = last_data_time.replace(tzinfo=LOCAL_TIMEZONE)
    last_data_time = dl.strDateTimeZone(last_data_time)
    gDadosSolar['last_data_time'] = last_data_time.isoformat()
    print(last_data_time.isoformat())
    print(last_data_time.tzname())

    # dados solar reset
    gLastReset['valMes'] = month_eq
    #gLastReset['dtMes']=datetime.today().strftime('%Y-%m-01T00:00:00+00:00')
    dtMes = datetime.today().strftime('%Y-%m-%d %H:%M:%S')
    gLastReset['dtMes'] = dl.strDateTimeZone(dtMes).isoformat()
    gLastReset['valDia'] = month_eq
    #gLastReset['dtDia']=datetime.today().strftime('%Y-%m-%dT00:00:00+00:00')
    gLastReset['dtDia'] = gLastReset['dtMes']

    part1 = "reset_"
    # TODO: Need to check values source
    gDadosSolar[part1+"today_eq"] = gLastReset['dtDia']
    gDadosSolar[part1+"month_eq"] = gLastReset['dtMes']
    # v0.23.
    gDadosSolar[part1+"real_power_measurement"] = gLastReset['dtMes']
    gDadosSolar[part1+"real_power_total_increasing"] = gLastReset['dtMes']
    gDadosSolar[part1+"today_eq_Wh"] = gLastReset['dtMes']
    gDadosSolar[part1+"total_eq"] = gLastReset['dtMes']

def pegaDadosSolar():
    global gDadosSolar
    global gEnvios
    ''' pega dados solar '''
    dados_solar = pega_solar(HOYMILES_PLANT_ID)

    gEnvios['load_time'] = dl.strDateTimeZone('now').isoformat()  # datetime.today().strftime('%Y-%m-%d %H:%M:%S')
    gEnvios['load_cnt'] = gEnvios['load_cnt'] + 1

    if DEVELOPERS_MODE:
        print ("dados_solar: " + str(dados_solar))
    gDadosSolar = dados_solar['data']
    capacidade = dl.float2number(gDadosSolar['capacitor'])
    real_power = dl.float2number(gDadosSolar['real_power'])
    if real_power == 0:
        # é igual a 0
        printC(Color.B_Red, "REAL_POWER = 0")
        time.sleep(60) # espera 60 segundos
        printC(Color.F_Blue, "Getting data again")
        dados_solar = pega_solar(HOYMILES_PLANT_ID)
        gDadosSolar = dados_solar['data']
        capacidade = dl.float2number(gDadosSolar['capacitor'])
        real_power = dl.float2number(gDadosSolar['real_power'])
    if capacidade == 0:
        # é um erro
        print  (Color.B_Red + "Erro capacitor: " + str(capacidade) + Color.B_Default)
    else:
        ajustaDadosSolar()
    return gDadosSolar


# RODA O APP WEB
def iniciaWebServerB(Conf):
    ''' inicia o webserver '''
    webserver.app.run(debug=True, host="0.0.0.0", threaded=True)
    #app.run(debug=True, host="0.0.0.0", threaded=False)

def iniciaWebServer():
    ''' inicia o webserver '''
    printC (Color.B_LightMagenta, "WEB SERVER Starting ...")

    path_index = comum.PATH_TEMPLATE
    if IN_HASSIO():
        path_index = comum.PATH_TEMPLATE_HAS

    bl_existe_index = os.path.isfile(path_index + '/index.html')
    if not bl_existe_index:
        ''' não existe o index '''
        printC (Color.B_Red, "Index not found. I can't start webserver. ")
        arr = os.listdir(path_index)
        printC(Color.F_Magenta, path_index)
        print(arr)
    else:
        # existe index
        p = multiprocessing.Process(target=iniciaWebServerB, args=({"Something":"SomethingElese"},))
        p.start()


# INICIO, START

print (Color.B_Blue + "********** " + MANUFACTURER + " " + APP_NAME + " v." + VERSAO + Color.B_Default)
print (Color.B_Green + "Starting up... " + datetime.today().strftime('%Y-%m-%d %H:%M:%S') + '     ' + Color.B_Default)

# version check
if int(dl.version()) < int(version_expected['dmslibs']):
    printC (Color.B_Red, "Wrong dmslibs version! ")
    printC (Color.F_Blue, "Current: " + dl.version() )
    printC (Color.F_Blue, "Expected: " + version_expected['dmslibs'] )

dl.inicia_log(logFile='/var/tmp/hass.hoymiles.log', logName='hass.hoymiles', stdOut=True)



# info
dl.dadosOS()
status['ip'] = dl.get_ip()
print (Color.B_Cyan + "IP: " + Color.B_Default + Color.F_Magenta + status['ip'] + Color.F_Default)
if DEVELOPERS_MODE:
    print (Color.B_Red, "DEVELOPERS_MODE", Color.B_Default)

get_secrets()

if dl.IN_HASSIO():
    print (Color.B_Blue, "IN HASS.IO", Color.B_Default)
    if not DEVELOPERS_MODE or 1==1:  # teste
        substitui_secrets()
        if DEVELOPERS_MODE:
            print (Color.B_Red, "DEVELOPERS_MODE", Color.B_Default)
    if DEFAULT_MQTT_PASS == MQTT_PASSWORD:
        log().warning ("YOU SHOUD CHANGE DE DEFAULT MQTT PASSWORD!")
        print (Color.F_Red + "YOU SHOUD CHANGE DE DEFAULT MQTT PASSWORD!" + Color.F_Default)


if DEVELOPERS_MODE or MQTT_HOST == '192.168.50.20':
    print (Color.F_Green + "HOYMILES_USER: " + Color.F_Default + str(HOYMILES_USER))
    print (Color.F_Green + "HOYMILES_PASSWORD: " + Color.F_Default + str(HOYMILES_PASSWORD))
    print (Color.F_Green + "HOYMILES_PLANT_ID: " + Color.F_Default + str(HOYMILES_PLANT_ID))
    print (Color.F_Green + "MQTT_HOST: " + Color.F_Default + str(MQTT_HOST))
    print (Color.F_Green + "MQTT_PASSWORD: " + Color.F_Default + str(MQTT_PASSWORD))
    print (Color.F_Green + "MQTT_USERNAME: " + Color.F_Default + str(MQTT_USERNAME))
    print (Color.F_Blue + "INTERVALO_MQTT: " + Color.F_Default + str(INTERVALO_MQTT))
    print (Color.F_Blue + "INTERVALO_HASS: " + Color.F_Default + str(INTERVALO_HASS))
    print (Color.F_Blue + "INTERVALO_GETDATA: " + Color.F_Default + str(INTERVALO_GETDATA))
    print (Color.F_Blue + "WEB_SERVER: " + Color.F_Default + str(WEB_SERVER))

if dl.float2number(HOYMILES_PLANT_ID) < 100:        
    print (Color.F_Green + "HOYMILES_PLANT_ID: " + Color.F_Default + str(HOYMILES_PLANT_ID))
    print (Color.B_Magenta + "Wrong plant ID" + Color.B_Default )

cnt = 0
while token == '':
    pega_token()
    cnt = cnt + 1
    if token == '':
        print (Color.B_Red + "I can't get access token" + Color.B_Default)
        if cnt >= 5: 
            exit()
        time.sleep(60000)

if token != '':
    # pega dados solar
    #dados_solar = pega_solar(HOYMILES_PLANT_ID)
    #print (str(dados_solar))
    #gDadosSolar = dados_solar['data']
    pegaDadosSolar()
else:
    log().error("I can't get access token")
    print (Color.B_Red + "I can't get access token" + Color.B_Default)
    quit()

# força a conexão
while not gConnected:
    mqttStart()
    time.sleep(1)  # wait for connection
    if not clientOk:
        time.sleep(240)

send_hass()

# primeira publicação
jsonx = publicaDadosWeb(gDadosSolar, HOYMILES_PLANT_ID)

if dl.float2number(gDadosSolar['total_eq'], 0) == 0:
    log().warning('All data is 0. Maybe your Plant_ID is wrong.')
    status['response'] = "Plant_ID could be wrong!"

send_clients_status()


if WEB_SERVER:  # se tiver webserver, inicia o web server
    iniciaWebServer()
    dl.writeJsonFile(FILE_COMM, jsonx)


printC(Color.B_LightCyan, 'Loop start!')
# loop start
while True:
    if gConnected:
        time_dif = dl.date_diff_in_Seconds(datetime.now(), \
            gDevices_enviados['t'])
        if time_dif > INTERVALO_HASS:
            gDevices_enviados['b'] = False
            send_hass()
        time_dif = dl.date_diff_in_Seconds(datetime.now(), \
            gMqttEnviado['t'])
        if time_dif > INTERVALO_GETDATA:
            pegaDadosSolar()
            jsonx = publicaDadosWeb(gDadosSolar, HOYMILES_PLANT_ID)
            if WEB_SERVER:
                dl.writeJsonFile(FILE_COMM, jsonx)
        if not clientOk: mqttStart()  # tenta client mqqt novamente.
    time.sleep(10) # dá um tempo de 10s








