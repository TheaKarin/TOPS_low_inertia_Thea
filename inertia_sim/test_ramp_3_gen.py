import sys
from collections import defaultdict
import matplotlib.pyplot as plt
import time
import tops.dynamic as dps
import tops.solvers as dps_sol
import importlib
importlib.reload(dps)
import numpy as np
import utility_functions_NJ as uf   
from init_N45 import init_n45
import tops.ps_models.copy_n45_2_0 as n45
import ramp_down_gen as rdg

if __name__ == '__main__':

    import sys
    sys.path.append('/Users/theathormodsen/Library/Mobile Documents/com~apple~CloudDocs/Masteroppgave/Kode og simulering/TOPS_low_inertia_Thea/')
    
    folderandfilename = 'ramp_down_tests/ramp_down_3_gen'
    t_ramp1 = 5
    t_ramp2 = 13
    t_ramp3 = 21 

    ramp_end1= t_ramp1 + 3
    ramp_end2= t_ramp2 + 3
    ramp_end3= t_ramp3 + 3

    t_end=30
    link_name = 'NO-2_GB'

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
                       data_path= 'inertia_sim/N45_case_data_NordLink/',
                       virtual_gen=False,spinning_reserve=1.2)
    
    
    model= ps.model.copy()
    gen = model['gen']['GEN']


    model['gen'] = {'GEN': gen}
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

    while t < t_end:
        sys.stdout.write("\r%d%%" % (t/(t_end)*100))
        if t < t_ramp1:
            rdg.ramp_down_one_gen(ps, ps.model, folderandfilename, gen_bus='G5240-1', t=0, t_end=t_end, 
                       ramp_start=t_ramp1, ramp_end=ramp_end1, P_start=700, P_end= 0)
        if t < t_ramp2:
            rdg.ramp_down_one_gen(ps, ps.model, folderandfilename, gen_bus='G5240-2', t=0, t_end=t_end, 
                      ramp_start=t_ramp2, ramp_end=ramp_end2, P_start=700, P_end= 0)
        if t < t_ramp3:
            rdg.ramp_down_one_gen(ps, ps.model, folderandfilename, gen_bus='G5240-3', t=0, t_end=t_end, 
                      ramp_start=t_ramp3, ramp_end=ramp_end3, P_start=700, P_end= 0)
        result = sol.step(t)
        x = sol.y
        v = sol.v
        t = sol.t


        dx = ps.ode_fun(0, ps.x_0)

        res['t'].append(t)
        res['gen_I'].append(ps.gen['GEN'].I(x, v).copy())
        res['gen_P'].append(ps.gen['GEN'].P_e(x, v).copy())
        res['gen_Q'].append(ps.gen['GEN'].Q_e(x, v).copy())
        res['V'].append(v.copy())
        # res['V'].append(ps.gen['GEN'].v_t(x, v).copy())
        # res['V'].append(ps.gen['GEN'].v_setp(x, v).copy())

        res['load_P'].append(ps.loads['DynamicLoad2'].P(x, v).copy())
        res['load_Q'].append(ps.loads['DynamicLoad2'].Q(x, v).copy())


    print('Simulation completed in {:.2f} seconds.'.format(time.time() - t_0))
    uf.read_to_file(res, 'results/'+folderandfilename+'.json')

    #plt.figure()
    #plt.plot(res['t'], res['gen_P'], res['gen_Q'], label=['P and Q generation'])


        
    
