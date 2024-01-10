import warnings
warnings.filterwarnings("ignore", category=UserWarning)
import PySimpleGUI as sg
import numpy as np
import os
from matplotlib import pyplot as plt
import pandas as pd
import glob
from xgboost import XGBClassifier
import time
import sys
import getopt
import cdi

from cdi import spec
import pickle as pk
import csv
from scipy.signal import savgol_filter
from scipy import signal

import socket
import random
import time
from scipy import signal



       
dev0 = spec(debug=False)   
setup_path = "C:/plastic/Jul04_hardplastics.stp"    #enter setup file here
flash_slot = cdi.CAL_OnDisk    
init_results = dev0.Init(setup_path,flash_slot)


if init_results["init_result"] in [cdi.INIT_Failed, cdi.INIT_Illegal_Addr]:
    print("No hardware found, shutting down.")        
    sys.exit(2)   


dev0.comp_mode = cdi.CM_NormAU  
if dev0.comp_mode != cdi.CM_NormAU :
    print("Error setting compensation mode")


int_time = dev0.GetIntegrateTime()["int_time"]

          
DICTIONARY_PLASTIC_KINDS = ("Others","PET", "HDPE", "PVC", "HDPE", "PP","PS","None", "Debris")
countHighestConfidence={"Others":0,"HDPE":0,"HDPE":0,"PP":0,"PET":0,"PS":0}
bg_color=("Red","gold","light green")

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)




###############################################################   GUI SETUP  ##################################################################################################

_VARS = {'window': False}
imsize=(50, 50)
b="Black"
h="helvetica 20 bold"
bcg='#f5f5f5'






extreme=[[sg.Button('Sig',font="Arial 1", image_size=imsize,image_filename=resource_path("Signallevel.png"),tooltip="Obtain signal strength")]]



layout=[[[[extreme]]]]

_VARS['window'] = sg.Window('Plastic sort CEERI',
                            layout,background_color=bcg,
                            finalize=True,
                            resizable=False,
                           
                            )


_VARS['window'].Maximize()


def popup(message):
    sg.theme('DarkGrey')
    layout = [[sg.Text(message)]]
    window = sg.Window('Message', layout, no_titlebar=True, keep_on_top=True, finalize=True)
    
    return window

##############################################################################################################################################################################



def get_spectrum(int_time,dev0):
    j=0
    wavelength=[]
    spectrum=[]
    while True:
        convert_results = dev0.Convert()
        if convert_results["sample_done"] != 0:            
            spectrum = convert_results["spectrum"]
            wavelength=convert_results["wavelength_array"]
            sig=dev0.GetLinearizedCounts()["samp"]
            
            j=0
            return wavelength,spectrum,sig
            break
        else:
            j=j+1
            if j==1000:
                print(j)
                print("Unable to connect to Hardware.....")
                dev0.USB2_EndThread()
                sys.exit(2)
                j=0
                return [],[]
                break           
            

################################################################Model Deployment and signal processing ############################################################################################################    


def analyse(test):

        #1,1723-->PET 1723,2615-->HDPE

        test=pd.DataFrame
        test=signal.detrend(test)
    ##    y= savgol_filter(test, 17, polyorder = 2,deriv=2)    

        if test[49] ==np.max(test) or test[46] ==np.max(test) :
            AI_result="Polyolefins"
        elif test[120]==np.max(test):
            AI_result="PET"
        elif test[123]==np.max(test) or test[38]==np.max(test):
            AI_result="PS"
        else:
            AI_result="Wrong"
        return AI_result
start=0
end=0

#############################################################################################################################################################################



popup_win = popup('Acquire Signal Level...')
while True:             
    event, values =  _VARS['window'].read(timeout=0.5)
#############################################################Acquire reference signal level   ################################################################################################################

    if event =='Sig':
        popup_win.close()
        w,s,sig=get_spectrum(int_time,dev0)
        
        sig=sig+1.5

        _VARS['window']['Sig'].update(disabled=True)  

#############################################################################################################################################################################
    
    wavelength,spectrum ,sl=get_spectrum(int_time,dev0)#Obtain signal strength continuously
    
#############################################################  Accumulation and Decision making ################################################################################################################

    if(detector_lock==False and sl<sig):
                new_value = max(countHighestConfidence, key=countHighestConfidence.get)
                print(new_value)
                end=time.time()-start
                
                
                countHighestConfidence={"Others":0,"HDPE":0,"HDPE":0,"PP":0,"PET":0,"PS":0}

                detector_lock=True
#############################################################  Collection and soft decision  ################################################################################################################

    if(sig!=0 and sl>sig):
            start=time.time()
             
            spectrum=signal.detrend(spectrum)
          
            res = {(wavelength[i]): [(spectrum[i])] for i in range(len(wavelength))}    #1.spectrum collected

            res= pd.DataFrame.from_dict(res)

            AI_result, decisionConfidence=analyse(res)                          #2.call model and analyse

            decisionConfidence=float(decisionConfidence.strip("%"))

           
            if(1<=int(AI_result)<=6):
                    plasticKind = DICTIONARY_PLASTIC_KINDS[int(AI_result)]      #3.Collating the soft-decision    
                    if countHighestConfidence[str(plasticKind)]<decisionConfidence:
                            countHighestConfidence[str(plasticKind)]=decisionConfidence
                            detector_lock=False

    if event in (sg.WIN_CLOSED, 'Close'):
        _VARS['window'].close()
        sys.exit(2)
        dev0.USB2_EndThread()
        break


_VARS['window'].close()
sys.exit(2)

