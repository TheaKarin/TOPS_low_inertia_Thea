import sys
from collections import defaultdict
import matplotlib.pyplot as plt
import time
import tops.dynamic as dps
import tops.solvers as dps_sol
import importlib
importlib.reload(dps)
import numpy as np

# Add src directory to Python path
#import os
#sys.path.append(os.path.join(os.path.dirname(os.path.dirname(__file__)), 'src'))

import utility_functions_NJ as uf   
from init_N45 import init_n45
import tops.ps_models.n45_2_0 as n45



if __name__ == '__main__':
    #import sys
    sys.path.append('/Users/theathormodsen/Library/Mobile Documents/com~apple~CloudDocs/Masteroppgave/Kode og simulering/TOPS_low_inertia_Thea/src')
    folderandfilename = 'local_freq_tuning/K_est = 5'
    t_trip=10.81
    event_flag=True
    t_end=50
    link_name='NO_2-DE'


    energy_mix = {'FI': {'Wind': 0.7, 'Hydro': 0.1, 'Nuclear': 0.2, 'Solar': 0.0, 'Fossil': 0.0},
                'NO_1': {'Wind': 0.5, 'Hydro': 0.5, 'Nuclear': 0.0, 'Solar': 0.0, 'Fossil': 0.0},
                'NO_2': {'Wind': 0.4, 'Hydro': 0.6, 'Nuclear': 0.0, 'Solar': 0.0, 'Fossil': 0.0},
                'NO_3': {'Wind': 0.4, 'Hydro': 0.6, 'Nuclear': 0.0, 'Solar': 0.0, 'Fossil': 0.0},
                'NO_4': {'Wind': 0.5, 'Hydro': 0.5, 'Nuclear': 0.0, 'Solar': 0.0, 'Fossil': 0.0},
                'NO_5': {'Wind': 0.0, 'Hydro': 1.0, 'Nuclear': 0.0, 'Solar': 0.0, 'Fossil': 0.0},
                'SE_1': {'Wind': 0.95, 'Hydro': 0.05, 'Nuclear': 0.0, 'Solar': 0.0, 'Fossil': 0.0},
                'SE_2': {'Wind': 0.95, 'Hydro': 0.05, 'Nuclear': 0.0, 'Solar': 0.0, 'Fossil': 0.0},
                'SE_3': {'Wind': 0.6, 'Hydro': 0.0, 'Nuclear': 0.4, 'Solar': 0.0, 'Fossil': 0.0},
                'SE_4': {'Wind': 0.95, 'Hydro': 0.05, 'Nuclear': 0.0, 'Solar': 0.0, 'Fossil': 0.0}}


    ps = init_n45(model_data=n45,display_pf=False,energy_mix= energy_mix, 
                       data_path= 'inertia_sim/2030_scenario/',
                       virtual_gen=False,spinning_reserve=1.2)


    model = ps.model.copy()
    loads = model['loads']['Load']
    loads[0].extend(['K_est', 'T_est'])

    for row in loads[1:]:
        row.extend([5, 0.1])

    model['loads'] = {'DynamicLoad2': loads}
    ps = dps.PowerSystemModel(model=model)
    
    ps.power_flow()
    ps.init_dyn_sim()


    
    x0 = ps.x0.copy()
    v0 = ps.v0.copy()






    x_0 = ps.x_0.copy()

    # Solver
    sol = dps_sol.ModifiedEulerDAE(ps.state_derivatives, ps.solve_algebraic, 0, x_0, t_end, max_step=5e-3)

    # Initialize simulation
    t = 0
    res = defaultdict(list)
    t_0 = time.time()
    print(max(abs(ps.state_derivatives(0, ps.x_0, ps.v_0))))

       
    sc_bus_idx = 0
    for gen in ps.gen['GEN'].par['name']:
        if gen == 'G3245-1':
            sc_bus_idx = np.where(ps.gen['GEN'].par['name'] == gen)[0][0]
            break
    
    while t < t_end:
        sys.stdout.write("\r%d%%" % (t/(t_end)*100))

        # if t > t_trip and event_flag:
        #     event_flag = False
        #     #find the index of the vsc corresponding to the name load 
        #     #ps.vsc['VSC_SI'].par['name'] is an ndarray
        #     index_vsc = np.where(ps.vsc['VSC_SI'].par['name'] == link_name)[0]
        #     ps.vsc['VSC_SI'].set_input('p_ref', 0,index_vsc)

        if t >= 10 and t <= 10.5:
            ps.y_bus_red_mod[(sc_bus_idx,) * 2] = 1e6
        else:
            ps.y_bus_red_mod[(sc_bus_idx,) * 2] = 0
        result = sol.step()
        x = sol.y
        v = sol.v
        t = sol.t
        
        omega, delta_omega = ps.loads['DynamicLoad2'].freq_est(x, v)

        dx = ps.ode_fun(0, ps.x_0)
        res['t'].append(t)
        res['gen_speed'].append(ps.gen['GEN'].speed(x, v).copy())
        res['v'].append(v.copy())
        res['gen_I'].append(ps.gen['GEN'].I(x, v).copy())
        res['gen_P'].append(ps.gen['GEN'].P_e(x, v).copy())
        res['load_P'].append(ps.loads['DynamicLoad2'].P(x, v).copy())
        res['load_Q'].append(ps.loads['DynamicLoad2'].Q(x, v).copy())
        res['VSC_p'].append(ps.vsc['VSC_SI'].p_e(x, v).copy())
        res['freq_est_omega'].append(omega)
        res['freq_est_delta_omega'].append(delta_omega)
        res['VSC_Sn'].append(ps.vsc['VSC_SI'].par['S_n'])
    res['VSC_name'].append(ps.vsc['VSC_SI'].par['name'])
    res['gen_name'].append(ps.gen['GEN'].par['name'])
    res['bus_names'].append(ps.buses['name'])
    res['load_name'].append(ps.loads['DynamicLoad2'].par['name'])
    print('Simulation completed in {:.2f} seconds.'.format(time.time() - t_0))
    uf.read_to_file(res, 'Results/'+folderandfilename+'.json')