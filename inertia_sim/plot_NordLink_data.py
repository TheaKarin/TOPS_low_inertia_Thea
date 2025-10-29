import pandas as pd 
import matplotlib.pyplot as plt
import sys
from config import system_path
sys.path.append(system_path)


def import_NordLink_data(path):
    """
    Imports the NordLink data from a .xlsx file.
    
    Parameters:
    path : string
        Path to the .xlsx file.
    """

    data = pd.read_excel(path, sheet_name='Utfall-NordLink-2023-02-17-v2')
    print('Successfully imported NordLink data.')

    # Convert 'Timestamp' column to datetime
    data['Timestamp'] = pd.to_datetime(data['Timestamp'])

    # Starting the time from 0
    start_time = data['Timestamp'].iloc[0]
    data['Seconds'] = (data['Timestamp'] - start_time).dt.total_seconds()

    return data

if __name__ == '__main__':


    path = system_path+'inertia_sim/N45_case_data_NordLink/Case-Norlink.xlsx'
    data = import_NordLink_data(path)

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


    # Check if the necessary columns exist
    required_columns = ['Timestamp', 'Frequency: FI', 'Frequency: NO1', 'Frequency: NO2', 'Frequency: NO3']
    if not all(col in data.columns for col in required_columns):
        print("Error: Required columns are missing from the data.")
    else:
        data['mean_freq'] = data[['Frequency: FI', 'Frequency: NO1', 'Frequency: NO2', 'Frequency: NO3']].mean(axis=1)
        plt.figure()
        plt.plot(data['Seconds'], data['Frequency: FI'], label='FI')
        plt.plot(data['Seconds'], data['Frequency: NO1'], label='NO1')
        plt.plot(data['Seconds'], data['Frequency: NO2'], label='NO2')
        plt.plot(data['Seconds'], data['Frequency: NO3'], label='NO3')
        plt.plot(data['Seconds'], data['mean_freq'], label='Average frequency')
        plt.title('NordLink Fault Frequency Data')
        plt.xlabel('Seconds')
        plt.ylabel('Frequency [Hz]')
        plt.legend()
        plt.grid()
        plt.show()


