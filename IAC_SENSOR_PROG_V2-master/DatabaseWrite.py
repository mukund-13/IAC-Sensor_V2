import json
import os
import requests
import configparser

debug = True


def send_to_database(address, msg):

    # response, msg = requests.get(address.format(msg[0: 1], msg[2:]))
    response = requests.get(address.format(msg[0: 1], msg[2:]))
    print(address.format(msg[0: 1], msg[2:]))
    if response.ok:
        # if(msg = ???)
        # write t o a file to sensing process
        return True

    else:
        return False


def write_to_backup(backup, data):
    with open(backup, "a") as _:
        _.write(data)
        return True
    return False


def delete_from_file(file_name, part_to_delete):
    file = open(file_name, "r+")
    file_contents = file.read()
    file_contents = remove_prefix(file_contents, part_to_delete)
    file.write(file_contents)
    file.close()


def remove_prefix(input_string, prefix):
    if prefix and input_string.startswith(prefix):
        return input_string[:len(prefix)]
    return input_string


# Main program starts here

# Get webserver addtess
def json_to_dict(filename):
    fp = open(filename, 'r')
    data = json.load(fp)
    fp.close()
    return data
config = json_to_dict("configCustomer.json")
webserver_address = config['WebserverAddress']

# Open backup file (file may or may not exist already)
f = open("BackupData.txt", "x")

while True:
    if os.path.isfile("CommunicationFlag.txt"):
        os.remove("CommunicationFlag.txt")
        file = open("FormattedSystemData.txt", "r+")
        fileContents = file.read()
        file.truncate(0)  # sets the file size to 0 bytes and moves the file pointer back to the start of the buffer
        file.close()
        if debug:
            print("FILE CONTENTS: {}".format(fileContents))

        # following parse the file for messages
        start_index = 0
        for i in range(0, len(fileContents), 1):
            if fileContents[i] == "$":
                msg = fileContents[start_index: i]  ## TRY DIFFERENT SUBSTRING METHOD
                if debug:
                    print("sending: {}".format(msg))
                successfulSend = send_to_database(webserver_address, msg)
                start_index = i + 1

        # save and read data from back up file
        if not successfulSend:  # save data to backup file
            print("CONNECTION IS DOWN--BACKING UP DATA")
            write_to_backup("BackupData.txt", fileContents)
        else:  # retrive all backed up data, if there is any, from backup file and parse the mesgs and send them
            backup = open("BackupData.txt")
            backupContents = backup.read()
            start_index = 0
            for i in range(0, len(backupContents), 1):
                if backupContents[i] == "$":
                    msg = backupContents[start_index: i]
                    successfulSend = send_to_database(webserver_address, msg)
                    start_index = i + 1
                    if successfulSend:
                        delete_from_file("BackupData.txt", msg)