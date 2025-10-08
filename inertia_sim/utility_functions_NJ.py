'''
This script contains utility functions for processing and plotting simulation results.
It includes functions to read and format results from JSON files, plot various system parameters such as generator power, frequency, voltage, and load power, and import data from Excel files.
The script is designed to work with the Nordic 45 system and includes functions for plotting results from different scenarios, including generator trips and power flow data.
The script also includes functions to plot the different results of VSC power.
The implementation of the plotting functions is done in the Plot_n45.py script.
'''


""" THEA: 
I get KeyError: 't' which I think is the reason why the plotting doesn't work. Tried to comment in line
195-198 but then I get the KeyError: 'gen_speed'. Have to find out what this bug is.
"""

import numpy as np 
import matplotlib.pyplot as plt
from matplotlib import rcParams
from pathlib import Path
import json
import pandas as pd 
import os


def read_to_file(result, file_path):
    """
    Reads the results to a .json files.

    Parameters:
    results : dictionary
        Dictionary containing simulation results.
    file_path : string  
        Path to save the file.

    """

    for key, value in result.items():
        for i, item in enumerate(value):
            if isinstance(item, np.ndarray): #check if item is a numpy array
                result[key][i] = item.tolist()
    
    #Convert complex numbers to strings
    for key, value in result.items():
        try:
            if (isinstance(value[0][0], complex)): #check if item is a complex number
                result[key] = [[str(x) for x in sublist] for sublist in value] #convert complex numbers to strings
        except:
            pass
    
    with open(file_path, 'w') as file:
        json.dump(result, file, indent=4)
    
    print('Results saved to:', file_path)




def format_results(path):
    """
    Reads and formats the results from .json files in a folder.

    Parameters:
    path : string
        Path to the folder containing simulation results.
    """

    results = []
    file_names = []

    #Open all json files in the folder
    folder_path = Path(path)

    for file in sorted(folder_path.iterdir()):
        if file.suffix == '.json':
            with open(file, 'r') as f:
                results.append(json.load(f)) 
                file_names.append(file)
    
    
    #Format complex strings to complex values
    for res in results:
        for key, list in res.items(): 
            try:
                res[key] = [[complex(x) for x in sublist] for sublist in list]
            except:
                pass
    return results, file_names

def plot_gen_power(results, file_names, gen_name=None):
    """
    Plot generator power output results from simulation.

    Parameters:
    results : list of dictionaries
        List of dictionaries containing simulation results.
    file_names : list of strings
        List of file names.
     gen_name : string, optional
        Name of the generator to plot. If None, plot all generators.
    """
    plt.figure()
    it = 0   
    for res in results:
        if gen_name is not None:
            if gen_name in res['gen_name'][0]:
                plt.plot(res['t'], np.array(res['gen_P'])[:, res['gen_name'][0].index(gen_name)], label=gen_name+' ' + file_names[it].stem)
            it += 1
        else:
            for gen in res['gen_name']:
                plt.plot(res['t'], np.array(res['gen_P'])[:, res['gen_name'].index(gen)], label=gen)
    plt.xlim(10, max(res['t']))  # Start x-axis at 10s
    plt.xlabel('Time [s]')
    plt.ylabel('Power [MW]')
    plt.grid()
    plt.legend()


def import_powerflow_data(path):
    """
    Retrievies data from .xlsx files

    Parameter:
    path : string
        String to folder path 
    """
  
    # Reading the aggregated generation data from excel file
    ENTSOE_gen_data = pd.read_excel(
        path + 'dataframes_transparency.xlsx', sheet_name='Aggr_generation', index_col=0)
    # Reading the aggregated load data from excel file
    ENTSOE_load_data = pd.read_excel(
        path + 'dataframes_transparency.xlsx', sheet_name='Aggr_load', index_col=0)

    # Reading the aggregated exchange data from excel file (power links)
    ENTSOE_exchange_data = pd.read_excel(
        path + 'powerflow_Statnett.xlsx', sheet_name='aggr_exchange', index_col=0)
    return ENTSOE_gen_data, ENTSOE_load_data, ENTSOE_exchange_data



def plot_freq(results, file_names, rocof=False, scenario = None, gen = None):
    """
    Plot frequency results from simulation.

    Parameters:
    results : list of dictionaries
        List of dictionaries containing simulation results.
    rocof : bool, optional
        If True, plot ROCOF. Default is False.

    """
    plt.rcParams.update({

        "font.family": "Dejavu serif",

        "font.serif": ["Computer Modern Roman"],
        "font.size": 12,           # Default font size
        "axes.titlesize": 14,      # Font size for axes titles
        "axes.labelsize": 14,      # Font size for x and y labels
        "xtick.labelsize": 12,     # Font size for x tick labels
        "ytick.labelsize": 12,     # Font size for y tick labels
        "legend.fontsize": 12,     # Font size for legend
        "figure.titlesize": 16     # Font size for figure title
    })

    #Plot frequency
    if gen is not None:
        plt.figure()
        it = 0
        for res in results:
            gen_index = res['gen_name'][0].index(gen)
            if file_names[it].stem[0] == '0':
                plt.plot(res['t'], 50 + 50*np.array(res['gen_speed'])[:,gen_index], label = file_names[it].stem[1:])
            else:
                plt.plot(res['t'], 50 + 50*np.array(res['gen_speed'])[:,gen_index], label = file_names[it].stem)
            it += 1
        if scenario == 'NordLink':
            #This is used to plot the real frequency data from the NordLink case
            from plot_NordLink_data import import_NordLink_data
            #from config import system_path
            system_path = "/Users/theathormodsen/Library/Mobile Documents/com~apple~CloudDocs/Masteroppgave/Kode og simulering/TOPS_low_inertia_Thea"
            path = system_path+'inertia_sim/N45_case_data_NordLink/Case-Norlink.xlsx'
            data = import_NordLink_data(path)


            # Check if the necessary columns exist
            required_columns = ['Timestamp', 'Frequency: FI', 'Frequency: NO1', 'Frequency: NO2', 'Frequency: NO3']
            if not all(col in data.columns for col in required_columns):
                print("Error: Required columns are missing from the data.")
            else:
                data['mean_freq'] = data[['Frequency: FI', 'Frequency: NO1', 'Frequency: NO2', 'Frequency: NO3']].mean(axis=1)
                plt.plot(data['Seconds'], data['Frequency: FI'], label='Real data')

    else:
        plt.figure()
        it = 0  
        for res in results:
            #freq =[]
            #for timestep in res['gen_speed']:
            #     freq.append(50 + 50*timestep[-6])
            #plt.plot(res['t'], freq, label = file_names[it].stem)
            if file_names[it].stem[0] == '0':
                plt.plot(res['t'], 50 + 50*np.mean(res['gen_speed'], axis=1), label = file_names[it].stem[1:])
            else:
                plt.plot(res['t'], 50 + 50*np.mean(res['gen_speed'], axis=1), label = file_names[it].stem)
            it += 1

        if scenario == 'NordLink':
            #This is used to plot the real frequency data from the NordLink case
            from plot_NordLink_data import import_NordLink_data
            #from config import system_path
            system_path = "/Users/theathormodsen/Library/Mobile Documents/com~apple~CloudDocs/Masteroppgave/Kode og simulering/TOPS_low_inertia_Thea"
            path = system_path+'inertia_sim/N45_case_data_NordLink/Case-Norlink.xlsx'
            data = import_NordLink_data(path)


            # Check if the necessary columns exist
            required_columns = ['Timestamp', 'Frequency: FI', 'Frequency: NO1', 'Frequency: NO2', 'Frequency: NO3']
            if not all(col in data.columns for col in required_columns):
                print("Error: Required columns are missing from the data.")
            else:
                data['mean_freq'] = data[['Frequency: FI', 'Frequency: NO1', 'Frequency: NO2', 'Frequency: NO3']].mean(axis=1)
                plt.plot(data['Seconds'], data['Frequency: FI'], label='Real data')
                # plt.plot(data['Seconds'], data['Frequency: NO1'], label='NO1')
                # plt.plot(data['Seconds'], data['Frequency: NO2'], label='NO2')
                # plt.plot(data['Seconds'], data['Frequency: NO3'], label='NO3')
                # plt.plot(data['Seconds'], data['mean_freq'], label='Average frequency')
    # #Add a dotted line at 49.1 Hz
    # plt.axhline(y=49.1, color='r', linestyle='--', label='49.1 Hz')

    plt.xlim(10, max(res['t']))  # Start x-axis at 10s
    plt.xlabel('Time [s]')
    plt.ylabel('Frequency [Hz]')
    plt.grid()  
    plt.legend()

    #Plot ROCOF
    if rocof:
        plt.figure()
        it = 0   
        if gen is not None:
            for res in results:

                gen_index = res['gen_name'][0].index(gen)
                if file_names[it].stem[0] == '0':
                    plt.plot(res['t'], np.gradient(50 + 50*np.array(res['gen_speed'])[:,gen_index], res['t']), label = file_names[it].stem[1:])
                    it += 1
                else:
                    plt.plot(res['t'], np.gradient(50 + 50*np.array(res['gen_speed'])[:,gen_index], res['t']), label = file_names[it].stem)
                    it += 1
        else:
            for res in results:
                if file_names[it].stem[0] == '0':
                    plt.plot(res['t'], np.gradient(50 + 50*np.mean(res['gen_speed'], axis=1), res['t']), label = file_names[it].stem[1:])
                    it += 1
                else:
                    plt.plot(res['t'], np.gradient(50 + 50*np.mean(res['gen_speed'], axis=1), res['t']), label = file_names[it].stem)
                    it += 1
        plt.xlim(10, max(res['t']))  # Start x-axis at 10s
        plt.xlabel('Time [s]')
        plt.ylabel('ROCOF [Hz/s]')
        plt.grid()
        plt.legend()
            



    return None

def plot_power_VSC(results, file_names, VSC_name):
    """
    Plot power and voltage results from simulation.

    Parameters:
    results : list of dictionaries
        List of dictionaries containing simulation results.
    file_names : list of strings
        List of file names.
    VSC_name : string
        Name of the VSC to plot.
    """
    plt.figure()
    index = 0
    for name in results[0]['VSC_name'][0]:
        if(name == VSC_name):
            break
        else:
            index += 1
    it = 0
    
    for res in results:
        #multpliying be VSC Sn to get the power in MW
        power = np.array(res['VSC_p'])[:, index] * res['VSC_Sn'][0][index]
        plt.plot(res['t'], power, label = file_names[it].stem)
        # plt.plot(res['t'], ([row[index] for row in res['VSC_p']]), label = file_names[it].stem)# label = res['VSC_name'][0][index]+' '+file_names[i].stem)
        it += 1
    plt.xlim(10, max(res['t']))  # Start x-axis at 10s
    plt.xlabel('Time [s]')
    plt.legend()
    plt.ylabel('Power [MW]')
    #plt.title(f'Active power output from {res['VSC_name'][0][index]}')
    plt.grid()
def plot_load_freq(results, file_names, load_name):
    """
    Plot load frequency results from simulation.

    Parameters:
    results : list of dictionaries
        List of dictionaries containing simulation results.
    file_names : list of strings
        List of file names.
    load_name : string
        Name of the load to plot.
    """
    plt.figure()
    it = 0
    for res in results:
        plt.plot(res['t'], np.array(res['load_freq'])[:, res['load_name'][0].index(load_name)], label=load_name+' ' + file_names[it].stem)
        it += 1
    plt.xlim(10, max(res['t']))  # Start x-axis at 10s
    plt.xlabel('Time [s]')
    plt.ylabel('Frequency [Hz]')
    plt.grid()
    plt.legend()


def plot_load_rocof(results, file_names, load_name):
    """
    Plot load ROCOF results from simulation.

    Parameters:
    results : list of dictionaries
        List of dictionaries containing simulation results.
    file_names : list of strings
        List of file names.
    load_name : string
        Name of the load to plot.
    """
    plt.figure()
    it = 0
    for res in results:
        plt.plot(res['t'], np.array(res['load_rocof'])[:, res['load_name'][0].index(load_name)], label=load_name+' ' + file_names[it].stem)
        it += 1
    plt.xlim(10, max(res['t']))  # Start x-axis at 10s
    plt.xlabel('Time [s]')
    plt.ylabel('Rocof [Hz/s]')
    plt.grid()
    plt.legend()


def plot_VSC_freq(results, file_names, VSC_name):
    """
    Plot VSC frequency results from simulation.

    Parameters:
    results : list of dictionaries
        List of dictionaries containing simulation results.
    file_names : list of strings
        List of file names.
    VSC_name : string
        Name of the VSC to plot.
    """
    plt.figure()
    index = 0
    for name in results[0]['VSC_name'][0]:
        if(name == VSC_name):
            break
        else:
            index += 1
    it = 0
    
    for res in results:
        
        plt.plot(res['t'], np.array(res['VSC_freq'])[:, index], label = file_names[it].stem)
        it += 1
    plt.xlim(10, max(res['t']))  # Start x-axis at 10s
    plt.xlabel('Time [s]')
    plt.legend()
    plt.ylabel('Frequency [Hz]')
    plt.grid()


def plot_VSC_rocof(results, file_names, VSC_name):
    """
    Plot VSC ROCOF results from simulation.

    Parameters:
    results : list of dictionaries
        List of dictionaries containing simulation results.
    file_names : list of strings
        List of file names.
    VSC_name : string
        Name of the VSC to plot.
    """
    plt.figure()
    index = 0
    for name in results[0]['VSC_name'][0]:
        if(name == VSC_name):
            break
        else:
            index += 1
    it = 0
    
    for res in results:
        plt.plot(res['t'], np.array(res['VSC_rocof'])[:, index], label = file_names[it].stem)
        it += 1
    plt.xlim(10, max(res['t']))  # Start x-axis at 10s
    plt.xlabel('Time [s]')
    plt.legend()
    plt.ylabel('Rocof [Hz/s]')
    plt.grid()

  
def plot_gen_speed(results, file_names, gen_name=None):
    """
    Plot generator speed results from simulation.

    Parameters:
    results : list of dictionaries
        List of dictionaries containing simulation results.
    file_names : list of strings
        List of file names.
    gen_name : string, optional
        Name of the generator to plot. If None, plot all generators.
    """
    plt.figure()
    it = 0   
    for res in results:
        if gen_name is not None:
            plt.plot(res['t'], np.array(res['gen_speed'])[:, res['gen_name'][0].index(gen_name)], label=gen_name+' ' + file_names[it].stem)
            it += 1
        else:
            for gen in res['gen_name']:
                plt.plot(res['t'], np.array(res['gen_speed'])[:, res['gen_name'].index(gen)], label=gen)
    plt.xlabel('Time [s]')
    plt.ylabel('Speed [p.u.]')
    plt.grid()
    plt.legend()

 
def plot_power_load(results, file_names, load_name=None):
    plt.figure()
    it = 0
    for res in results:
        if load_name is not None:
                plt.plot(res['t'], np.array(res['load_P'])[:, res['load_name'][0].index(load_name)], label=load_name + ' ' + file_names[it].stem)
                it += 1
        else:
            for load in res['load_name'][0]:
                plt.plot(res['t'], np.array(res['load_P'])[:, res['load_name'][0].index(load)], label=load)
    plt.xlim(10, max(res['t']))  # Start x-axis at 10s
    plt.xlabel('Time [s]')
    plt.ylabel('Power [MW]')
    plt.grid()
    plt.legend()


def plot_voltage(results, file_names, bus_name=None):
    '''
    Initialization of the plot
    uf.plot_voltage(results, file_names, complex(5310,0))
    This is for the bus 5310 as the bus_name is complex for whatever reason
    '''
    plt.figure()
    it = 0
    for res in results:
        if bus_name is not None:
            #absolute value of every entry of nested list res['v] at the index of bus_name
            v = np.array(res['v'])[:, res['bus_names'][0].index(bus_name)]
            #taking the absolute value of the complex number
            v = [abs(complex(x)) for x in v]


            plt.plot(res['t'], v, label=str(bus_name) + ' ' + file_names[it].stem)
            it += 1
        else:
            for bus in res['bus_names'][0]:
                plt.plot(res['t'], np.array(res['v'])[:, res['bus_names'][0].index(bus)], label=bus)
    plt.xlim(10, max(res['t']))  # Start x-axis at 10s
    plt.xlabel('Time [s]')
    plt.ylabel('Voltage [p.u.]')
    plt.grid()
    plt.legend()


def plot_local_freq(results, file_names, load_name, gen_name,  mean_freq = False):
    plt.figure()
    it = 0
    for res in results:
        plt.plot(res['t'], np.array(res['freq_est'])[:, res['load_name'][0].index(load_name)], label=load_name+' ' + file_names[it].stem)
    
        if gen_name is not None:
            plt.plot(res['t'], 50 +  50*np.array(res['gen_speed'])[:, res['gen_name'][0].index(gen_name)], label=gen_name+' ' + file_names[it].stem)
        it += 1
    if mean_freq == True:
        plt.plot(res['t'], 50 + 50*np.mean(res['gen_speed'], axis=1),label = 'mean_freq')
    plt.xlim(10, max(res['t']))  # Start x-axis at 10s
    plt.xlabel('Time [s]')
    plt.ylabel('Freq [Hz]')
    plt.grid()
    plt.legend()


def plot_local_freq_test(results, file_names, load_name, gen_name,  mean_freq = False):
    plt.figure()
    it = 0
    for res in results:
        #plt.plot(res['t'], np.array(res['freq_est_omega'])[:, res['load_name'][0].index(load_name)], label='omega ' + load_name+' ' + file_names[it].stem)
        plt.plot(res['t'], np.array(res['freq_est_delta_omega'])[:, res['load_name'][0].index(load_name)], label='delta omega ' + load_name+' ' + file_names[it].stem)
        it += 1
    if gen_name is not None:
        res = results[0]
        plt.plot(res['t'], 50 +  50*np.array(res['gen_speed'])[:, res['gen_name'][0].index(gen_name)], label=gen_name)
        
    if mean_freq == True:
        plt.plot(res['t'], 50 + 50*np.mean(res['gen_speed'], axis=1),label = 'mean_freq')
    plt.xlim(10, max(res['t']))  # Start x-axis at 10s
    plt.xlabel('Time [s]')
    plt.ylabel('Freq [Hz]')
    plt.grid()
    plt.legend()


def plot_line_p(results, file_names, line_name):
    """
    Plot line power results from simulation.

    Parameters:
    results : list of dictionaries
        List of dictionaries containing simulation results.
    file_names : list of strings
        List of file names.
    line_name : string
        Name of the line to plot.
    """
    base_mva = 1000
    plt.figure()
    it = 0
    for res in results:
        idx = []
        i = 0
        for line in res['line_names'][0]:
            if line == line_name:
                idx.append(i)
            i += 1
        i=0  
        #to only plot one line  
        idx = res['line_names'][0].index(line_name)
        if file_names[it].stem[0] == '0':
            plt.plot(res['t'], np.array(res['line_P'])[:, idx]*base_mva, label=line_name + ' ' + file_names[it].stem[1:])
            it+= 1
        else:
            plt.plot(res['t'], np.array(res['line_P'])[:, idx]*base_mva, label=line_name + ' ' + file_names[it].stem)
            it += 1
    
    plt.xlim(10, 20)  # Start x-axis at 10s
    plt.xlabel('Time [s]')
    plt.ylabel('Power [MW]')
    
    plt.grid()  
    plt.legend()
    


def plot_trafos_p(results, file_names, trafo_name):
    """
    Plot transformer power results from simulation.

    Parameters:
    results : list of dictionaries
        List of dictionaries containing simulation results.
    file_names : list of strings
        List of file names.
    trafos : string
        Name of the transformer to plot.
    """
    base_mva = 1000
    plt.figure()
    it = 0
    for res in results:
        idx = []
        i = 0
        #to only plot one line  
        idx = res['trafos_names'][0].index(trafo_name)
        plt.plot(res['t'], np.array(res['transformer_P'])[:, idx]*base_mva, label=trafo_name + ' ' + file_names[it].stem)
        it += 1
    plt.xlim(10, 20)  # Start x-axis at 10s
    plt.xlabel('Time [s]')
    plt.ylabel('Power [MW]')
    plt.grid()  
    plt.legend()