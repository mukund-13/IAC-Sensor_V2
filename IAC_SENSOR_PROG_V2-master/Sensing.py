import sys, os
import resource
import time
import socket
import json, configparser
from openhab import OpenHAB
import re
import pathlib
import openhab.oauth2_helper


########################
# FUNCTION DEFINITIONS #
########################

# $$$$$$$$$ UTILITY FUNCTIONS ##############################################

############################################################
# update time interval reached flag
# param: previous time stamp, time interval for next time stamp
# return: a boolean flag indicating if next time stamp should be taken
# status: complete
def update_time_flag(previous_time, interval):
    if time.time() - previous_time >= interval:
        return True
    else:
        return False


############################################################
# purpose: print msg to a text file
# parameters: file to print to, message
# return: true if success, false otherwise
# status: complete
def msg_to_file(file_name, message):
    with open(file_name, "a") as file:
        file.write(message)
        file.write("$")
        return True
    return False


############################################################
# purpose: convert string / int to boolean
# parameters: string / int
# return: true if success, false otherwise
# status: complete
def ConvertToBoolean(val):
    if (val == '1' or val == 'True' or val == 1):
        return True
    return False


############################################################
# purpose: flip switches, for testing
# return: current value of the switching device
# status: complete
def flip(j):
    if j == 0:
        return 1
    else:
        return 0


# $$$$$$$$$ INITIALIZAtiON FUNCTIONS ##############################################

############################################################
# purpose: Read and convert the json formated program debug file and customer configuration file to dictionary format
# param: location of configuration file (eg: "configCustomer.ini")
# return: dictionary containing configuration info
# Configuration Dictionary Structure
#       Webserver Address: str
#       PHP Path: str
#       PC IP Address: str
#       Database Send Per Second: str
#       Nodes: dict
#       Sensing Devices: dict
#       Control Devices: dict
# status: complete
def json_to_dict(filename, flag):
    fp = open(filename, 'r')
    data = json.load(fp)
    fp.close()
    if (flag is not None):
        if (ConvertToBoolean(flag['config_to_dict_debug_flag'])):
            print("Customer Config data in Dictionary Format\n")
            print(data)
        else:
            print("Program Debug flags in Dictionary Format\n")
            print(data)
    return data


############################################################
# purpose: Find the which network identified node ID contains the port ID specified by the customer.
#          Write the network assigned node ID to the customer defined system
#          this function is called only once during the system initialization
# parameters: customer specified sensing/control system dictionary, Z-wave detected network dictionary
# return: node ID in the network that contains the customer specified Port ID
# status: complete
#
def MapNodeNameToInternalNodeID(systemData, network):
    NodeNameToIdMapping = {}
    for port in systemData["SensingPorts"]:
        if systemData["SensingPorts"][port]["NodeName"] not in NodeNameToIdMapping.keys():
            portid = int(systemData["SensingPorts"][port]["PortID"])
            for node in network.nodes:
                if node == 1:  # do not consider the controller node
                    continue
                if (int(portid) in network.nodes[node].get_sensors()):
                    NodeNameToIdMapping[systemData["SensingPorts"][port]["NodeName"]] = node  # node is node ID
                    break;
    for port in systemData["SwitchingPorts"]:
        if systemData["SwitchingPorts"][port]["NodeName"] not in NodeNameToIdMapping.keys():
            portid = int(systemData["SwitchingPorts"][port]["PortID"])
            for node in network.nodes:
                if node == 1:  # do not consider the controller node
                    continue
                if (int(portid) in network.nodes[node].get_sensors()):
                    NodeNameToIdMapping[systemData["SwitchingPorts"][port]["NodeName"]] = node  # node is node ID
                    break;

    return NodeNameToIdMapping


############################################################
# purpose: Compare the ports Id in configCustomerTest.json with network
#          this function is called only once during the system initialization
# parameters: network, systemData
# return: None
# status: complete
#
def CheckMissingNodeandPortIds(systemData, network):
    print('\n\nChecking config with OpenZwave network')
    SensingPorts = []
    SwitchingPorts = []
    SensorPortsInNode = []
    SwitchPortsInNode = []
    flag = 0
    #### Fetching Sensor Ports / Switching Ports from open z wave network
    for node in network.nodes:
        if node == 1:  # do not consider the controller node
            continue
        for val in (network.nodes[node].get_values_for_command_class(49)):
            SensorPortsInNode.append(val)
        for val in (network.nodes[node].get_values_for_command_class(37)):
            SwitchPortsInNode.append(val)

    #### Fetching Sensor Ports from config
    for port in systemData["SensingPorts"]:
        portid = int(systemData["SensingPorts"][port]["PortID"])
        SensingPorts.append(portid)

    #### Fetching Switching Ports from config
    for port in systemData["SwitchingPorts"]:
        portid = int(systemData["SwitchingPorts"][port]["PortID"])
        SwitchingPorts.append(portid)

    ###### Comparing sensor port
    missingInConfig = list(set(SensorPortsInNode) - set(SensingPorts))
    missingInNetwork = list(set(SensingPorts) - set(SensorPortsInNode))
    if (missingInNetwork != []):
        flag = 1
        print("The port Id :" + str(missingInNetwork) + " Not found in the OpenZWave Network")
    if (missingInConfig != []):
        print("Warning: The port Id :" + str(missingInConfig) + " is not in use, Please recheck")

    ###### Comaring switch port
    missingInConfigForSwitch = list(set(SwitchPortsInNode) - set(SwitchingPorts))
    missingInNetworkForSwitch = list(set(SwitchingPorts) - set(SwitchPortsInNode))
    if (missingInNetworkForSwitch != []):
        flag = 1
        print("The port Id :" + str(missingInConfigForSwitch) + " Not found in the OpenZWave Network")
    if (missingInConfigForSwitch != []):
        print("Warning: The port Id :" + str(missingInNetworkForSwitch) + " is not in use, Please recheck")

    if (flag == 1):
        print('Exiting!!!!!!')
        exit()
    print('Checking Completed !!')


# $$$$$$$$$$$ Application functions ######################################

############################################################
# purpose: compose message 0 - combine elements of company info into a single string,
# parameters: IP address of PC, company name, company phone number, company street address
# return: string representing all company info
# status: complete 6/29/2021, might need datalength
def pack_company_info_msg_0(my_ip_address, company_name, street_address, contact_person, phone_number, email_address,
                            pc_name):
    msg = "0|{}|{}|{}|{}|{}|{}|{}".format(my_ip_address, company_name, street_address, contact_person, phone_number,
                                          email_address, pc_name)
    if ConvertToBoolean(flag['pack_company_info_msg_debug_flag']):
        print(msg)
    return msg


############################################################
# purpose: compose message 1 -Combine sensor data
# parameters: name of the PC, node name, port id, sensor type, unit, lower limit, upper limit,equipment
# return: dictionary with flag
# status: completed on 11-18-21
def pack_sensor_info_msg_1(pc_name, node_name, sensor_port_id, sensor_type, unit, lower_limit, upper_limit,
                           equipment, port_type):
    msg = "1|{}|{}|{}|{}|{}|{}|{}|{}|{}".format(pc_name, node_name, sensor_port_id, sensor_type, unit, lower_limit,
                                                upper_limit, equipment, port_type)
    if ConvertToBoolean(flag['pack_sensor_info_msg_debug_flag']):
        print(msg)
    return msg


############################################################
# purpose: compose message 2 - combine elements of sensing data message into a single string
# parameters: device name, IP address of PC, sensor data
# return: string representing all company info
# status: complete, might need datalength
def pack_sensor_data_msg_2_v1(node_name, port_id, sensor_data):
    msg = "2|{}|{}|{}|{}".format(time.time(), node_name, port_id, sensor_data)
    if ConvertToBoolean(flag['pack_sensor_data_msg_debug_flag']):
        print(msg)
    return msg


def pack_sensor_data_msg_2_v2(pc_name,node_name, port_name, sensor_data):
    time_str = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))
    msg = "2|{}|{}|{}|{}|{}".format(time_str, pc_name,node_name, port_name, sensor_data)
    if ConvertToBoolean(flag['pack_sensor_data_msg_debug_flag']):
        print(msg)
    return msg


############################################################
# purpose: compose message 3 - combine elements of control message into a single string
# parameters: name of control device, port name of control device, control device type, control device lower limit, control device upper limit
# return: message containing control device information
# status: complete 6/30/2021, might need datalength
def pack_sensor_info_msg_3(pc_name, node_name, control_port_name, unit, control_lower_limit,
                           control_upper_limit, equipment_controlled, control_type):
    msg = "3|{}|{}|{}|{}|{}|{}|{}|{}".format(pc_name, node_name, control_port_name, unit, control_lower_limit,
                                             control_upper_limit,
                                             equipment_controlled, control_type)

    if ConvertToBoolean(flag['pack_control_msg_debug_flag']):
        print(msg)
    return msg


############################################################
# purpose: collect data from sensors
# parameters: name of the node that the device is connected to, ID of the sensing device, z-wave network
# return: current value of the sensor device
# status: complete
def read_sensor_data(sensor_id, openhab):
    currentValue = openhab.get_item_raw(sensor_id)['state']
    currentValue = re.sub("[^0-9^.]", "", currentValue)
    currentValue = (0.00 if currentValue == "" else float(currentValue))
    return currentValue


############################################################
# purpose: converts output of sensors (eg. Voltage) into actual meaning (eg. CO2 level)
# parameters: sensor output, upper and lower bound of sensor output, upper and lower bound of meaning
# return: meaning of sensor output
# status: completed and tested 6/29/2021

########## afr  processing data add cali--LK
def output_to_meaning(output, output_lb, output_ub, meaning_lb, meaning_ub):
    output_real = output - output_lb
    output_range_real = output_ub - output_lb
    meaning_range_real = meaning_ub - meaning_lb
    ratio = output_real / output_range_real
    meaning = (ratio * meaning_range_real) + meaning_lb
    # if debug_output_to_meaning_flag is True:
    #     print("...")
    return meaning


############################################################
# purpose: process sensor data as it is collected, 3 types so far
# parameters: previous average min or max, new sensor data, number of data values collected so far, type of processing (1=avg, 2=min, 3=max)
# return: postprocessing value
# status: complete
def process_data(previous_value, new_value, num_values_collected, process_type, sensor):
    new_value= new_value* systemData["SensingPorts"][sensor]["Calibration"]
    if num_values_collected == 0:
        return new_value
    if process_type == 1:  ## AVERAGE ##
        postprocessingValue = ((previous_value * (num_values_collected - 1)) + new_value) / (num_values_collected)
    elif process_type == 2:  ## MINIMUM ##
        if previous_value > new_value:
            postprocessingValue = new_value
        else:
            postprocessingValue = previous_value
    elif process_type == 3:  ## MAXIMUM ##
        if previous_value > new_value:
            postprocessingValue = previous_value
        else:
            postprocessingValue = new_value
    else:
        print("invalid process type")
    # debug flag
    # exception
    return postprocessingValue


############################################################
# purpose: decode message 4 - extract info from database command (msg from database)
# parameters: command sent from database
# return: all elements of the command stored in separate variables
# command message format:
# status: complete
def decode_database_command(database_command):
    start_index = 0
    counter = 0
    for i in range(0, len(database_command), 1):
        if database_command[i] == "|":
            counter += 1
            if counter == 1:
                msgID = database_command[start_index, i]
            elif counter == 2:
                device_name = database_command[start_index, i]
            elif counter == 3:
                ip_address = database_command[start_index, i]
            elif counter == 4:
                value = database_command[start_index, i]
            start_index = i + 1
    timestamp = database_command[start_index, len(database_command)]
    return msgID, device_name, ip_address, value, timestamp


############################################################
# purpose: prepare and send message 0
# parameters: sensor data, ip address
# return: none
# status: complete
def Prepare_and_Send_Message0(systemData, IPAddress):
    companyInfo = pack_company_info_msg_0(IPAddress, systemData["CompanyName"], systemData["CompanyLocation"],
                                          systemData["ContactName"], systemData["PhoneNumber"],
                                          systemData["EmailAddress"], systemData["PCName"])
    msg_to_file("FormattedSystemData.txt", companyInfo)
    ff = open("CommunicationFlag.txt", "x")


############################################################
# purpose: prepare and send message 1
# parameters: sensor data
# return: none
# status: complete
def Prepare_and_Send_Message1(systemData):
    for sensor in systemData["SensingPorts"]:
        sensorMsg = pack_sensor_info_msg_1(systemData["PCName"],
                                           systemData["SensingPorts"][sensor]["NodeName"],
                                           systemData["SensingPorts"][sensor]["PortName"],
                                           systemData["SensingPorts"][sensor]["SensorType"],
                                           systemData["SensingPorts"][sensor]["InputMeaningUnit"],
                                           systemData["SensingPorts"][sensor]["InputMeaningLowerBound"],
                                           systemData["SensingPorts"][sensor]["InputMeaningUpperBound"],
                                           systemData["SensingPorts"][sensor]["AttachedToEquipment"],
                                           systemData["SensingPorts"][sensor]["PortType"])
        msg_to_file("FormattedSystemData.txt", sensorMsg)
        ff = open("CommunicationFlag.txt", "w+")


############################################################
# purpose: prepare and send message 3
# parameters: sensor data
# return: none
# status: complete
def Prepare_and_Send_Message3(systemData):
    for switch in systemData["SwitchingPorts"]:
        switchMsg = pack_sensor_info_msg_3(systemData["PCName"],
                                           systemData["SwitchingPorts"][switch]["NodeName"],
                                           systemData["SwitchingPorts"][switch]["PortName"],
                                           systemData["SwitchingPorts"][switch]["Unit"],
                                           systemData["SwitchingPorts"][switch]["LowerLimit"],
                                           systemData["SwitchingPorts"][switch]["UpperLimit"],
                                           systemData["SwitchingPorts"][switch]["AttachedToEquipment"],
                                           systemData["SwitchingPorts"][switch]["PortType"])

        msg_to_file("FormattedSystemData.txt", switchMsg)
        ff = open("CommunicationFlag.txt", "w+")


############################################################
# purpose: read all sensor data based on each of their sampling inervals
# parameters: sensor data
# return: sensor data
# status: complete
def Read_Sensor_Data(systemData):
    for sensor in systemData["SensingPorts"]:
        if update_time_flag(systemData["SensingPorts"][sensor]["PreviousSampleTime"],
                            systemData["SensingPorts"][sensor]['PollingIntervalInSeconds']):
            label = systemData["SensingPorts"][sensor]["NodeName"] + "_" + systemData["SensingPorts"][sensor][
                "PortName"]
            sensor_reading = read_sensor_data(label, openhab) if CheckNodeStatus(
                systemData["SensingPorts"][sensor]["NodeName"]) else 99999
            systemData["SensingPorts"][sensor]["ProcessedValue"] = sensor_reading
            # sensorData["Sensing Devices"][sensor]["Processed Value"] = process_data(sensorData["Sensing Devices"][sensor]["Processed Value"], sensor_reading, sensorData["Sensing Devices"][sensor]['Num Values Collected'], sensorData["Sensing Devices"][sensor]['Filter Method'])
            proccessedData = process_data(systemData["SensingPorts"][sensor]["ProcessedValue"], sensor_reading,
                                          systemData["SensingPorts"][sensor]['NumValuesCollected'],
                                          systemData["SensingPorts"][sensor]['FilterMethod'], sensor)
            systemData["SensingPorts"][sensor]["PreviousSampleTime"] = time.time()
            if ConvertToBoolean(flag['read_sensor_data_debug_flag']):
                print("Node: " + str(systemData["SensingPorts"][sensor]["NodeName"]))
                print("Port Type: " + str(systemData["SensingPorts"][sensor]["PortType"]))
                print("Label: " + label)
                print("Sensor Reading: " + str(sensor_reading))
                print("proccessedData: " + str(proccessedData))
                print('----------------------------------------')
    return systemData


############################################################
# purpose: prepare and send message 2
# parameters: sensor data, previous database send
# return: systemData, previous_database_send
# status: complete
def Prepare_and_Send_Message2(systemData, previous_database_send_time):
    if update_time_flag(previous_database_send_time, systemData["DatabaseSendIntervalInSeconds"]):
        for sensor in systemData["SensingPorts"]:
            packed_msg = pack_sensor_data_msg_2_v2(systemData["PCName"],
                                                   systemData["SensingPorts"][sensor]["NodeName"],
                                                   systemData["SensingPorts"][sensor]["PortName"],
                                                   systemData["SensingPorts"][sensor]["ProcessedValue"])
            msg_to_file("FormattedSystemData.txt", packed_msg)
            systemData["SensingPorts"][sensor]["ProcessedValue"] = 0
            if ConvertToBoolean(flag['msg_to_file_debug_flag']):
                print(packed_msg)
        ff = open("CommunicationFlag.txt", "w+")
        previous_database_send_time = time.time()
    return systemData, previous_database_send_time


############################################################
# purpose: control switches in the node
# parameters: systemData
# return: systemData
# status: complete
def Control_the_switches_on_node(systemData):
    for switch in systemData["SwitchingPorts"]:
        if update_time_flag(systemData["SwitchingPorts"][switch]["PreviousSampleTime"],
                            systemData["SwitchingPorts"][switch]['PollingIntervalInSeconds']):
            if CheckNodeStatus(systemData["SwitchingPorts"][switch]["NodeName"]):
                label = systemData["SwitchingPorts"][switch]["NodeName"] + "_" + systemData["SwitchingPorts"][switch][
                "PortName"]
                switch = openhab.get_item(label)
                if (switch.state == "ON"):
                    switch.command('OFF')
                else:
                    switch.command('ON')
                time.sleep(20)
    return systemData


#############################$$$$$$$$$$ Network Integraty Check ########################################


###########################################################
# purpose: checks if a node is alive
# parameters: nodeid
# return: True, if  node is alive else False
# status: complete,
def CheckNodeStatus(nodename):
    nodes=openhab.req_get("/things")
    for node in nodes:
        if node['label']==nodename and node['statusInfo']['status']== 'ONLINE':
            return True
    return False

# $$$$$$$$$$ Adjusting Node Config ########################################


############################################################
# purpose: to set the sesitivity of sensor reading
# parameters: network
# return: none
# status: complete,
def SetSensorReadingSensitivity(network):
    for node in network.nodes:
        network.nodes[node].set_config_param(67, 1)
        network.nodes[node].set_config_param(68, 60)


# $$$$$$$ the main starts here ###############################################

if __name__ == "__main__":

    url_base = 'http://127.0.0.1:8080'
    api_username = 'IAC'
    api_password = 'IAC'
    oauth2_client_id = 'http://127.0.0.1/auth'
    oauth2_token_cache = pathlib.Path(__file__).resolve().parent / '.oauth2_token'

    # this must be set for oauthlib to work on http (do not set for https!)
    os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

    oauth2_token = openhab.oauth2_helper.get_oauth2_token(url_base, username=api_username, password=api_password)
    oauth2_config = {'client_id': oauth2_client_id,
                     'token_cache': str(oauth2_token_cache),
                     'token': oauth2_token
                     }
    openhab = OpenHAB(base_url=f'{url_base}/rest', oauth2_config=oauth2_config)
    configDebug = "configDebug.json"
    flag = json_to_dict(configDebug, None)

    configCustomer = "configCustomer.json"
    systemData = json_to_dict(configCustomer, flag)
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("8.8.8.8", 80))
    IPAddress = s.getsockname()[0]
    s.close()
    Prepare_and_Send_Message0(systemData, IPAddress)
    Prepare_and_Send_Message1(systemData)
    Prepare_and_Send_Message3(systemData)

    previous_database_send_time = 0
    print("------------------------------------------------------------")
    print("Retrieve sensor data from the network")
    print("------------------------------------------------------------")
    Ports = ['Temp1', 'IN1', 'IN2', 'Temp2']
    values = {}
    DevicesPortIDs = []
    NodeTemp = []
    i, skip, j = 0, False, 0
    while True:
        skip = True;
        systemData = Read_Sensor_Data(systemData)
        systemData, previous_database_send_time = Prepare_and_Send_Message2(systemData, previous_database_send_time)
        systemData = Control_the_switches_on_node(systemData)
