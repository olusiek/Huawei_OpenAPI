#!/usr/bin/python3
import http.client
import json
import configparser # lib to get config data from file


# defined variables
API_URL = "intl.fusionsolar.huawei.com"

config = configparser.RawConfigParser()  
config.read('/Users/paolo/huawei/config.cfg') #location of configuration file

FS_API = dict(config.items('fusionsolar API')) #name of the section within configuration file
WhatToLog = dict(config.items('what to log'))
InfluxDB = dict(config.items('influxDB'))
#API_URL = FS_API['URL']

def get_token(username,password):

    conn = http.client.HTTPSConnection(API_URL)
    
    #print(username, " " , password, " " , API_URL)

    payload = json.dumps({
    "userName": username, #FS_API is a reference to the config.cfg
    "systemCode": password
    })

    headers = {
    'Content-Type': 'application/json'
    }

    conn.request("POST", "/thirdData/login", payload, headers)
    res = conn.getresponse()
    data = res.read()
    print(data.decode("utf-8"))
    token = res.getheader("XSRF-TOKEN") #Wyciagamy liste headerów. XSRF token jest w cookies ktore sa w headers.
    #print("token:" , token)
    
    conn.close() # zamknięcie połączenia

    return(token)


# DOPISAĆ KAWAŁEK KODU DO POBRANIA STATION_ID KTórego później będizemy uzywać
def get_stationID(token):
    # This function will return the list of the Station ID's used later to get all devices installed over there

    conn = http.client.HTTPSConnection(API_URL)

    payload = ''

    headers = {
    'Content-Type': 'application/json', 
    'XSRF-TOKEN': token
    }

    conn.request("POST","/thirdData/getStationList", payload, headers)

    res = conn.getresponse()
    data = json.loads(res.read())

    return(data["data"][0]["stationCode"])

def get_stationKPI(token,stationID):
    #this function will return the dict containing basic instalation data:
    #            "total_power": 545.3,
    #            "day_power": 0.87,
    #            "real_health_state": 3,
    #            "month_power": 18.75

    return(dict)

def get_inverterSN(token,stationID):
    # This function will return an inverter SN for a specific location to be used later to get KPI's
    # to make it more simple, we're looking just for an devIdType = '1' which means Inverter. 
    
    conn = http.client.HTTPSConnection(API_URL)

    payload = json.dumps({
    "stationCodes": stationID
    })

    headers = {
    'Content-Type': 'application/json', 
    'XSRF-TOKEN': token
    }

    conn.request("POST","/thirdData/getDevList", payload, headers)

    res = conn.getresponse()
    data = json.loads(res.read())

    data = data["data"]

    for i in data:
        
        #print(i["devTypeId"])
        #print(type(i["devTypeId"]))
        
        devTypeId = i["devTypeId"]
        if devTypeId == 1:
            #print(i["id"])
            inverterSN = i["id"]

    return(inverterSN)

def get_currentdata(token,inverterSN):
    #This function will return the DevRealKPI formated to the dict for specific inverter

    conn = http.client.HTTPSConnection(API_URL)

    payload = json.dumps({
    "devIds": "1000000034457107",
    "devTypeId": "1"
    })

    headers = {
    'Content-Type': 'application/json', 
    'XSRF-TOKEN': token
    }

    conn.request("POST","/thirdData/getDevRealKpi", payload, headers)

    res = conn.getresponse()
    data = json.loads(res.read())

    inverter_real_KPI = data["data"][0]["dataItemMap"]

    print(inverter_real_KPI["mppt_total_cap"])

    return(inverter_real_KPI)

def influxDB_update(influxdb_url,influxDB_name,data,inverterID,WhatToLog):
    #influxdb_url - an URL of the InfluxDB https://host:port/write. Defined in config.cfg
    #influxDB_name - name of InfluxDB. Defined in config.cfg
    #data - output from get_currentdata(). provides realKPI from an inverter
    #inverterID - output from get_inverterSN. is a part of influxDB structure
    #WhatToLog - A section from config.cfg where important fields are defined and will be sent to InfluxDB

    print(influxdb_url)
    print(influxDB_name)
    print(data)
    print(inverterID)
    print(WhatToLog)
    
    return()

token = get_token(FS_API['username'],FS_API['password'])

print(token)

stationID = get_stationID(token)

inverterID = get_inverterSN(token,stationID)

#print(inverterID)

#print(get_currentdata(token,inverterID))

current_data = get_currentdata(token,inverterID)

influxDB_update(InfluxDB['influxdb_url'],InfluxDB['influxdb_name'],current_data,inverterID,WhatToLog)


#token = "x-vz5e1dfteold1gkahhfw2ntdtgk6lguneoo746g4vt5imn6oc9nuan3tgbanjsdeo5qm2nnx4alg7ttc1dfueo7wrz1cpeoa6rftk8kabuliqm2q6o0arwpjby2p89hg"
conn2 = http.client.HTTPSConnection(API_URL)

payload = json.dumps({
    "stationCodes": "NE=34457105"
})
headers = {
    'Content-Type': 'application/json', 
    'XSRF-TOKEN': token
    }

#print('\n')
#print("Payload: " + payload)
#print('\n')
#print("Headers:" + json.dumps(headers, indent=4))
#print("Headers: \n\tContent-Type: " + headers["Content-Type"] + ", \n\tXSRF-TOKEN: " + headers["XSRF-TOKEN"])
#print('\n')
conn2.request("POST", "/thirdData/getStationRealKpi", payload, headers)
res2 = conn2.getresponse()
data2 = res2.read()
#print(res2.status, res2.reason)
#print(res2.getcode()) #pobranie kodu
#print('\n')
#print(type(data2.decode()))
#print(data2.decode("utf-8"))
#print('\n')
data2_json = json.loads(data2)
#print(json.dumps(data2_json, indent=4)) 
#print(type(data2_json))
#print(data2["failcode"])

#print(data2_json["data"][0]["stationCode"])

a = data2_json["data"][0]["stationCode"]

#print("\n" + a)

payload = json.dumps({
    "devIds": "1000000034457107",
    "devTypeId": "1"
})

conn3 = http.client.HTTPSConnection(API_URL)

conn3.request("POST","/thirdData/getDevRealKpi", payload, headers)
res3 = conn3.getresponse()
data3 = res3.read()
#print(data3)
data3_json = json.loads(data3)
#print(json.dumps(data3_json, indent=4))
#print(data3_json["data"][0]["dataItemMap"]["pv2_u"])
inverter_real_KPI = data3_json["data"][0]["dataItemMap"]

#print(json.dumps(inverter_real_KPI, indent=4, sort_keys=True))

influx_payload = ""

for keys,values in inverter_real_KPI.items():
#    print(keys,values)
#    print(type(keys))
#    print(type(values))
    influx_payload = influx_payload + keys + "=" + str(values) + "&"
#    print(values)

#print(influx_payload)
