'''
This script is used to plot the results of the simulations performed in the Nordic 45 system.
The script uses the utility functions defined in the utility_functions_NJ.py file to plot the results.
The results are stored in the folder 'Results' folder at the highest level in this work enviroment.
The results are stored in .json files, which are read and plotted using the functions in the utility_functions_NJ.py file.
'''
if __name__ == '__main__':  
    import sys
    #from config import system_path
    system_path = "/Users/theathormodsen/Library/Mobile Documents/com~apple~CloudDocs/Masteroppgave/Kode og simulering/TOPS_low_inertia_Thea"
    sys.path.append(system_path)
    import utility_functions_NJ as uf
    import matplotlib.pyplot as plt
    import matplotlib.font_manager as fm

    # Set the font properties for the plots
    plt.rcParams.update({
        "font.family": "Dejavu serif",
        "font.serif": ["Computer Modern Roman"],
        "font.size": 14,           # Default font size
        "axes.titlesize": 14,      # Font size for axes titles
        "axes.labelsize": 14,      # Font size for x and y labels
        "xtick.labelsize": 12,     # Font size for x tick labels
        "ytick.labelsize": 12,     # Font size for y tick labels
        "legend.fontsize": 12,     # Font size for legend
        "figure.titlesize": 16     # Font size for figure title
    })
    '''
    The system_path variable is used to define the path to the system folder.
    The subfolder of Results are a folder containing the different result .json files.
    '''
    # folder_path = system_path + 'Results/Real inertia vs SI/'
    #folder_path = system_path + '/results/Summary/'
    #folder_path= system_path + '/results/ramp_down_tests/'
    folder_path= system_path + '/results/SC/'

    # The results and file_names variables are used to store the results and file names of the .json files in the folder.
    results, file_names = uf.format_results(folder_path)

    # Print available loads in first result file
    print("\nAvailable loads in results:")
    if len(results) > 0 and 'load_name' in results[0]:
        print(results[0]['load_name'][0])
    else:
        print("No load names found in results")
    '''
    Available loads in results:
    ['L3000-1', 'L3000-2', 'L3000-3', 'L3020-1', 'L3100-1', 'L3115-1', 'L3249-1', 'L3300-1', 'L3300-2', 'L3359-1',
     'L3359-2', 'L3359-3', 'L3359-4', 'L3360-1', 'L5120-1', 'L5120-2', 'L5120-3', 'L5210-1', 'L5210-2', 'L5220-1',
     'L5231-1', 'L5240-1', 'L5270-1', 'L5310-1', 'L5320-1', 'L5320-2', 'L5321-1', 'L5420-1', 'L5430-1', 'L5431-1',
     'L5530-1', 'L5560-1', 'L5560-2', 'L7000-1', 'L7000-2', 'L7000-3', 'L7000-4', 'L7000-5', 'L7010-1', 'L7020-2',
     'L7100-1', 'L7100-2', 'L8500-1', 'L8500-2', 'L8500-3', 'L8600-1', 'L8600-2', 'L8700-1']

     This is all the loads available when simulating the Nordic 45 system with the current model setup. 
     There is no L5240-2 which I want as that is the NSL load.

    5.11.2025
    Available loads in results:
    ['L3000-1', 'L3000-2', 'L3000-3', 'L3020-1', 'L3100-1', 'L3115-1', 'L3249-1', 'L3300-1', 'L3300-2', 'L3359-1',
    'L3359-2', 'L3359-3', 'L3359-4', 'L3360-1', 'L5120-1', 'L5120-2', 'L5120-3', 'L5210-1', 'L5210-2', 'L5220-1',
    'L5231-1', 'L5240-1', 'L5240-2', 'L5270-1', 'L5310-1', 'L5320-1', 'L5320-2', 'L5321-1', 'L5420-1', 'L5430-1',
    'L5431-1', 'L5530-1', 'L5560-1', 'L5560-2', 'L7000-1', 'L7000-2', 'L7000-3', 'L7000-4', 'L7000-5', 'L7010-1',
    'L7020-2', 'L7100-1', 'L7100-2', 'L8500-1', 'L8500-2', 'L8500-3', 'L8600-1', 'L8600-2', 'L8700-1']
    '''
    

    '''
    The plot functions are used to plot the results of the simulations. 
    There are several different plot functions, each used to plot different results.
    Below are some examples of the plot functions that can be used, and their initialization.
    '''
    
    #uf.plot_freq(results, file_names, scenario = 'NordLink')
    # uf.plot_freq(results, file_names)
    # uf.plot_freq(results, file_names,rocof=True)
    # uf.plot_freq(results, file_names, gen='G5230-1',rocof=True)
    # uf.plot_freq(results, file_names, gen='G7000-1',scenario='NordLink')
    #uf.plot_power_load(results, file_names,load_name='L5240-2')
    # uf.plot_voltage(results, file_names, complex(5110,0))
    # results, file_names = uf.format_results(folder_path2)
    # uf.plot_freq(results, file_names)
    # uf.plot_gen(results, file_names)
    #uf.plot_gen_power(results, file_names, 'G5120-1')
    # uf.plot_gen_power(results, file_names, 'SC5230-1')
    # uf.plot_gen_power(results, file_names, 'SC5230-2')
    # uf.plot_gen_power(results, file_names, 'SC5240-1')
    # uf.plot_gen_speed(results, file_names, 'G5240-1')
    # uf.plot_gen_speed(results, file_names, 'G7000-1')
    # uf.plot_gen_speed(results, file_names, 'G7100-1')
    # uf.plot_load_freq(results, file_names, 'L5120-1')
    # uf.plot_load_rocof(results, file_names, 'L5120-1')
    # uf.plot_VSC_freq(results, file_names, 'WG5120-1')
    # uf.plot_VSC_rocof(results, file_names, 'WG5230-1')
    # uf.plot_power_VSC(results, file_names, 'WG5230-1')
    # uf.plot_VSC_rocof(results, file_names, 'NO_2-GB')
    # uf.plot_power_VSC(results, file_names, 'WG3000-1')
    # uf.plot_power_VSC(results, file_names, 'WG5120-1')
    # uf.plot_power_VSC(results, file_names, 'WG7000-1')
    # uf.plot_power_VSC(results, file_names, 'FI-EE')
    uf.plot_power_VSC(results, file_names, 'NO_2-GB')
    # uf.plot_power_VSC(results, file_names, 'NO_2-DE')
    # uf.plot_power_VSC(results, file_names, 'SE_4-LT')
    # uf.plot_line_p(results, file_names, 'L3359-5110')
    # uf.plot_trafos_p(results, file_names, 'T5130-5320')

    # uf.plot_power_VSC(results, file_names, 'WG3000-1')
    # uf.plot_power_VSC(results, file_names, 'WG3000-2')
    # uf.plot_power_VSC(results, file_names, 'WG3100-1')
    # uf.plot_power_VSC(results, file_names, 'WG3100-2')
    # uf.plot_power_VSC(results, file_names, 'WG3100-3')
    plt.show()