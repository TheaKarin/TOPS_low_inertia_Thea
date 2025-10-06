#This is the script used in the master's thesis to investigate the different cases and tune.
#This is only kept as documentation
#It may also prove usefull for ideas when using N45

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
    #fault_area = 'FI'  # Kan jo egt hentes fra fault_bus. Skal fikses senere
    fault_bus = '7000'#'3359' #7000
    fault_Sn = 1400 #1400 #1110
    fault_P = 1400
    kinetic_energy_eps =  300e3  #300 MWs 180MWs #130MWs
    #path = 'C:/Users/eirik/OneDrive - NTNU/Master/'


    #ENTSOE_gen_data, ENTSOE_load_data, ENTSOE_exchange_data = MThesis.Import_data_ENTSOE(path)
    ENTSOE_gen_data, ENTSOE_load_data, ENTSOE_exchange_data = MThesis.Import_data_ENTSOE('examples/dyn_sim/N45_case_data/')
    #actual_data = MThesis.Import_actual_data(path + 'faktiske hendelser/utfall Olkiluoto.xlsx')

    # List of international power links: Should be updated if added links or using another model than N45
    international_links = {'L5230-1': 'NO_2-DE', 'L5240-2': 'NO_2-GB', 'L5210-1': 'NO_2-DK',
                           'L3360-1': 'SE_3-DK', 'L8600-1': 'SE_4-DK', 'L8700-1': 'SE_4-PL',
                           'L8600-2': 'SE_4-DE', 'L8700-2': 'SE_4-LT', 'L7020-1': 'FI-EE',
                           'L3020-1': 'SE_3-FI', 'L7010-1': 'FI-SE_3', 'L5220-1': 'NO_2-NL',
                           'L7020-2': 'FI-RU'}

    print(ENTSOE_exchange_data)
    print('Transparency')
    print(ENTSOE_gen_data)
    print(ENTSOE_load_data)
    print('----------')
    # print(ENTSOE_exchange_data['Power transfer'].keys())
    # print('Data from Transparency:\n',ENTSOE_gen_data)
    # Load model
    #import tops.ps_models.n45_with_controls_adapted as model_data
    import tops.ps_models.n45_2_0 as model_data
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
    # Initialize a list to store specified power generation by area code
    PowerGen_by_area = {}
    # Iterate through the 'GEN' data and extract 'bus' and 'P' columns
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

    #gen_without_gov = MThesis.find_gen_wihtout_gov(model, all_gen)

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
                '''area_transfer = area_transfer[:2] + '-' + area_transfer[-2:]
                P_new = (ENTSOE_exchange_data['Power transfer'].loc[area_transfer]/
                         PowerExc_by_country.get(area[:2])*row[index_P])
                row[index_P] = P_new if P_new != 0 else 0.01
                row[index_Q] = cot_phi * P_new if P_new != 0 else row[index_Q]'''

        else: #national loads
            P_new = row[index_P] * ENTSOE_load_data['Power consumption'].loc[area] / PowerCon_by_area.get(area)
            row[index_P] = P_new
            row[index_Q] = P_new * cot_phi

    print(pd.DataFrame({'Area': PowerCon_by_area.keys(), 'Consumpt': PowerCon_by_area.values()}))

    # R = 0
    #MThesis.scale_impedance(model,0,True)

    #Adding virtual line with generator to be disconnected
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

    #estmation of RoCoF
    RoCoF_est = -fault_P*model['f']/(2*kinetic_energy_eps)
    #Frequency bias:
    index_droop = model['gov']['HYGOV'][0].index('R')
    #index_name_hygov = model['gov']['HYGOV'][0].index('gen')
    #index_name_tgov = model['gov']['TGOV1'][0].index('gen')
    #index_gen_name = model['generators']['GEN'][0].index('name')
    Freq_bias = MThesis.calc_frequency_bias(model)

    # print(model['gov']['TGOV1'][0])
    #model['gov']['TGOV1'].append([mapping_for_gov[element] for element in model['gov']['TGOV1'][0]])
    MThesis.HYGOV_to_simplified(model)
    EK_TEST = 0
    S_TEST = 0
    for row in model['generators']['GEN'][1:]:
        row[index_H] = row[index_H] * scaling
        EK_TEST += row[index_Sn] * row[index_H]
        S_TEST += row[index_Sn]
    H_test = EK_TEST/S_TEST
    del index_P, index_Sn #Freeing up memory
    del index_area, from_count, cot_phi, load_name, index_Q, index_H, added
    del other_from_count, other_load_name, other_to_count, other_transfer, area_transfer
    del to_count, transfer_code, fault_Sn, fault_P, P_new, P_specified
    # --------------------------------------------------------------
    # Power system model
    ps = dps.PowerSystemModel(model=model)
    ps.use_numba = True
    #import examples.dyn_sim.x0 as x0
    # Power flow calculation
    ps.power_flow()

    # Initialization
    ps.init_dyn_sim()
    x0 = ps.x0.copy()
    v0 = ps.v0.copy()


    # ---------------------------------------- Checking simulated results (stationary) --------------------------------
    for name, P in zip(ps.loads['Load'].par['name'], ps.loads['Load'].par['P']):
        if name in international_links.keys():
            print(name, P)

    Flows = {'NO_1-NO_2': 0.0, 'NO_1-NO_5': 0.0, 'NO_5-NO_2': 0.0, 'NO_1-NO_3': 0.0, 'NO_4-NO_3': 0.0, 'NO_5-NO_3': 0.0,
             'NO_1-SE_3': 0.0, 'NO_3-SE_2': 0.0, 'NO_4-SE_1': 0.0, 'NO_4-SE_2': 0.0, 'NO_4-FI': 0.0, 'SE_1-FI': 0.0,
             'SE_1-SE_2': 0.0, 'SE_2-SE_3': 0.0, 'SE_3-SE_4': 0.0, 'SE_3-FI': 0.0}

    # Flow along transmission lines
    S_base = model['base_mva']
    for fbus, tbus, p_to, p_from in zip(
            ps.lines['Line'].par['from_bus'], ps.lines['Line'].par['to_bus'],
            ps.lines['Line'].p_to(x0, v0).copy(), ps.lines['Line'].p_from(x0, v0).copy()):

        from_area = area_by_bus.get(fbus)
        to_area = area_by_bus.get(tbus)
        if from_area + '-' + to_area in Flows:
            Flows[from_area + '-' + to_area] -= p_to * S_base
        elif to_area + '-' + from_area in Flows:
            Flows[to_area + '-' + from_area] -= p_from * S_base

    #Flow along Transformer-lines
    for fbus, tbus, p_to, p_from in zip(
            ps.trafos['Trafo'].par['from_bus'], ps.trafos['Trafo'].par['to_bus'],\
            ps.trafos['Trafo'].p_to(x0, v0).copy(), ps.trafos['Trafo'].p_from(x0, v0).copy()):
        #S_base = model['base_mva']
        from_area = area_by_bus.get(fbus)
        to_area = area_by_bus.get(tbus)
        if from_area + '-' + to_area in Flows:
            Flows[from_area + '-' + to_area] -= p_to * S_base
        elif to_area + '-' + from_area in Flows:
            Flows[to_area + '-' + from_area] -= p_from * S_base

    #Checking if flow matches production - consumption:
    generation = {'FI': 0.0, 'NO_1': 0.0, 'NO_2': 0.0, 'NO_3': 0.0, 'NO_4': 0.0, 'NO_5': 0.0,
                  'SE_1': 0.0, 'SE_2': 0.0, 'SE_3': 0.0, 'SE_4': 0.0} #Generation in each area
    consumption = generation.copy() #Consumption in each area
    power_out = generation.copy() #Simulated power output from each area
    export = generation.copy() #Export data

    for bus, P in zip(ps.gen['GEN'].par['bus'], ps.gen['GEN'].P_e(x0, v0).copy()):
            area = area_by_bus.get(bus)
            generation[area] += P

    total_cons_test = export.copy()
    for name, bus, P in zip(ps.loads['Load'].par['name'], ps.loads['Load'].par['bus'], ps.loads['Load'].p(x0, v0).copy()):
        area = area_by_bus.get(bus)
        reverse = international_links[name].split('-') if name in international_links else None
        if reverse is None:  # name not in international_links.keys():
            consumption[area] += P * S_base
        elif international_links[name] in Flows.keys():
            Flows[international_links[name]] += P * S_base
        elif reverse[1] + '-' + reverse[0] in Flows.keys():
            Flows[reverse[1] + '-' + reverse[0]] += P * S_base
        else:
            export[area] += P * S_base
        total_cons_test[area] += P * S_base

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
    print(pd.DataFrame({'Area': list(total_cons_test.keys()), 'total cons': list(total_cons_test.values())}))
    print(pd.DataFrame({'Area export': list(PowerExc_by_country.keys()), 'exchange': list(PowerExc_by_country.values())}))
    for area, gen, con, pflow, exc in zip(
            generation, generation.values(), consumption.values(), power_out.values(), export.values()):
        print('Area:', area, ' Generation - consumption: ', round(gen-con), ' After simulation: ', round(pflow+exc))

    #This should give the same
    total_loss = (ps.lines['Line'].p_loss_tot(x0, v0) + ps.trafos['Trafo'].p_loss_tot(x0, v0)) * S_base
    print('Balance:',sum(generation.values())-sum(consumption.values()) - sum(export.values()))
    print('Losses: ', total_loss)


    #Checking balance
    print('FI-SE_3',ps.loads['Load'].par['name'][-12], ps.loads['Load'].p(x0, v0).copy()[-12]*S_base)
    print('SE_3-FI',ps.loads['Load'].par['name'][3], ps.loads['Load'].p(x0, v0).copy()[3]*S_base)
    print(sum(ps.gen['GEN'].par['S_n']))
    # ------------------------------------------------------------------------------
    #Open the Excel file in append mode using openpyxl engine. To save for printing initial power flow
    # with pd.ExcelWriter(path + 'dataframes_DynPSSimPy.xlsx',
    #                     engine='openpyxl') as writer:

    #     # Save the new DataFrame to the existing sheet (if it doesn't exist, it will create a new sheet)
    #     pd.DataFrame({'Area': list(generation.keys()), 'Generation': list(generation.values())}) \
    #         .to_excel(writer, sheet_name='DynPSS_Gen', index=True)

    #     pd.DataFrame({'Area': list(consumption.keys()), 'Consumption': list(consumption.values())}) \
    #         .to_excel(writer, sheet_name='DynPSS_Con', index=True)

    #     pd.DataFrame({'Transfer': list(Flows.keys()), 'Power [MW]': list(Flows.values())}) \
    #         .to_excel(writer, sheet_name='DynPSS_trans', index=True)

    #     pd.DataFrame({'Link': list(export.keys()), 'exchange': list(export.values())}) \
    #         .to_excel(writer, sheet_name='DynPSS_export', index=True)

    #     print('Excel writing complete')
    #-----------------------------------------------------------------------------
    #Dynamisk til master. Alt før det her er fra prosjektoppgave (forprosjekt)
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
    sc_bus_idx = ps.gen['GEN'].bus_idx_red['terminal'][-1]  #bus 3249 (SE_1)
    print('RoCof', RoCoF_est)
    print('Frequency bias MW/Hz', Freq_bias)
    print('H_EPS', H_EPS)
    print('S_EPS', S_EPS)
    print('Kinetic EPS', Ek_EPS)
    print('Test kinetic EPS', EK_TEST)
    print('Test S EPS', S_TEST)
    print('Test H EPS', H_test)

    print('Initiating dynamic simulation')
    #print(ps.buses)
    #print(type(ps.buses))
    #print(type(ps.buses[0]))
    #print(ps.y_bus_red_mod[(sc_bus_idx,) * 2])
    while t < t_end:
        sys.stdout.write("\r%d%%" % (t / (t_end) * 100))

        #From actual response, error after about 16.7 seconds
        '''if t >= 16.7 and t <= 17.1:
            ps.y_bus_red_mod[(sc_bus_idx,) * 2] = 2
        else:
            ps.y_bus_red_mod[(sc_bus_idx,) * 2] = 0'''

        if t > 17.6 and event_flag: #17.6  #10.5 #10.8 #60.26
            event_flag = False
            ps.lines['Line'].event(ps, 'Virtual line', 'disconnect')

        result = sol.step()
        x = sol.y
        v = sol.v
        t = sol.t

        # Store result
        Flows = {key: 0.0 for key in Flows} #reseting for each iteration
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
        volt_virtual.append(abs(v[-1]))
        voltages_angle.append([np.degrees(np.angle(volt)) for volt in v])

    print('Simulation completed in {:.2f} seconds.'.format(time.time() - t_0))
    #print('Simulated flows\n',(Flows_all_itr))
    # Convert dict to pandas dataframe
    index = pd.MultiIndex.from_tuples(result_dict)
    result = pd.DataFrame(result_dict, columns=index)
    #print(index)
    #print(result.xs(key='speed', axis='columns', level=1).iloc[-1][result.xs(key='speed', axis='columns', level=1).iloc[-1] > 0.1/ps.model['f']].index.get_level_values(0).tolist())


    #Reading data from actual event: Must be compatible
    mapping_from_actual = {'SE4': 'SE_4', 'SE3': 'SE_3', 'SE2': 'SE_2', 'SE1': 'SE_1', 'NO1': 'NO_1', 'NO2': 'NO_2',
                           'NO3': 'NO_3', 'NO4': 'NO_4', 'NO5': 'NO_5', 'FI': 'FI', 'DK': 'DK'}

    keys_frequency = []
    frequency_iloc = []
    keys_realPower = []
    keys_realPower_reversed = [] # e.g: if NO_1-NO_2 not found from keys_realPower, check NO_2-NO_1 with reversed
    Flows_iloc = []

    # for k, key in enumerate(actual_data.keys()):
    #     split = key.split(':')
    #     if len(split) == 2:
    #         if 'Frequency' in split[1]:
    #             area_code = mapping_from_actual[split[0]]
    #             keys_frequency.append(area_code)
    #             frequency_iloc.append(k)
    #         elif 'Real Power' in split[1]:
    #             transfer_codes = split[0].split('-')
    #             keys_realPower.append(
    #                 mapping_from_actual[transfer_codes[0]] + '-' + mapping_from_actual[transfer_codes[1]])
    #             keys_realPower_reversed.append(
    #                 mapping_from_actual[transfer_codes[1]] + '-' + mapping_from_actual[transfer_codes[0]])
    #             Flows_iloc.append(k)
    #         else:
    #             print('Unknown Split!!!!')

    print('Checkpoint charlie')
    #Slicing results to Area:
    P_e_stored = np.array(P_e_stored) / ps.gen['GEN'].par['S_n'] #to p.u
    P_m_stored = np.array(P_m_stored)
    voltages = np.array(voltages)
    voltages_angle = np.array(voltages_angle)
    Flows_all_itr = np.array(Flows_all_itr)
    #index_bus_name = model['generators']['GEN'][0].index('bus')
    index_gen_name = model['generators']['GEN'][0].index('name')
    P_e_in_area = []
    P_m_in_area = []
    frequency_actual = []
    frequency_label = []
    generators_plot = []
    generators_duplicate = set()
    index_gen_name = model['generators']['GEN'][0].index('name')
    for k, row in enumerate(model['generators']['GEN'][1:], start=0):
        if area_by_bus[row[index_bus_name]] in keys_frequency and row[index_gen_name] != 'Virtual gen':
            bus_name = row[index_bus_name]
            gen_name = row[index_gen_name]
            if row[index_bus_name] not in generators_duplicate:
                generators_plot.append(gen_name)
                P_e_in_area.append(P_e_stored[:, k])
                P_m_in_area.append(P_m_stored[:, k])
                generators_duplicate.add(row[index_bus_name])
    #speed_results = result.xs(key='speed', axis='columns', level=1).drop(columns=['Virtual gen'])
    '''list_frequency_sim =[]
    #list_frequency_sim = speed_results.mean(axis=1)
    for k, row in enumerate(model['generators']['GEN'][1:], start=0):
        if area_by_bus[row[index_bus_name]] == fault_area and row[index_gen_name] != 'Virtual gen':
            gen_name = row[index_gen_name]
            list_frequency_sim.append(speed_results[gen_name])
            generators_plot.append(gen_name)
    list_frequency_sim = pd.DataFrame(list_frequency_sim).T.mean(axis=1)'''

    # for area in area_mapping.values():
    #     if area in keys_frequency:
    #         index_iloc = keys_frequency.index(area)
    #         frequency_actual.append(actual_data.iloc[:, frequency_iloc[index_iloc]].to_list())
    #         frequency_label.append(area)

    voltages_in_area = []
    voltages_angle_in_area = []
    buses_plot = []
    buses_duplicate = set()
    index_bus_name = model['buses'][0].index('name')
    for k, row in enumerate(model['buses'][1:], start=0):
        bus_name = row[index_bus_name]
        if area_by_bus[bus_name] == fault_area and bus_name != 'Virtual bus':
            buses_plot.append(bus_name)
            voltages_in_area.append(voltages[:, k])
            voltages_angle_in_area.append(voltages_angle[:, k])

    Flows_plot = []
    labels_flows = []
    Flows_actual = []
    # for k, transfer in enumerate(Flows.keys(), start=0):
    #     if transfer in keys_realPower:
    #         Flows_plot.append(Flows_all_itr[:, k])
    #         labels_flows.append(transfer)
    #         index_iloc = keys_realPower.index(transfer)
    #         Flows_actual.append(actual_data.iloc[:, Flows_iloc[index_iloc]].apply(lambda x: x/1e6).to_list())
    #     elif transfer in keys_realPower_reversed:
    #         Flows_plot.append(Flows_all_itr[:, k])
    #         labels_flows.append(transfer)
    #         index_iloc = keys_realPower_reversed.index(transfer)
    #         Flows_actual.append((actual_data.iloc[:, Flows_iloc[index_iloc]]).apply(lambda x: -x/1e6).tolist())

    # #Average  frequency:
    # #Average of Actual data:
    # list_frequency_actual = list()
    # for k, plot in enumerate(frequency_actual):
    #     list_frequency_actual.append([elem - plot[0] for elem in plot])
    #     #ax.plot(actual_data['Timestamp'], [elem - plot[0] for elem in plot], label=frequency_label[k], linestyle='dashed')
    # Average_freq = []
    # # Iterate over each column
    # for j in range(len(list_frequency_actual[0])):
    #     column_sum = 0
    #     for i in range(len(list_frequency_actual)):
    #         column_sum += list_frequency_actual[i][j]
    #     Average_freq.append(column_sum / len(list_frequency_actual))
    #Average of simulated:
    list_frequency_sim = list()
    speed_results = result.xs(key='speed', axis='columns', level=1).drop(columns=['Virtual gen']) if add_virtual_gen \
               else result.xs(key='speed', axis='columns', level=1)
    list_frequency_sim = speed_results.mean(axis=1)


    #print('Flows actually\n',Flows_actual)
    timestamps = result[('Global', 't')]
    fig, ax = plt.subplots(1)
    fig.suptitle('Generator speed deviation', fontsize=20)
    #ax.plot(timestamps, result.xs(key='speed', axis='columns', level=1).drop(columns=['Virtual gen']) * ps.model['f'])
    ax.plot(timestamps, list_frequency_sim * ps.model['f'], label='Simulated')
    #ax.plot(actual_data['Timestamp'], Average_freq, label='Actual')
    #gi_navn = frequency_label.index(fault_area)
    #ax.plot(actual_data['Timestamp'],[elem - frequency_actual[gi_navn][0] for elem in frequency_actual[gi_navn]],label='Actual')
    #for gen in generators_plot:
        #ax.plot(timestamps, result.xs(key='speed', axis='columns', level=1)[gen] * ps.model['f'], label=gen)
        #ax[1].plot(timestamps, result.xs(key='angle', axis='columns', level=1)[gen] * ps.model['f'], label=gen)
    #for k, plot in enumerate(frequency_actual):
    #    ax.plot(actual_data['Timestamp'], [elem - plot[0] for elem in plot], label=frequency_label[k], linestyle='dashed')

    ax.plot(timestamps, np.linspace(-0.1, -0.1, num=len(timestamps)), linestyle="dashed", color='k')
    ax.plot(timestamps, np.linspace( 0.1,  0.1, num=len(timestamps)), linestyle="dashed", color='k')
    ax.set_ylabel('Deviation (Hz)', fontsize=15)
    #ax[1].set_ylabel('Angle (rad.)')
    ax.set_xlabel('Time (s)', fontsize=15)
    #ax.set_ylim(-0.5, 0.102)
    ax.set_xlim(0, t_end)
    ax.legend()
    #ax[1].legend()
    '''fig2, ax2 = plt.subplots(2)
    fig2.suptitle('Electrical power and mechanical power in ' + fault_area)
    for k, gen in enumerate(generators_plot):
        ax2[0].plot(timestamps, P_e_stored, label=gen)
        ax2[1].plot(timestamps, P_m_stored, label=gen)

    #ax2[0].plot(timestamps, P_e_in_area)
    ax2[0].set_ylabel('Electrical Power (p.u.)')
    ax2[0].set_ylim(0, 1.5)
    #ax2[1].plot(timestamps, P_m_in_area)
    ax2[1].set_ylabel('Mechanical power (p.u)')
    ax2[1].set_xlabel('Time (s)')
    ax2[1].set_ylim(0, 1.5)
    ax2[0].legend()
    ax2[1].legend()

    fig3, ax3 = plt.subplots(2)
    fig3.suptitle('Bus voltages in ' + fault_area)
    for k, bus in enumerate(buses_plot):
        ax3[0].plot(timestamps, voltages_in_area[k], label=bus)
        ax3[1].plot(timestamps, voltages_angle_in_area[k], label=bus)
    ax3[0].plot(timestamps, np.linspace(1.05, 1.05, num=len(timestamps)), linestyle="dashed", color='k')
    ax3[0].plot(timestamps, np.linspace(0.95, 0.95, num=len(timestamps)), linestyle="dashed", color='k')
    ax3[0].set_ylabel('Bus voltage (p.u)')
    ax3[0].set_ylim(0.9, 1.1)
    ax3[1].set_ylabel('voltage angle (degrees)')
    ax3[1].set_xlabel('Time (s)')
    ax3[1].set_ylim(-180, 180)
    ax3[1].set_yticks([-180, -135, -90, -45, 0, 45, 90, 135, 180])
    ax3[0].legend()
    ax3[1].legend()

    plt.figure()
    plt.suptitle('Power flows')
    for k, (plot_actual, plot_sim) in enumerate(zip(Flows_actual, Flows_plot)):
        #plot_line = plt.plot(timestamps, plot_sim, linestyle='solid', label=labels_flows[k])
        if labels_flows[k] == 'NO_1-SE_3':
            plot_line = plt.plot(timestamps, [value * 1150 / plot_sim[0] for value in plot_sim], linestyle='solid', label=labels_flows[k])
            plt.plot(actual_data['Timestamp'], [value * 1150 / plot_actual[20] for value in plot_actual], color=plot_line[0].get_color(), linestyle="dashed",
                     label=labels_flows[k])
        elif labels_flows[k] == 'SE_1-FI':
            plot_line = plt.plot(timestamps, [value * 650 / plot_sim[0] for value in plot_sim], linestyle='solid',
                                 label=labels_flows[k])
            plt.plot(actual_data['Timestamp'], [value * 650 / plot_actual[20] for value in plot_actual], color=plot_line[0].get_color(), linestyle="dashed",
                     label=labels_flows[k])
        #plt.plot(actual_data['Timestamp'], plot_actual, color=plot_line[0].get_color(), linestyle="dashed",
        #         label=labels_flows[k])
    plt.legend()
    plt.ylabel('Power flows (MWh/h)')
    plt.xlabel('Time (s)')


    plt.figure()
    plt.plot(result[('Global', 't')], np.array(E_f_stored))
    plt.xlabel('time (s)')
    plt.ylabel('E_q (p.u.)')'''

    plt.show()
