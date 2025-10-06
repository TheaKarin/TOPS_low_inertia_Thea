'''
The script is used to simulate a fault on the NorLink cable, which leads to a fault of 1675MW.
This should be seen in combination with the script init_N45.py, which is used to initialize the Nordic 45 system.
'''



if __name__ == '__main__':
    import sys
    sys.path.append('/Users/theathormodsen/Library/Mobile Documents/com~apple~CloudDocs/Masteroppgave/Kode og simulering/TOPS_low_inertia_Thea/src')
    #This code is used to generate a fault on the NorLink cable and test the system response.
    #The fault is a reversal of power flow on the cable, which leads to a fault of 1675MW. 
    import init_N45 as init
    import fault_events as fault
    import tops.ps_models.n45_2_0 as n45

    '''
    The energy mix for the different countries in the Nordic 45 system is defined below.
    The two different energy mixes are used to simulate the system in two different scenarios.
    The first scenario is the energy mix for 2023 case.
    The second scenario is the energy mix for 2030 worst case scenario.
    '''

    #Energy mix for Nordlink 
    energy_mix_NordLink = {'FI': {'Wind': 0.218, 'Hydro': 0.334, 'Nuclear': 0.448, 'Solar': 0.0, 'Fossil': 0.0},
                'NO_1': {'Wind': 0.083, 'Hydro': 0.917, 'Nuclear': 0.0, 'Solar': 0.0, 'Fossil': 0.0},
                'NO_2': {'Wind': 0.084, 'Hydro': 0.916, 'Nuclear': 0.0, 'Solar': 0.0, 'Fossil': 0.0},
                'NO_3': {'Wind': 0.140, 'Hydro': 0.860, 'Nuclear': 0.0, 'Solar': 0.0, 'Fossil': 0.0},
                'NO_4': {'Wind': 0.139, 'Hydro': 0.861, 'Nuclear': 0.0, 'Solar': 0.0, 'Fossil': 0.0},
                'NO_5': {'Wind': 0.0, 'Hydro': 1.0, 'Nuclear': 0.0, 'Solar': 0.0, 'Fossil': 0.0},
                'SE_1': {'Wind': 0.158, 'Hydro': 0.842, 'Nuclear': 0.0, 'Solar': 0.0, 'Fossil': 0.0},
                'SE_2': {'Wind': 0.212, 'Hydro': 0.788, 'Nuclear': 0.0, 'Solar': 0.0, 'Fossil': 0.0},
                'SE_3': {'Wind': 0.233, 'Hydro': 0.195, 'Nuclear': 0.572, 'Solar': 0.0, 'Fossil': 0.0},
                'SE_4': {'Wind': 0.8, 'Hydro': 0.2, 'Nuclear': 0, 'Solar': 0.0, 'Fossil': 0.0}}
    #Energy mix for 2030 worst case scenario
    energy_mix_2030 = {'FI': {'Wind': 0.7, 'Hydro': 0.1, 'Nuclear': 0.2, 'Solar': 0.0, 'Fossil': 0.0},
                'NO_1': {'Wind': 0.5, 'Hydro': 0.5, 'Nuclear': 0.0, 'Solar': 0.0, 'Fossil': 0.0},
                'NO_2': {'Wind': 0.4, 'Hydro': 0.6, 'Nuclear': 0.0, 'Solar': 0.0, 'Fossil': 0.0},
                'NO_3': {'Wind': 0.4, 'Hydro': 0.6, 'Nuclear': 0.0, 'Solar': 0.0, 'Fossil': 0.0},
                'NO_4': {'Wind': 0.5, 'Hydro': 0.5, 'Nuclear': 0.0, 'Solar': 0.0, 'Fossil': 0.0},
                'NO_5': {'Wind': 0.0, 'Hydro': 1.0, 'Nuclear': 0.0, 'Solar': 0.0, 'Fossil': 0.0},
                'SE_1': {'Wind': 0.95, 'Hydro': 0.05, 'Nuclear': 0.0, 'Solar': 0.0, 'Fossil': 0.0},
                'SE_2': {'Wind': 0.95, 'Hydro': 0.05, 'Nuclear': 0.0, 'Solar': 0.0, 'Fossil': 0.0},
                'SE_3': {'Wind': 0.6, 'Hydro': 0.0, 'Nuclear': 0.4, 'Solar': 0.0, 'Fossil': 0.0},
                'SE_4': {'Wind': 0.95, 'Hydro': 0.05, 'Nuclear': 0.0, 'Solar': 0.0, 'Fossil': 0.0}}


    '''
    The init_n45 function is used to initialize the Nordic 45 system.
    The function takes the following parameters:
    - model_data: The model data for the Nordic 45 system.
    - energy_mix: The energy mix for the different countries in the Nordic 45 system.
    - data_path: The path to the data files for the Nordic 45 system.
    - spinning_reserve: The spinning reserve for the Nordic 45 system.
    The function returns a PowerSystem object, which is used to perform the simulations.
    '''
    # ps = init.init_n45(model_data=n45,energy_mix= energy_mix_NordLink, 
    #                    data_path= 'inertia_sim/N45_case_data_Nordlink/',
    #                 #    kinetic_energy_eps= 50e3,
    #                    spinning_reserve=1.2)
    ps = init.init_n45(model_data=n45,energy_mix= energy_mix_2030, 
                        data_path= 'inertia_sim/2030_scenario/',
                        spinning_reserve=1.2)
    
    '''
    The HVDC_cable_trip function is used to simulate a fault on the NorLink cable.
    The function comes from the fault_events.py file.
    The function takes the following parameters:
    - ps: The PowerSystem object.
    - folderandfilename: The folder and filename for the results.
    - event_flag: A flag to indicate if the event is a fault or not.
    - FFR_sources: The sources of FFR (Fast Frequency Response) in the system.
    The function simulates a fault on the NorLink cable and stores the results in the specified folder and filename as a .json file.
    There has to be a folder with the same name as the first part of folderandfilename in the Results folder.
    '''
    fault.HVDC_cable_trip(ps=ps,folderandfilename = 'SC/3x150MVA',
                            event_flag=True)
    # fault.HVDC_cable_trip(ps=ps,folderandfilename = 'Frequency support from Wind activation time/49.5Hz activation', 
    #                         event_flag=True, FFR_sources=['WG3000-1','WG5120-1','WG7000-1'])
    # fault.HVDC_cable_trip(ps=ps,folderandfilename = 'FFR/300 MW', 
    #                         event_flag=True,FFR_sources=['L3000-1','L3359-1','L3249-1','L5120-1','L5270-1','L5560-1','L7000-1','L7100-1','L8500-1'])
    # fault.HVDC_cable_trip(ps=ps,folderandfilename = 'Frequency support from Wind/450 MW', 
    #                         event_flag=True, FFR_sources=['WG3000-1','WG3359-1','WG3249-1','WG5120-1','WG5230-1','WG5321-1','WG7000-1','WG7100-1','WG8500-1'])

