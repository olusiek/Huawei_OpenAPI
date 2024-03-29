#!/usr/bin/python3
import http.client
import json
import configparser # lib to get config data from file


# defined variables
config = configparser.RawConfigParser()  
config.read('/etc/huawei/config.cfg') #location of configuration file

FS_API = dict(config.items('fusionsolar API')) #name of the section within configuration file
WhatToLog = dict(config.items('what to log'))
InfluxDB = dict(config.items('influxDB'))
API_URL = FS_API['url']

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
    #print(data.decode("utf-8"))
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
    "devIds": inverterSN,
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

def influxDB_update(influxdb_url,influxDB_port,influxDB_name,data,inverterID,WhatToLog):
    #influxdb_url - an URL of the InfluxDB https://host:port/write. Defined in config.cfg
    #influxDB_name - name of InfluxDB. Defined in config.cfg
    #data - output from get_currentdata(). provides realKPI from an inverter 
    #inverterID - output from get_inverterSN. is a part of influxDB structure
    #WhatToLog - A section from config.cfg where important fields are defined and will be sent to InfluxDB

    #print(influxdb_url)
    #print(influxDB_name)
    #print(data)
    #print(inverterID)
    #print(WhatToLog)
    

    WATT = {'1' :  {'volts': round(data["a_u"],2), 'amps': round(data["a_i"],2), 'watts': round(data["a_i"] * data["a_u"],2)},
            '2' :  {'volts': round(data["b_u"],2), 'amps': round(data["b_i"],2), 'watts': round(data["b_i"] * data["b_u"],2)},
            '3' :  {'volts': round(data["c_u"],2), 'amps': round(data["c_i"],2), 'watts': round(data["c_i"] * data["c_u"],2)},
            '0' :  {'volts': 0, 'amps': 0, 'watts': round(data["a_i"] * data["a_u"] + data["b_i"] * data["b_u"] + data["c_i"] * data["c_u"],2)} #introduced Phase 0 to catch summarized WATTs for entire instalation
            }
    #Phase1_WATT, '2': Phase2_WATT, '3': Phase3_WATT, '0': Summary_WATT}

    #print(WATT)

    #print(data["efficiency"])

    #power,sensor=sdm120c,location=main_PDU,phase=2 Volts={0:.1f},frequency={1:.1f},Amps={2:.1f},Watts={3:.1f},Used=

    #power,sensor=SUN2000-5KTL-M1,location=garage,phase=1 Volts = data["a_u"], Amps=data["a_i"], Watts=Phase1_WAT
    #power,sensor=SUN2000-5KTL-M1,location=garage,phase=2 Volts = data["b_u"], Amps=data["b_i"], Watts=Phase2_WAT
    #power,sensor=SUN2000-5KTL-M1,location=garage,phase=3 Volts = data["c_u"], Amps=data["c_i"], Watts=Phase3_WAT

    #pv,device=SUN2000-5KTL-M1,location=garage,
    #print(data['a_u'])
    #print(type(data['a_u']))
    #payload = "power,sensor=SUN20005KTLM1,location=garage,phase=1 Volts=" + str(data['a_u']) + ",Amps=" + str(data['a_i']) + ",Watts=" + str(Phase1_WATT)
    #payload2 = "power,sensor=SUN20005KTLM1,location=garage,phase=2 Volts=" + str(data['b_u']) + ",Amps=" + str(data['b_i']) + ",Watts=" + str(Phase2_WATT)
    #payload3 = "power,sensor=SUN20005KTLM1,location=garage,phase=3 Volts=" + str(data['c_u']) + ",Amps=" + str(data['c_i']) + ",Watts=" + str(Phase3_WATT)

    payload = ""

    #print(payload)

    headers = {
        'Content-Type': 'application/json'
    }

    for phase,phasedata in WATT.items():
        if phase == "0":
            #print(phasedata)
            #print("Jestem faza 0!!!!!!!!!!!!!!!!!!! Phase", phase, "Watts:", phasedata['watts'])
            #print("uwzględniając efficiency:", round(phasedata['watts'] * (data["efficiency"]/100)))
            payload = "power,sensor=" + str(inverterID) + ",location=garage,phase=" + str(phase) + " Volts=0,Amps=0,Watts=" + str(round(phasedata['watts'] * (data["efficiency"]/100)))

        else:
            #print("Phase", phase, phasedata['volts'])
            #print(phasedata)
    #        payload = "power,sensor=SUN20005KTLM1,location=garage,phase=" + phase + " Volts=" + str(data['a_u']) + ",Amps=" + str(data['a_i']) + ",Watts=" + str(Phase1_WATT)
            payload = "power,sensor=" + str(inverterID) + ",location=garage,phase=" + str(phase) + " Volts=" + str(round(phasedata['volts'])) + ",Amps=" + str(round(phasedata['amps'],2)) + ",Watts=" + str(round(phasedata['watts'] * (data["efficiency"]/100)))
        
        #print(payload)
        #print(data["active_power"])
        influxDB_conn = http.client.HTTPConnection(influxdb_url,influxDB_port)
        influxDB_conn.request("POST", "/write?db=testdb", payload,headers)
        res = influxDB_conn.getresponse()
        influxDB_conn.close()

    # Second iteration to keep all the data in dedicated pv space in influxDB. It can be reused 

    for phase,phasedata in WATT.items():
        if phase == "0":
            payload = "pv,sensor=" + str(inverterID) + ",phase=" + str(phase) + " Volts=0,Amps=0,Watts=" + str(round(phasedata['watts'] * (data["efficiency"]/100)))

        else:
            payload = "pv,sensor=" + str(inverterID) + ",phase=" + str(phase) + " Volts=" + str(round(phasedata['volts'])) + ",Amps=" + str(round(phasedata['amps'],2)) + ",Watts=" + str(round(phasedata['watts'] * (data["efficiency"]/100)))
        
        influxDB_conn = http.client.HTTPConnection(influxdb_url,influxDB_port)
        influxDB_conn.request("POST", "/write?db=testdb", payload,headers)
        res = influxDB_conn.getresponse()
        influxDB_conn.close()
    

    #Now lets process rest of the _data_ available :) In the next version maybe i will revert it into the loop
    payload_keys = "pv,sensor=" + str(inverterID)
    payload_values = ""

    if WhatToLog["temperature"] == "Yes":
        if payload_values:
            payload_values = payload_values + ",temperature=" + str(data["temperature"])
        else:
            payload_values = payload_values + "temperature=" + str(data["temperature"])

    if WhatToLog["efficiency"] == "Yes":
        if payload_values:
            payload_values = payload_values + ",efficiency=" + str(data["efficiency"])
        else:
            payload_values = payload_values + "efficiency=" + str(data["efficiency"])

    if WhatToLog["active_power"] == "Yes":
        if payload_values:
            payload_values = payload_values + ",active_power=" + str(data["active_power"])
        else:
            payload_values = payload_values + "active_power=" + str(data["active_power"])

    if WhatToLog["elec_freq"] == "Yes":
        if payload_values:
            payload_values = payload_values + ",elec_freq=" + str(data["elec_freq"])
        else:
            payload_values = payload_values + "elec_freq=" + str(data["elec_freq"])

    if WhatToLog["power_factor"] == "Yes":
        if payload_values:
            payload_values = payload_values + ",power_factor=" + str(data["power_factor"])
        else:
            payload_values = payload_values + "power_factor=" + str(data["power_factor"])

    if WhatToLog["total_cap"] == "Yes":
        if payload_values:
            payload_values = payload_values + ",total_cap=" + str(data["total_cap"])
        else:
            payload_values = payload_values + "total_cap=" + str(data["total_cap"])

    if WhatToLog["mppt_power"] == "Yes":
        if payload_values:
            payload_values = payload_values + ",mppt_power=" + str(data["mppt_power"])
        else:
            payload_values = payload_values + "mppt_power=" + str(data["mppt_power"])

    if WhatToLog["mppt_total_cap"] == "Yes":
        if payload_values:
            payload_values = payload_values + ",mppt_total_cap=" + str(data["mppt_total_cap"])
        else:
            payload_values = payload_values + "mppt_total_cap=" + str(data["mppt_total_cap"])



    payload = payload_keys + " " + payload_values
    print(payload)

    influxDB_conn = http.client.HTTPConnection(influxdb_url,influxDB_port)
    influxDB_conn.request("POST", "/write?db=testdb", payload,headers)
    res = influxDB_conn.getresponse()
    influxDB_conn.close()

    payload_keys = "pv,sensor=" + str(inverterID)
    payload_values = ""


    #PV 24 iterations should be here - next version will do that using loop - it is not needed for current stage
    if WhatToLog["pv1"] == "Yes":
        if payload_values:
            payload_values = payload_values + ",Volts=" + str(round(data['pv1_u'])) + ",Amps=" + str(round(data['pv1_i'])) + ",Watts=" + str(round(data['pv1_u'] * data['pv1_i']))
        else:
            payload_values = payload_values + "Volts=" + str(round(data['pv1_u'])) + ",Amps=" + str(round(data['pv1_i'])) + ",Watts=" + str(round(data['pv1_u'] * data['pv1_i']))
        payload_keys = payload_keys + ",pv=1"


    payload = payload_keys + " " + payload_values
    print(payload)

    influxDB_conn = http.client.HTTPConnection(influxdb_url,influxDB_port)
    influxDB_conn.request("POST", "/write?db=testdb", payload,headers)
    res = influxDB_conn.getresponse()
    influxDB_conn.close()

    payload_keys = "pv,sensor=" + str(inverterID)
    payload_values = ""

    # MPPT twelve iterations - next version will do that using loop
    if WhatToLog["mppt_1_cap"] == "Yes":
        if payload_values:
            payload_values = payload_values + ",cap=" + str(data["mppt_1_cap"])
        else:
            payload_values = payload_values + "cap=" + str(data["mppt_1_cap"])
        payload_keys = payload_keys + ",mppt=1"

    payload = payload_keys + " " + payload_values

    print(payload)
    influxDB_conn = http.client.HTTPConnection(influxdb_url,influxDB_port)
    influxDB_conn.request("POST", "/write?db=testdb", payload,headers)
    res = influxDB_conn.getresponse()
    influxDB_conn.close()

    return()



token = get_token(FS_API['username'],FS_API['password'])

#print(token)

stationID = get_stationID(token)

inverterID = get_inverterSN(token,stationID)

#print(inverterID)

#print(get_currentdata(token,inverterID))

current_data = get_currentdata(token,inverterID)

influxDB_update(InfluxDB['influxdb_url'],InfluxDB['influxdb_port'],InfluxDB['influxdb_name'],current_data,inverterID,WhatToLog)

