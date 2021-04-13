import time
import sys
import os
import _thread
import struct
import numpy as np
import pyvisa as visa
from datetime import date

def FindUSB():
    # Find the USB address the RTM3004 is plugged into.
    # Note, at the moment the program is written specifically for USB.
    ResList=rm.list_resources()
    
    for ResID in ResList:
        inst = rm.open_resource(ResID)
        ID = inst.query("*IDN?")
        if ID == 'Rohde&Schwarz,RTM3004,1335.8794k04/103028,01.550\n' and ResID[0:3]=="USB":
            return ResID
    
    # If RTM3004 was not found by the loop, give error message and quit.
    sys.exit("ERROR: RTM3004 was not found among the connected USB devices.")
    
###############################################
### GLOBAL VARIABLES VALUE ASSIGNMENT START ###
###############################################

# Setup device connections
rm = visa.ResourceManager()
USBID = FindUSB()
instr = rm.open_resource(USBID)

# First system argument will tell how many Waveforms to capture
if len(sys.argv) < 2:
    sys.exit("ERROR: Need to give number of events as command line option!")
nWaveforms = int(float(sys.argv[1]))    

# Second system argument is the file name and folder to save the waveforms to
# File extension defined here separately
if len(sys.argv) > 2:
    filename = str(sys.argv[2])
else:
    filename = "testdata/test"
fileext = ".dat"

# Initialize settings arrays
CHAN_SETTINGS = []
WAVEFORM_SETTINGS = []
MISC_SETTINGS = []

# [t_start, t_stop, n_samples, values per interval]
header = ""

# Determines Channels to measure
CHANMEAS=[False, False, False, False]
# Comparison waveform, used to see if the read waveform has changed since last read.
OldWaveform = ""
# Which channel is used for comparison
ComparisonChannel = 1

# Data root folder
folder = "testdata"
# Save folder named by measurement day
date = date.today()
datestring = date.strftime("%Y-%m-%d")
folder += datestring

# Create folders if they don't exist yet
if not os.path.exists(folder):
        os.makedirs(folderpath)
        print("Folder created")

###############################################
###      GLOBAL VARIABLE ASSIGNMENT END     ###
###############################################

def restartScope():
    # Not implemented yet
    print("WARNING: Scope not responding properly, trying to restart", end='', flush=True)
    try:
        urllib.request.urlopen('http://10.42.43.231/api/relay/0?apikey=69DCEEFA18B4AF96')
    except:
        print('')
        print("ERROR: Could not reach smart plug. Stopping execution!")
        quit()
    else:
        urllib.request.urlopen('http://10.42.43.231/api/relay/0?apikey=69DCEEFA18B4AF96&value=0')
        for rep in range(5):
            time.sleep(0.5)
            print('.', end='', flush=True)
        urllib.request.urlopen('http://10.42.43.231/api/relay/0?apikey=69DCEEFA18B4AF96&value=1')
        for rep in range(55):
            time.sleep(0.5)
            print('.', end='', flush=True)
    print('')

def init():
    global CHAN_SETTINGS
    global WAVEFORM_SETTINGS
    global MISC_SETTINGS
    # First, of course, reset the instrument
    instr.write("*RST")
    # Basic channel settings, sublists ordered by channel. 
    # Only edit the values here, add other commands to MISC_SETTINGS
    CHAN_SETTINGS = [["CHAN1:STAT ON", "CHAN1:COUP DC", "CHAN1:SCAL 2", "CHAN1:OFFS 0"],\
                     ["CHAN2:STAT OFF", "CHAN2:COUP DC", "CHAN2:SCAL 200E-3", "CHAN2:OFFS -800E-3"],\
                     ["CHAN3:STAT OFF", "CHAN3:COUP DC", "CHAN3:SCAL 0.5", "CHAN3:OFFS 1.5"], \
                     ["CHAN4:STAT OFF", "CHAN4:COUP DC", "CHAN4:SCAL 2", "CHAN4:OFFS 0"]]
    
    # Settings for tuning waveform graph
    # TRIG:A:SOUR CH<n>|EXT
    # TRIG:A:LEV<n> where n corresponds to the channel (5 = external trigger)
    ### DO NOT TOUCH "FORM" COMMANDS UNLESS YOU WANNA REWRITE THE DECODER AS WELL ###
    WAVEFORM_SETTINGS = ["TIM:SCAL 100E-3", "TIM:POS 1.5E-6", "ACQ:POIN 20000", "ACQ:INT SMHD", \
                         "TRIG:A:MODE NORM", "TRIG:A:SOUR CH1", "TRIG:A:LEV1 200E-3", "TRIG:A:EDGE:SLOP POS", \
                         "FORM REAL", "FORM:BORD LSBF"]
    
    # Other settings.
    MISC_SETTINGS = []
    
    # Check connection to device
    if instr.query("*IDN?") != 'Rohde&Schwarz,RTM3004,1335.8794k04/103028,01.550\n':
        print("ERROR: WRONG ID DURING INIT, RESTARTING SCOPE")
        instr.close()
        #restartScope()
    print("Scope found. Initializing",end='', flush=True)
    
    # Run basic channel settings
    for CHAN in CHAN_SETTINGS:
        for command in CHAN:
            instr.write(command)
    
    # Run Waveform settings
    for command in WAVEFORM_SETTINGS:
        instr.write(command)
    
    # Run misc settings
    for command in MISC_SETTINGS:
        instr.write(command)
    
    # Wait for a bit. Uncertain if necessary.
    for rep in range(12):
        time.sleep(0.5)
        print('.', end='', flush=True)
    print('', end='\n', flush=True)
        
    # Fetch header, 
    FetchHeader()
    
    
def FetchHeader():
    # Changes the 
    global header
    # [t_start, t_stop, n_samples, values per interval]
    headerstring = instr.query("CHAN:DATA:HEAD?")
    # Parse numerical values from the string format header
    sep1 = headerstring.find(",");
    sep2 = headerstring.find(",",sep1+1);
    sep3 = headerstring.find(",",sep2+1);
    header = [float(headerstring[0:sep1]), float(headerstring[sep1+1:sep2]), \
              int(headerstring[sep2+1:sep3]), int(headerstring[sep3+1:])]
    if header[0]==0 and header[1]==0 and header [2]==0 and header[3]==0:
        print("No reference signal detected.")
        Waiter = input("Please connect a signal or enter \"q\" to quit.")
        if Waiter == "q":
            sys.exit("Program ended by user")
        else:
            print("Retrying", flush=True)
            for rep in range(10):
                time.sleep(0.5)
                print('.', end='', flush=True)
            print('', end='\n', flush=True)
            FetchHeader()

def getWaveforms():
    global OldWaveform
    global ComparisonChannel
    global CHANMEAS
    
    # Check which channels are online for measurement
    for i in range(len(CHANMEAS)):
        STAT = int(instr.query("CHAN"+str(i+1)+":STAT?"))
        if i+1==ComparisonChannel and STAT==0:
            sys.exit("ERROR: Comparison channel offline, quitting program")
        if STAT == 1:
            CHANMEAS[i] = True
        else:
            CHANMEAS[i] = False
    while True:
        # Initialize data array
        data=[]
        # Datakey tells which channels were recorded
        datakey=[]
        # Read all data channels
        if CHANMEAS[0]:
            instr.write("CHAN1:DATA?")
            ch1 = instr.read_raw()
            data.append(ch1)
            datakey.append("CHAN1")
        if CHANMEAS[1]:
            instr.write("CHAN2:DATA?")
            ch2 = instr.read_raw()
            data.append(ch2)
            datakey.append("CHAN2")
        if CHANMEAS[2]:
            instr.write("CHAN3:DATA?")
            ch3 = instr.read_raw()
            data.append(ch3)
            datakey.append("CHAN3")
        if CHANMEAS[3]:
            instr.write("CHAN4:DATA?")
            ch4 = instr.read_raw()
            data.append(ch4)
            datakey.append("CHAN4") 
        
        # Read the comparison data
        instr.write("CHAN"+str(ComparisonChannel)+":DATA?")
        ch_check = instr.read_raw()
        
        # Check that data has changed from last measurement (OldWaveform) 
        # and that oscilloscope didn't refresh mid-measurement (ch_check)
        if (data[ComparisonChannel-1] != OldWaveform) and (data[ComparisonChannel-1] == ch_check):
            OldWaveform = ch_check
            return data, datakey


def decodeWaveforms(data):
    # By default, data is read in binary packed format, this function decodes that into human-readable data.
    # [t_start, t_stop, n_samples, values per interval]
    global header
    t_start, t_stop, nSamples = header[0], header[1], header[2]
    dt=(t_stop-t_start)/(nSamples-1)
    
    # Initializing data array
    decWaves = np.zeros((1+len(data),nSamples),'f')
    decWaves[0] = [round((t_start+i*dt)*1e10)/1e10 for i in range(nSamples)]
    
    for ch in range(len(data)):
        # First character should be "#".
        pound = data[ch][0:1]
        if pound != b'#':
            print("ERROR: Unknown data format returned from scope!")
            quit()
            
        # Second character is number of following digits for data string length value.
        length_digits = int(data[ch][1:2])
        data_length = int(data[ch][2:length_digits+2])
        
        # from the given data length, and known header length, we get indices:
        data_begin = length_digits + 2  # 2 for the '#' and digit count
        data_end = data_begin + data_length
        data_entries = data_length // 4;
        
        # Check that data length matches up
        if data_entries != nSamples:
            print("ERROR: Data length not consistent with number of sampleFs!")
            quit()
        # Unpack the data
        decWaves[ch+1] = np.float32(struct.unpack('f'*data_entries,data[ch][data_begin:data_end]))
    return decWaves


def WriteFile(data, datakey, filename="test.dat"):
    data = decodeWaveforms(data)
    data = data.tolist()
    
    writelines="t\t"
    for CHAN in datakey:
        writelines += CHAN+"\t"
    writelines += "\r\n"
    for i in range(len(data[0])):
        for j in range(len(data)):
            writelines += format(data[j][i],"+.8e")+"\t"
        writelines += "\n"
        
    f = open(filename,'w')
    f.write(writelines)
    f.close() 


def main():
    global nWaveforms
    global filename
    global fileext
    
    init()
    for i in range(nWaveforms):
        savename = filename+"_meas"+str(i+1).zfill(len(nWaveforms))+fileext
        data, datakey = getWaveforms()
        WriteFile(data,datakey,savename)
        print("Waveform number "+str(i+1)+" done")
        #_thread.start_new_thread(WriteFile, (data,datakey,savename))
    

def maintest():    
    global nWaveforms
    
    try:
        scope = init(usbtmc.Instrument(scope_id))
        nSamples = getNSamples(scope)
    except usb.core.USBError:
        exc = sys.exc_info()[1]
        if exc.errno == 110:
            restartScope()
    
            try:
                scope = init(usbtmc.Instrument(scope_id))
                nSamples = getNSamples(scope)
            except:
                raise ValueError("ERROR: Reset not successful, check scope and connection!")
        else:
            print("ERROR: Unknown USB Error. Stopping execution!")
            raise
    except ValueError as err:
        if err.args == ('WrongIdent'):
            restartScope()
            try:
                scope = init(usbtmc.Instrument(scope_id))
                nSamples = getNSamples(scope)
            except:
                raise ValueError("ERROR: Reset not successful, check scope and connection!")
        else:
            print("ERROR: Unknown Error. Stopping execution!")
            raise
    except:
        raise
    
    f = ROOT.TFile("/home/positron/DAQ/scripts/scope.temp.root", "RECREATE","RTM3004 DAQ file",201)
    
    graphList = [ [ROOT.TGraph(nSamples) for ch in range(4)] for n in range(nWaveforms) ]
    
    placeholderString=""
    for i in range(24008):
        placeholderString+=str('0')
    saveStrings = [placeholderString for ch in range(4)]
    
    startTime = time.time()
    
    lock = False
    for i in range(0,nWaveforms):
        print("Acquiring event #",str(i+1),"of",str(nWaveforms), end="\r", flush=True)
        try:
            saveStrings = getWaveforms(scope)
        except usb.core.USBError:
            exc = sys.exc_info()[1]
            if exc.errno == 110:
                print('')
                restartScope()
                try:
                    scope = init(usbtmc.Instrument(scope_id))
                    saveStrings = getWaveforms(scope)
                except:
                    raise ValueError("ERROR: Reset not successful, check scope and connection!")
            else:
                print("ERROR: Unknown USB Error. Stopping execution!")
                raise
        while lock:
            time.sleep(0.0001)
        lock = True
        _thread.start_new_thread(saveToFile, (saveStrings,i,nSamples))
    
    while lock:
        time.sleep(0.0001)
    
    f.Close()
    
    print("Acquisition of",str(nWaveforms),"events completed. Elapsed time:",round(time.time()-startTime),"seconds.")
    sys.exit(0)


if __name__ == "__main__":
    main()