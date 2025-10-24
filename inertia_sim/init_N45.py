'''
This script is used to initialize the Nordic 45 system.
This should be seen in combination with the trip_2030.py script, which is used to simulate a fault on the NorLink cable.
'''



import sys
from collections import defaultdict
import time

from config import system_path
sys.path.append(system_path)  # Corrected path to dyn_sim module

import tops.dynamic as dps
import tops.solvers as dps_sol
import importlib
importlib.reload(dps)


import utility_functions_NJ as uf
import tops.utility_functions_eirik as MThesis


import pandas as pd
import numpy as np 




def init_n45(model_data, data_path, energy_mix,display_pf=False, fault_bus = '7000',fault_Sn = 1400,fault_P = 1400,kinetic_energy_eps = None,virtual_gen = False, spinning_reserve = 1.2):

    """
    Initializes the Nordic 45 system from "N45_case_data" folder with the specified fault bus, fault Sn, fault P and kinetic energy of the EPS.

    Parameters:
    model_data : dictionary
        Dictionary containing the model data.
    data_path : str
        Path to the data files for the Nordic 45 system.
    energy_mix : dictionary
        Dictionary containing the energy mix for the different countries in the Nordic 45 system.
    spinning_reserve : float
        The amount of extra power generation that is available to be used in case of a fault.

    Not all parameters are needed, but they are used to set the system up for a specific scenario.
    display_pf : bool
        If True, the power flow is displayed.
    
    kinetic_energy_eps : float
        The kinetic energy of the EPS. It's not necessarily needed, but is used to scale the inertia of the system.

    These parameters are not necessarily needed, only if there should be a disconnection of a generator.
    fault_bus : string
        The bus number of the fault.
    fault_Sn : float
        The nominal power of the fault.
    fault_P : float 
        The active power of the fault.
    virtual_gen : bool
        If True, a virtual generator is added to the system.

    """




    data_path = system_path + data_path
  
    #Accessing the case data and saving it in Dataframe format
    ENTSOE_gen_data, ENTSOE_load_data, ENTSOE_exchange_data = uf.import_powerflow_data(data_path)
    # List of international power links: Should be updated if added links or using another model than N45
    international_links = {'L5230-1': 'NO_2-DE', 'L5240-2': 'NO_2-GB', 'L5210-1': 'NO_2-DK',
                           'L3360-1': 'SE_3-DK', 'L8600-1': 'SE_4-DK', 'L8700-1': 'SE_4-PL',
                           'L8600-2': 'SE_4-DE', 'L8700-2': 'SE_4-LT', 'L7020-1': 'FI-EE',
                           'L3020-1': 'SE_3-FI', 'L7010-1': 'FI-SE_3', 'L5220-1': 'NO_2-NL',
                           'L7020-2': 'FI-RU'}
    #Initializing the model from the load data in n45_with_controls
    model = model_data.load()

    # ------------------------------ Reparameterization to fit specific time-senario -----------------------------------
    index_area = model['buses'][0].index('Area')
    area_mapping = {24: 'SE_4', 23: 'SE_3', 22: 'SE_2', 21: 'SE_1', 11: 'NO_1', 12: 'NO_2', 13: 'NO_3',
        14: 'NO_4', 15: 'NO_5', 31: 'FI'} #integers from original N45, strings from Transparency platform
    #Change from numbers to strings from area_mapping to have consistent area names
    for bus in model['buses'][1:]:
        area = bus[index_area]
        if area in area_mapping:
            bus[index_area] = area_mapping[area]
        else:
            print(f"ERROR: Unknown price area {area}")

    
    # Making dictionary to map bus to area
    area_by_bus = {} #From bus find area
    bus_by_area = {} #From area find buses
    index_bus_name = model['buses'][0].index('name')
    index_area = model['buses'][0].index('Area')
    for bus in model['buses'][1:]:
        area = bus[index_area]
        area_by_bus[bus[index_bus_name]] = area
        if area not in bus_by_area:
            bus_by_area[area] = [bus[index_bus_name]]
        else:
            bus_by_area[area].append(bus[index_bus_name])
    fault_area = area_by_bus.get(fault_bus)



    #------------------------------Updating the Power consumption in the n45_with_controls model-----------------------------------
    PowerCon_by_area = {}
    PowerExc_by_country = {} #Used for scaling when mulitple export/import power links between countries
    index_name = model['loads'][0].index('name')
    index_bus_name = model['loads'][0].index('bus')
    index_P = model['loads'][0].index('P')
    load_sum = 0.0
    added = set() #To not count interconnectors multiple times
    for row in model['loads'][1:]:
        bus_name = row[index_bus_name]
        load_name = row[index_name]
        P_specified = row[index_P]
        area = area_by_bus.get(bus_name)
        load_sum += P_specified
        if load_name not in international_links.keys(): #If load inside model
            if area not in PowerCon_by_area:
                PowerCon_by_area[area] = 0.0
            PowerCon_by_area[area] = PowerCon_by_area[area] + P_specified

        elif load_name in international_links.keys(): #if import/export cable
            transfer_code = international_links[load_name]
            from_count = transfer_code[:2]
            to_count = transfer_code[-2:]
            for other_load_name, other_transfer in international_links.items():
                other_from_count = other_transfer[:2]
                other_to_count = other_transfer[-2:]
                if from_count == other_from_count and to_count == other_to_count \
                        and transfer_code != other_transfer and transfer_code not in added:
                    if from_count not in PowerExc_by_country:
                        PowerExc_by_country[from_count] = 0.0
                    PowerExc_by_country[from_count] = PowerExc_by_country[from_count] + P_specified
                    added.add(transfer_code)
                elif from_count == other_to_count and to_count == other_from_count \
                        and transfer_code != other_transfer and transfer_code not in added:
                    if from_count not in PowerExc_by_country:
                        PowerExc_by_country[from_count] = 0.0
                    PowerExc_by_country[from_count] = PowerExc_by_country[from_count] - P_specified
                    added.add(transfer_code)


    # ------------------------------Updating generators' specified powers----------------------------------------------
    index_bus_name = model['generators']['GEN'][0].index('bus')
    index_gen = model['generators']['GEN'][0].index('name')
    index_P = model['generators']['GEN'][0].index('P')
    index_Sn = model['generators']['GEN'][0].index('S_n')
    
    #Mapping the generators by their means of production
    hydro_gen = []
    for row in model['gov']['HYGOV']:
        if row[0] == 'name':
            continue
        else:
            hydro_gen.append(row[1])
    hydro_gen_by_area = {}
    for row in model['generators']['GEN'][1:]:
        bus_name = row[index_bus_name]
        area = area_by_bus.get(bus_name)
        gen_name = row[index_gen]
        if gen_name in hydro_gen:
            if area not in hydro_gen_by_area:
                hydro_gen_by_area[area] = []
            hydro_gen_by_area[area].append(gen_name)
    nuclear_gen = []
    for row in model['gov']['TGOV1']:
        if row[0] == 'name':
            continue
        else:
            nuclear_gen.append(row[1])
    nuclear_gen_by_area = {}
    for row in model['generators']['GEN'][1:]:
        bus_name = row[index_bus_name]
        area = area_by_bus.get(bus_name)
        gen_name = row[index_gen]
        if gen_name in nuclear_gen:
            if area not in nuclear_gen_by_area:
                nuclear_gen_by_area[area] = []
            nuclear_gen_by_area[area].append(gen_name)
    wind_gen_by_area = {}
    for row in model['vsc']['VSC_SI'][1:]:
        area = area_by_bus.get(row[1])
        if row[0] not in international_links.values():
            if area not in wind_gen_by_area:
                wind_gen_by_area[area] = []
            wind_gen_by_area[area].append(row[0])


   
   
    #Updating the specified power generation for each generation type
    index_Sn = model['generators']['GEN'][0].index('S_n')
    index_P = model['generators']['GEN'][0].index('P')
    for row in model['generators']['GEN'][1:]:
        bus_name = row[index_bus_name]
        area = area_by_bus.get(bus_name)
        gen_name = row[index_gen]
        if gen_name in hydro_gen:
            power = ENTSOE_gen_data['Power generation'].loc[area]*energy_mix[area]['Hydro']/len(hydro_gen_by_area.get(area))  
            # if power > row[index_Sn]:
            #     ValueError(f"Power generation for {gen_name} in {area} is larger than the nominal power")
            row[index_P] = power
            if gen_name == 'G'+model['slack_bus']+'-1':
                continue
            else:
                row[index_Sn] = power*spinning_reserve
            
            # row[index_Sn] = row[index_Sn] * ENTSOE_gen_data['Power generation'].loc[area] / PowerGen_by_area.get(area)
        elif gen_name in nuclear_gen:
            power = ENTSOE_gen_data['Power generation'].loc[area]*energy_mix[area]['Nuclear']/len(nuclear_gen_by_area.get(area))
            # if power > row[index_Sn]:
            #     ValueError(f"Power generation for {gen_name} in {area} is larger than the nominal power")
            if gen_name == 'G'+model['slack_bus']+'-1':
                continue
            row[index_P] = power
            row[index_Sn] = power*spinning_reserve
            
            # row[index_Sn] = row[index_Sn] * ENTSOE_gen_data['Power generation'].loc[area] / PowerGen_by_area.get(area)
    index_P = model['generators']['GEN'][0].index('P')
    hydro_and_nuclear_power = 0
    for row in model['generators']['GEN'][1:]:
        hydro_and_nuclear_power += row[index_P]
    print(f"Total hydro and nuclear power: {hydro_and_nuclear_power}")
    

    
    wind_power = 0
    for row in model['vsc']['VSC_SI'][1:]:
        name = row[0]
        bus_name = row[1]
        area = area_by_bus.get(bus_name)
        if name not in international_links.values() and len(wind_gen_by_area.get(area)) > 0:
            power = ENTSOE_gen_data['Power generation'].loc[area] * energy_mix[area]['Wind']/len(wind_gen_by_area.get(area))
            # if power > row[2]:
            #     ValueError(f"Power generation for {name} in {area} is larger than the nominal power")
            row[2] = power*1.2
            row[3] = power/row[2]
            row[4] = 0.0
            
            wind_power += power
    print(f"Total wind power: {wind_power}")
    print(f"Total power: {hydro_and_nuclear_power+wind_power}")
    print(f"Total power ENTSOE: {ENTSOE_gen_data['Power generation'].sum()}")


    # ------------------------------Updating loads' active and reactive power consumptions------------------------------
    index_name = model['loads'][0].index('name')
    index_bus_name = model['loads'][0].index('bus')
    index_P = model['loads'][0].index('P')
    index_Q = model['loads'][0].index('Q')
    loads_per_area = {}
    for row in model['loads'][1:]:
        bus_name = row[index_bus_name]
        area = area_by_bus.get(bus_name)
        if area not in loads_per_area:
            loads_per_area[area] = []
        if row[index_name] in international_links.keys():
            continue
        else:
            loads_per_area[area].append(row[index_name])

    for row in model['loads'][1:]:
        if row[index_name] in international_links.keys():
            transfer_code = international_links[row[index_name]]
            #OBS very specific for the Nordic 45 system 21.02.2025
            if transfer_code == 'FI-SE_3':
                power = -ENTSOE_exchange_data['Power transfer'].loc['SE_3-FI']
                row[index_P] = power
            else:
                power = ENTSOE_exchange_data['Power transfer'].loc[transfer_code]
                row[index_P] = power


        else:
            area = area_by_bus.get(row[index_bus_name])
            load_scaling = len(loads_per_area.get(area))
            power = ENTSOE_load_data['Power consumption'].loc[area]/load_scaling
            row[index_P] = power
            # row[index_Q] = power*0.1
            

    
    #take the sum of all loads and compare with the total power generation
    load_sum = 0
    for row in model['loads'][1:]:
        load_sum += row[index_P]
    print(f"Total load: {load_sum-(ENTSOE_exchange_data['Power transfer'].sum()-ENTSOE_exchange_data['Power transfer'].loc['SE_3-FI'])}")
    load_sum_entsoe = ENTSOE_load_data['Power consumption'].sum()
    print(f"Total load ENTSOE: {load_sum_entsoe}")
    print(f"Total import/export{(ENTSOE_exchange_data['Power transfer'].sum()-ENTSOE_exchange_data['Power transfer'].loc['SE_3-FI'])}")
    freq_bias_calculated = MThesis.calc_frequency_bias(model)
    print(f"Frequency bias: {freq_bias_calculated}")
    

   
    if virtual_gen:
        #Adds a virtual line with generator to be disconnected
        MThesis.add_virtual_line(model, fault_bus)
        add_virtual_gen = MThesis.add_virtual_gen(model, fault_bus, fault_P, fault_Sn)
        area_by_bus['Virtual bus'] = model['buses'][-1][index_area] #adding to mapping
    # ------------------------------Updating the inertia of the system based on the kinetic energy of the EPS-----------------------------------
    index_H = model['generators']['GEN'][0].index('H')
    S_EPS = 0 #Nominal power of EPS
    H_EPS = 0 #Inertia time constant of EPS
    Ek_EPS = 0 #Kinetic energy of EPS
    
    # Scaling the kinetic energy of the EPS
    for row in model['generators']['GEN'][1:]:
        #row[index_H] * = 1
        S_EPS += row[index_Sn]
        Ek_EPS += row[index_Sn] * row[index_H]
    H_EPS = Ek_EPS/S_EPS #Intertia time constant
    print(f'Kinetic energy before scaling: {Ek_EPS}')
    if kinetic_energy_eps is not None:
        scaling = kinetic_energy_eps/Ek_EPS
        for row in model['generators']['GEN'][1:]:
            row[index_H] *= scaling  # Apply the scaling factor to the inertia constant
        kinetic_energy_calculated = 0
        for row in model['generators']['GEN'][1:]:
            kinetic_energy_calculated += row[index_Sn]*row[index_H]
        print(f"Kinetic energy: {kinetic_energy_calculated}")


    init_VSC(model, ENTSOE_exchange_data)

    ps = dps.PowerSystemModel(model=model)
    ps.use_numba = True

    if display_pf:
        display_power_flow(ps, model, international_links, fault_bus, PowerExc_by_country)

    return ps

def init_VSC(model, exchange_data):
    vsc_international_links = {'L5230-1': 'NO_2-DE', 'L5240-2': 'NO_2-GB','L8700-2': 'SE_4-LT', 'L7020-1': 'FI-EE'} #Load names of international links with VSC-HVDC
    
    vsc_power_exchange = {'NO_2-DE': 0.0, 'NO_2-GB': 0.0, 'SE_4-LT': 0, 'FI-EE': 0.0} #Power exchange with VSC-HVDC

    for link, load in exchange_data.iterrows():
        if link in vsc_power_exchange.keys():
            vsc_power_exchange[link] = load['Power transfer']
    
    for row in model['loads'][1:]:
        name = row[0]

        # Removing loads that corresponds to VSC HVDC transmission 
        if name in vsc_international_links.keys(): 

            row[2] = 0.01 #setting P = 0
            row[3] = 0.01 #setting Q = 0
    
    for row in model['vsc']['VSC_SI'][1:]:
        link_name= row[0]
      
        if link_name in vsc_power_exchange.keys():
            s_b = row[2]
            row[3] = -vsc_power_exchange[link_name]/s_b







def display_power_flow(ps, model, international_links, fault_bus, PowerExc_by_country):
    """
    Displays the power flow in the Nordic 45 system.
    Parameters:
    model_data : dictionary
        Dictionary containing the model data.
    """
    
    ps.init_dyn_sim()
    x0 = ps.x0.copy()
    v0 = ps.v0.copy()
    
    Flows = {'NO_1-NO_2': 0.0, 'NO_1-NO_5': 0.0, 'NO_5-NO_2': 0.0, 'NO_1-NO_3': 0.0, 'NO_4-NO_3': 0.0, 'NO_5-NO_3': 0.0,
             'NO_1-SE_3': 0.0, 'NO_3-SE_2': 0.0, 'NO_4-SE_1': 0.0, 'NO_4-SE_2': 0.0, 'NO_4-FI': 0.0, 'SE_1-FI': 0.0,
             'SE_1-SE_2': 0.0, 'SE_2-SE_3': 0.0, 'SE_3-SE_4': 0.0, 'SE_3-FI': 0.0}

    # dictionary to map bus to area
    area_by_bus = {} #From bus find area
    bus_by_area = {} #From area find buses
    index_bus_name = model['buses'][0].index('name')
    index_area = model['buses'][0].index('Area')
    for bus in model['buses'][1:]:
        area = bus[index_area]
        area_by_bus[bus[index_bus_name]] = area
        if area not in bus_by_area:
            bus_by_area[area] = [bus[index_bus_name]]
        else:
            bus_by_area[area].append(bus[index_bus_name])
    
    s_base = ps.s_n

    #Flow along lines
    for from_bus, to_bus, p_to, p_from in zip(
        ps.lines['Line'].par['from_bus'], ps.lines['Line'].par['to_bus'],
        ps.lines['Line'].p_to(x0, v0).copy(), ps.lines['Line'].p_from(x0, v0).copy()):

        from_area = area_by_bus.get(from_bus)
        to_area = area_by_bus.get(to_bus)

        if from_area + '-' + to_area in Flows:
            Flows[from_area + '-' + to_area] -= p_to * s_base
        elif to_area + '-' + from_area in Flows:
            Flows[to_area + '-' + from_area] -= p_from * s_base

    #Flow along Transformer-lines
    for fbus, tbus, p_to, p_from in zip(
            ps.trafos['Trafo'].par['from_bus'], ps.trafos['Trafo'].par['to_bus'],\
            ps.trafos['Trafo'].p_to(x0, v0).copy(), ps.trafos['Trafo'].p_from(x0, v0).copy()):
        #S_base = model['base_mva']
        from_area = area_by_bus.get(fbus)
        to_area = area_by_bus.get(tbus)
        if from_area + '-' + to_area in Flows:
            Flows[from_area + '-' + to_area] -= p_to * s_base
        elif to_area + '-' + from_area in Flows:
            Flows[to_area + '-' + from_area] -= p_from * s_base
    
    #Checking if flow matches production - consumption:
    generation = {'FI': 0.0, 'NO_1': 0.0, 'NO_2': 0.0, 'NO_3': 0.0, 'NO_4': 0.0, 'NO_5': 0.0,
                  'SE_1': 0.0, 'SE_2': 0.0, 'SE_3': 0.0, 'SE_4': 0.0} #Generation in each area
    consumption = generation.copy() #Consumption in each area
    power_out = generation.copy() #Simulated power output from each area
    export = generation.copy() #Export data
    VSC_power = generation.copy() #Power from VSC-HVDC links

    for bus, P in zip(ps.gen['GEN'].par['bus'], ps.gen['GEN'].P_e(x0, v0).copy()):
            area = area_by_bus.get(bus)
            generation[area] += P
    
    for bus, s_b, p in zip(ps.vsc['VSC_SI'].par['bus'], ps.vsc['VSC_SI'].par['S_n'], ps.vsc['VSC_SI'].par['p_ref']):
        area = area_by_bus.get(bus)
        VSC_power[area] += p*s_b
    
    for name, bus, P in zip(ps.loads['Load'].par['name'], ps.loads['Load'].par['bus'], ps.loads['Load'].p(x0, v0).copy()):

        area = area_by_bus.get(bus)

        link = international_links[name].split('-') if name in international_links else None

        if link is None: # if name is not in international_links.keys() == is load 
            consumption[area] += P * s_base
        elif international_links[name] in Flows.keys():
            Flows[international_links[name]] += P * s_base
        elif international_links[name] in Flows.keys():
            Flows[international_links[name]] += P * s_base
        elif link[1] + '-' + link[0] in Flows.keys():
            Flows[link[1] + '-' + link[0]] += P * s_base
        else:
            export[area] += P * s_base #export power LCC-HVDC
    
    #This is the power exchange from simulation:
    for key, val in Flows.items():
        #Flow_filtered = [(key, value) for key, value in Flows.items() if area in key]
        from_to = key.split('-')
        power_out[from_to[0]] += val
        power_out[from_to[1]] -= val
    
    print(pd.DataFrame({'Transfer': list(Flows.keys()), 'Power [MW]': list(Flows.values())}))
    print(pd.DataFrame({'Area': list(generation.keys()), 'Generation': list(generation.values())}))
    print(pd.DataFrame({'Area': list(consumption.keys()), 'Consumption': list(consumption.values())}))
    print(pd.DataFrame({'Transfer': list(export.keys()), 'exchange': list(export.values())}))
    #print(pd.DataFrame({'Area': list(total_cons_test.keys()), 'total cons': list(total_cons_test.values())}))
    print(pd.DataFrame({'Area export': list(PowerExc_by_country.keys()), 'exchange': list(PowerExc_by_country.values())}))
    for area, gen, con, pflow, exc in zip(
            generation, generation.values(), consumption.values(), power_out.values(), export.values()):
        print('Area:', area, ' Generation - consumption: ', round(gen-con), ' After simulation: ', round(pflow+exc))

    #This should give the same
    total_loss = (ps.lines['Line'].p_loss_tot(x0, v0) + ps.trafos['Trafo'].p_loss_tot(x0, v0)) * s_base
    print('Balance:',sum(generation.values())-sum(consumption.values()) - sum(export.values()) + sum(VSC_power.values()))
    print('Losses: ', total_loss)


    #Checking balance
    print('FI-SE_3',ps.loads['Load'].par['name'][-12], ps.loads['Load'].p(x0, v0).copy()[-12]*s_base)
    print('SE_3-FI',ps.loads['Load'].par['name'][3], ps.loads['Load'].p(x0, v0).copy()[3]*s_base)
    print(sum(ps.gen['GEN'].par['S_n']))

    

