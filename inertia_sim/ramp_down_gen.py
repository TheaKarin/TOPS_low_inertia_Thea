
'''
This script is meant to simulate the behavious/instability of the system that occurred in the 
Scandic power system when NSL had full export and the generators in Kvilldal ramped down.

This is done by using nordic 45, bus splitting ut bus 5240 into 5240 and 5245 to hopefully create more accurate results.
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
import tops.utility_functions_eirik as eirik
import numpy as np 

# general case (ps,model, gen_bus, t, t_end, ramp_start, ramp_end, P_start, P_end) 
def ramp_down_one_gen(ps,model, folderandfilename, gen_bus , t , t_end, ramp_start, ramp_end, P_start, P_end): #spesific case to help with logic
    '''
    Simulates a ramp down of a generator in the Nordic 45 system.
    Parameters:
    model : dictionary
        Dictionary containing the model data.
    fault_bus : string
        The bus number of the generator to be ramped down.
    t0 : float
        The initial time of the simulation.
    t_end : float
        The end time of the simulation.
    ramp_start : float
        The time when the ramp down starts.
    ramp_end : float
        The time when the ramp down ends.
    P_start : float
        The initial power of the generator.
    P_end : float
        The final power of the generator.
    '''
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

    while t < t_end:
        sys.stdout.write("\r%d%%" % (t/(t_end)*100))
        if t < ramp_start:
            #P_gen = ps.gen['GEN'].par['P']
            P_gen = P_start
        elif t > ramp_end:
            P_gen = P_end
        else:
            # Linear ramp down of generator power
            P_gen = P_start + (P_end - P_start) * (t - ramp_start) / (ramp_end - ramp_start)

        result = sol.step(t)

        x = sol.y
        v = sol.v
        t = sol.t

        dx = ps.ode_fun(0, ps.x_0)


        res['t'].append(t)
        res['gen_speed'].append(ps.gen['GEN'].speed(x, v).copy())
        res['v'].append(v.copy())
        res['gen_I'].append(ps.gen['GEN'].I(x, v).copy())
        res['gen_P'].append(ps.gen['GEN'].P_e(x, v).copy())
        res['load_P'].append(ps.loads['Load'].P(x, v).copy())
        res['load_Q'].append(ps.loads['Load'].Q(x, v).copy())
    
    print('Simulation completed in {:.2f} seconds.'.format(time.time() - t_0))
    uf.read_to_file(res, 'results/'+folderandfilename+'.json')

    #return