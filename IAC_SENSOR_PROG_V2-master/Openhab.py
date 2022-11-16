from openhab import OpenHAB
############### https://www.openhab.org/docs/installation/linux.html
base_url = 'http://127.0.0.1:8080/rest'
openhab = OpenHAB(base_url)

# fetch all items
items = openhab.fetch_all_items()
# i=openhab.get_item('ZWaveNode002FGBS222SmartImplant_Sensortemperature1')
a=openhab.get_item_raw('IAC001_Sensortemperature1')
print(items)