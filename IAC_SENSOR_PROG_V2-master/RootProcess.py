############################################################
# This root program, RootProcess.py is used for starting
# the energy equipment data sensing and control.  It spawns 
# two other processes: Sensing.py and DatabaseWrite.py.   
# The command for program execution: ????
# Input parameters: none
# Output: None
# Update Date: Nov 20, 2021
# Persor who updated this version:
# Status: fully tested and works???
############################################################
import os
import multiprocessing

def execute(process):
    os.system(f'python {process}')

processes = ('Sensing.py','DatabaseWrite.py')


if __name__ == '__main__':
    try:
        os.remove("CommunicationFlag.txt")
    except Exception as e:
        pass
 
    try:
        os.remove("FormattedSensorData.txt")
    except Exception as e:
        pass

    ####### Dont remove backupdata
    try:
       os.remove("BackupData.txt")
    except Exception as e:
       pass
 
    process_pool = multiprocessing.Pool(processes=2)
    process_pool.map(execute, processes)
