import numpy as np
import os
import time
import tkinter as tk
from tkinter import filedialog

###########################################################################
###                     QUICK USE INSTRUCTIONS:                         ###
###  Call program from commandline, you will be prompted to choose the  ###
### directory of your datafiles. After it has been chosen, program will ###
### run automatically. You must (for now) manually set the integration  ###
###       limits in the global parameter part of the program.           ###
###########################################################################


def getHeader():
    global filedef
    global datafolder
    filelist = os.listdir(datafolder)
    for file in filelist:
        if file[0:len(filedef[0])] == filedef[0]:
            filepath = datafolder+"/"+file
            f = open(filepath,"r")
            lines = f.readlines()
            f.close()
            header=lines[0].split()
            return header

def getFiledef():
    global datafolder
    global filedef
    filelist = os.listdir(datafolder)
    filedef = []
    for file in filelist:
        filedefEnd = file.rfind("_")
        if file[-4:] == ".dat" and not file[:filedefEnd] in filedef and not file[:3]=="OUT":
            filedef.append(file[:filedefEnd])

### GLOBALS ###

# Used for the directorz choosing
root = tk.Tk()
root.withdraw()

# Prompt to choose the folder for your data.
datafolder = "."
datafolder = filedialog.askdirectory(initialdir = "..")

if not os.path.exists(datafolder+"/processed"):
        os.makedirs(datafolder+"/processed")
        print("Folder created: " + datafolder+"/processed")

# filedef is list of file identifiers (measurement series)
filedef = []
# If set to False, you must specify the files manually above.
autoFiledef = True
    
# Limits of integration. Later on should be automatised or set to be dynamically changeable.
integrationLimits=[-1, 1]

start_time=time.time()
n_Files=0
### Globals end ###

def readData(filedef):
    # Reads the data from files
    global datafolder
    global header
    global n_Files
    
    filelist = os.listdir(datafolder)

    data=[]
    nFiles = 0
    for file in filelist:
        if file[0:len(filedef)] == filedef:
            filepath = datafolder+"/"+file
            nFiles += 1
            f = open(filepath,"r")
            lines = f.readlines()
            f.close()
            header=lines[0].split()
            n_Files+=1
            
            tempdata = []
            for i in range(len(lines[2].split())):
                tempdata.append([])
                
            for i in range(1,len(lines)):
                row = lines[i].split()
                for j in range(len(row)):   
                    tempdata[j].append(float(row[j]))
            
            if data==[]:
                for column in tempdata:
                    data.append(column)
            else:
                for columnindex in range(len(tempdata)):
                    for i in range(len(tempdata[0])):
                        if columnindex != 0:
                            data[columnindex][i] += tempdata[columnindex][i]

    for column in data:
        for index in range(len(column)):
            if column != data[0]:
                column[index]=column[index]/nFiles
    
    writelines = ""
    for i in range(len(header)):
        writelines += header[i]+"\t"
    writelines+="\n"
    for i in range(len(data[0])):
        for j in range(len(data)):
            writelines += str(data[j][i])+"\t"
        writelines += "\n"
    
    filename = datafolder+"/processed/OUTavg"+filedef+".dat"
    f = open(filename, "w")
    f.write(writelines)
    f.close() 
    
    return data



def integrate(averagedData,filedef):
    # Does the integration
    global integrationLimits
    
    #offsetData = [[],[]]
    #for i in range(len(averagedData)):
    #    if averagedData[0][i]<0:
    #        offsetData[0].append(averagedData[0][i])
    #        offsetData[1].append(averagedData[1][i])
    #offset = sum(offsetData[1])/len(offsetData[1])
    offset = 0.000067
    #print("Calculated offset: "+str(offset))
    
    data = np.zeros((2*len(averagedData)-1,len(averagedData[0])))
    data[0] = averagedData[0] 
    for i in range(1,len(averagedData)):
        data[2*i-1] = averagedData[i]
        data[2*i-1] -= offset
        for j in range(len(averagedData[0])):
            data[2*i,j] = np.trapz(data[2*i-1,0:j],data[0,0:j])
    
    integralRange = []
    for index in range(len(averagedData[0])):
        if averagedData[0][index] > integrationLimits[0] and averagedData[0][index] < integrationLimits[1]:
            integralRange.append(index)
    
    intData = np.zeros((len(data),len(integralRange)))
    for index in range(len(integralRange)):
        for jndex in range(len(data)):
            intData[jndex,index] = data[jndex, integralRange[index]]

    writelines = "t\t"
    for i in range(1,len(header)):
        writelines += header[i]+"\t"+header[i]+" int\t"
    writelines+="\n"
    for i in range(len(data[0])):
        if i in integralRange:
            for j in range(len(data)):
                writelines += str(data[j][i])+"\t"
            writelines += "\n"

    filename = datafolder+"/processed/OUTint"+filedef+".dat"
    f = open(filename, "w")
    f.write(writelines)
    f.close()
    return intData


def main():
    global header
    global start_time
    global n_Files
    global Filedef
    
    if autoFiledef:
        getFiledef()
        print("Automatically fetched filedef:\n"+str(filedef))
    header = getHeader()
    
    intstring = "fileset\tdt\t"
    print(header)
    for j in range(1,len(header)):
        intstring += "d"+header[j]+"\tdint"+header[j]+"\t"  
    intstring+="\n"
    for i in filedef:
        print(i)
        averagedData = readData(i)
        intData = integrate(averagedData,i)
        intstring += i+"\t"
        for column in range(len(intData)):
            intstring += str(intData[column,-1]-intData[column,0])+"\t"
        intstring+="\n"
    
    n_Files = len(os.listdir(datafolder))
    tot_time=time.time()-start_time
    print("Handled "+str(n_Files)+f" files in {tot_time:.2} seconds.")
    print(f"Average time per file: {tot_time/n_Files:.3} seconds")
    
    filename = datafolder+"/processed/OUTintall"+filedef[0][0:3]+".dat"
    f = open(filename, "w")
    f.write(intstring)
    f.close() 
    
if __name__ == "__main__":
    main()