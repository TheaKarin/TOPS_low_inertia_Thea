#This base script is created for a quick start into analysing N45.

from collections import defaultdict

import sys
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import time
import tops.dynamic as dps
import tops.solvers as dps_sol
import tops.utility_functions_eirik as MThesis
import importlib
importlib.reload(dps)

if __name__ == '__main__':
    fault_bus = '3359'
    fault_Sn = 1400
    fault_P = 1400
    kinetic_energy_eps = 300e3
    #path = 'C:/Users/eirik/OneDrive - NTNU/Master/'


    ENTSOE_gen_data, ENTSOE_load_data, ENTSOE_exchange_data = MThesis.Import_data_ENTSOE('examples/dyn_sim/N45_case_data/')

    # List of international power links: Should be updated if added links or using another model than N45
    international_links = {'L5230-1': 'NO_2-DE', 'L5240-2': 'NO_2-GB', 'L5210-1': 'NO_2-DK',
                           'L3360-1': 'SE_3-DK', 'L8600-1': 'SE_4-DK', 'L8700-1': 'SE_4-PL',
                           'L8600-2': 'SE_4-DE', 'L8700-2': 'SE_4-LT', 'L7020-1': 'FI-EE',
                           'L3020-1': 'SE_3-FI', 'L7010-1': 'FI-SE_3', 'L5220-1': 'NO_2-NL',
                           'L7020-2': 'FI-RU'}

    # Load model
    #import tops.ps_models.n45_tuned as model_data
    import tops.ps_models.n45_with_controls as model_data
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

    #To retrieve total specified power generation in an area
    PowerGen_by_area = {}
    index_bus_name = model['generators']['GEN'][0].index('bus')
    index_gen = model['generators']['GEN'][0].index('name')
    index_P = model['generators']['GEN'][0].index('P')

    all_gen = set()
    for row in model['generators']['GEN'][1:]:
        bus_name = row[index_bus_name]
        gen_name = row[index_gen]
        P_specified = row[index_P]
        area = area_by_bus.get(bus_name)
        if area not in PowerGen_by_area:
            PowerGen_by_area[area] = 0
        PowerGen_by_area[area] = PowerGen_by_area[area] + P_specified
        all_gen.add(gen_name)

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

    #Now the necessary data has been retrieved and calculated. Starting the change of variables

    # Updating generators' specified powers
    index_bus_name = model['generators']['GEN'][0].index('bus')
    index_gen = model['generators']['GEN'][0].index('name')
    index_P = model['generators']['GEN'][0].index('P')
    index_Sn = model['generators']['GEN'][0].index('S_n')
    for row in model['generators']['GEN'][1:]:
        bus_name = row[index_bus_name]
        P_specified = row[index_P]
        area = area_by_bus.get(bus_name)
        gen_name = row[index_gen]
        row[index_P] = (P_specified * ENTSOE_gen_data['Power generation'].loc[area] / PowerGen_by_area.get(area))
        row[index_Sn] = row[index_Sn] * ENTSOE_gen_data['Power generation'].loc[area] / PowerGen_by_area.get(area)

    # Updating loads' active and reactive power consumptions
    index_name = model['loads'][0].index('name')
    index_bus_name = model['loads'][0].index('bus')
    index_P = model['loads'][0].index('P')
    index_Q = model['loads'][0].index('Q')

    for row in model['loads'][1:]:
        bus_name = row[index_bus_name]
        load_name = row[index_name]
        area = area_by_bus.get(bus_name)
        cot_phi = row[index_Q] / row[index_P] if not -1 < row[index_P] < 1 else 0
        if row[index_name] in international_links.keys(): #if international link
            area_transfer = international_links.get(load_name)
            split = area_transfer.split('-')
            if area_transfer in ENTSOE_exchange_data['Power transfer'].keys(): #Only one link out of country
                P_new = ENTSOE_exchange_data['Power transfer'].loc[area_transfer]
                row[index_P] = P_new if P_new != 0 else 0.01
                row[index_Q] = cot_phi * P_new if P_new != 0 else row[index_Q]
            elif split[1]+'-'+split[0] in ENTSOE_exchange_data['Power transfer'].keys():
                #reversed_transfer = split[1]+'-'+split[0]
                P_new = - ENTSOE_exchange_data['Power transfer'].loc[split[1]+'-'+split[0]]
                row[index_P] = P_new if P_new != 0 else 0.01
                row[index_Q] = cot_phi * P_new if P_new != 0 else row[index_Q]
            else: #elif area_transfer not in ENTSOE_exchange_data['Power transfer'].keys(): #Might be multiple links out of country, need for disaggregation
                #export/import data is not retrieved
                P_new = row[index_P]
                row[index_P] = P_new if P_new != 0 else 0.01
                row[index_Q] = cot_phi * P_new if P_new != 0 else row[index_Q]

        else: #national loads
            P_new = row[index_P] * ENTSOE_load_data['Power consumption'].loc[area] / PowerCon_by_area.get(area)
            row[index_P] = P_new
            row[index_Q] = P_new * cot_phi

    print(pd.DataFrame({'Area': PowerCon_by_area.keys(), 'Consumpt': PowerCon_by_area.values()}))

    # R = 0
    #MThesis.scale_impedance(model,0,True)

    #Adding virtual line with generator or load to be disconnected. Only one gen or load works in this version
    add_virtual_gen = False
    MThesis.add_virtual_line(model, fault_bus)
    add_virtual_gen = MThesis.add_virtual_gen(model, fault_bus, fault_P, fault_Sn)
    #MThesis.load_to_disconnect(model,'L5230-1')

    area_by_bus['Virtual bus'] = model['buses'][-1][index_area] #adding to mapping
    index_H = model['generators']['GEN'][0].index('H')
    S_EPS = 0 #Nominal power of EPS
    H_EPS = 0 #Inertia time constant of EPS
    Ek_EPS = 0 #Kinetic energy of EPS
    # updating S_n
    for row in model['generators']['GEN'][1:]:
        #row[index_H] * = 1
        S_EPS += row[index_Sn]
        Ek_EPS += row[index_Sn] * row[index_H]
    H_EPS = Ek_EPS/S_EPS #Intertia time constant
    scaling = kinetic_energy_eps/Ek_EPS

    #Frequency bias:
    index_droop = model['gov']['HYGOV'][0].index('R')
    Freq_bias = MThesis.calc_frequency_bias(model)

    #MThesis.HYGOV_to_simplified(model)
    del index_P, index_Sn #Freeing up memory. These are not needed anymore
    del index_area, from_count, cot_phi, load_name, index_Q, index_H, added
    del other_from_count, other_load_name, other_to_count, other_transfer, area_transfer
    del to_count, transfer_code, fault_Sn, fault_P, P_new, P_specified
    # --------------------------------------------------------------
    # Power system model
    ps = dps.PowerSystemModel(model=model)
    ps.use_numba = True
    #import examples.dyn_sim.x0 as x0
    #x_0 = ps.x_0.copy()
    # Power flow calculation
    ps.power_flow()
    # Initialization
    ps.init_dyn_sim()
    x0 = ps.x0.copy()
    v0 = ps.v0.copy()

    #-----------------------------------------------------------------------------
    t = 0

    t_end = 50 #actual_data['Timestamp'].iloc[-1]  # Simulate the same time as actual response
    #x0 = ps.x0.copy()
    sol = dps_sol.ModifiedEulerDAE(ps.state_derivatives, ps.solve_algebraic, 0, x0, t_end, max_step=5e-3)

    P_e_stored = []
    P_m_stored = []
    E_f_stored = []
    voltages = []
    volt_virtual = []
    voltages_angle = []
    result_dict = defaultdict(list)
    t_0 = time.time()

    Flows_all_itr = []
    event_flag = True
    # Run simulation
    print('Initiating dynamic simulation')
    while t < t_end:
        sys.stdout.write("\r%d%%" % (t / (t_end) * 100))

        if t > 17.6 and event_flag:
            event_flag = False
            ps.lines['Line'].event(ps, 'Virtual line', 'disconnect')

        result = sol.step()
        x = sol.y
        v = sol.v
        t = sol.t

        # Store result
        S_base = model['base_mva']
        Flows = {'NO_1-NO_2': 0.0, 'NO_1-NO_5': 0.0, 'NO_5-NO_2': 0.0, 'NO_1-NO_3': 0.0, 'NO_4-NO_3': 0.0,
                 'NO_5-NO_3': 0.0, 'NO_1-SE_3': 0.0, 'NO_3-SE_2': 0.0, 'NO_4-SE_1': 0.0, 'NO_4-SE_2': 0.0,
                 'NO_4-FI': 0.0, 'SE_1-FI': 0.0, 'SE_1-SE_2': 0.0, 'SE_2-SE_3': 0.0, 'SE_3-SE_4': 0.0, 'SE_3-FI': 0.0}

        for fbus, tbus, p_to, p_from in zip(
                ps.lines['Line'].par['from_bus'], ps.lines['Line'].par['to_bus'],
                ps.lines['Line'].p_to(x, v).copy(), ps.lines['Line'].p_from(x, v).copy()):

            from_area = area_by_bus.get(fbus)
            to_area = area_by_bus.get(tbus)
            if from_area + '-' + to_area in Flows:
                Flows[from_area + '-' + to_area] -= p_to * S_base

            elif to_area + '-' + from_area in Flows:
                Flows[to_area + '-' + from_area] -= p_from * S_base

        # Flow along Transformer-lines
        for fbus, tbus, p_to, p_from in zip(
                ps.trafos['Trafo'].par['from_bus'], ps.trafos['Trafo'].par['to_bus'],
                ps.trafos['Trafo'].p_to(x, v).copy(), ps.trafos['Trafo'].p_from(x, v).copy()):
            from_area = area_by_bus.get(fbus)
            to_area = area_by_bus.get(tbus)
            if from_area + '-' + to_area in Flows:
                Flows[from_area + '-' + to_area] -= p_to * S_base
            elif to_area + '-' + from_area in Flows:
                Flows[to_area + '-' + from_area] -= p_from * S_base
        Flows_all_itr.append(list(Flows.copy().values()))
        result_dict['Global', 't'].append(sol.t)
        [result_dict[tuple(desc)].append(state) for desc, state in zip(ps.state_desc, x)]
        # Legger til nye outputs
        P_e_stored.append(ps.gen['GEN'].P_e(x, v).copy())
        P_m_stored.append(ps.gen['GEN'].P_m(x, v).copy())
        E_f_stored.append(ps.gen['GEN'].E_f(x, v).copy())
        voltages.append([abs(volt) for volt in v])
        voltages_angle.append([np.degrees(np.angle(volt)) for volt in v])

    print('Simulation completed in {:.2f} seconds.'.format(time.time() - t_0))
    # Convert dict to pandas dataframe
    index = pd.MultiIndex.from_tuples(result_dict)
    result = pd.DataFrame(result_dict, columns=index)

    #Reading data from actual event: Must be compatible
    mapping_from_actual = {'SE4': 'SE_4', 'SE3': 'SE_3', 'SE2': 'SE_2', 'SE1': 'SE_1', 'NO1': 'NO_1', 'NO2': 'NO_2',
                           'NO3': 'NO_3', 'NO4': 'NO_4', 'NO5': 'NO_5', 'FI': 'FI', 'DK': 'DK'}

    #Slicing results to Area:
    P_e_stored = np.array(P_e_stored) / ps.gen['GEN'].par['S_n'] #to p.u
    P_m_stored = np.array(P_m_stored)
    voltages = np.array(voltages)
    voltages_angle = np.array(voltages_angle)
    Flows_all_itr = np.array(Flows_all_itr)


    #Average of simulated:
    list_frequency_sim = list()
    speed_results = result.xs(key='speed', axis='columns', level=1).drop(columns=['Virtual gen']) if add_virtual_gen \
               else result.xs(key='speed', axis='columns', level=1)
    list_frequency_sim = speed_results.mean(axis=1)


    timestamps = result[('Global', 't')]
    fig, ax = plt.subplots(1)
    fig.suptitle('Generator speed deviation', fontsize=20)
    ax.plot(timestamps, list_frequency_sim * ps.model['f'], label='Simulated')
    ax.plot(timestamps, np.linspace(-0.1, -0.1, num=len(timestamps)), linestyle="dashed", color='k')
    ax.plot(timestamps, np.linspace( 0.1,  0.1, num=len(timestamps)), linestyle="dashed", color='k')
    ax.set_ylabel('Deviation (Hz)', fontsize=15)
    ax.set_xlabel('Time (s)', fontsize=15)
    ax.set_xlim(0, t_end)
    ax.legend()
    plt.show()
