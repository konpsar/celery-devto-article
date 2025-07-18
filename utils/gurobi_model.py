import gurobipy as gp
from gurobipy import GRB
from config_app import GUROBI_PARAMS as gurobi_params


def configure_model(model, aircraft, int_horizon, blackout_map, wo_total, max_day, max_concurrent_aircraft, weekend_counts):

    time_lmt = max(int_horizon)

    x = {}
    for a in aircraft:
        for j in range(len(aircraft[a].wps)):
            w = aircraft[a].wps[j].name
            for t in int_horizon:
                x[a, w, t] = model.addVar(vtype=GRB.BINARY, name=f"x_{a}_{w}_{t}")

    ### constraint 3.2.1: a workpackage is scheduled once within the time horizon
    for a in aircraft:
        for j in range(len(aircraft[a].wps)):
            w = aircraft[a].wps[j].name
            model.addConstr(gp.quicksum(x[a, w, t] for t in int_horizon) <= 1)

    ### constraint 3.2.2: a workpackage cannot be scheduled after its due date
    for a in aircraft:
        for j in range(len(aircraft[a].wps)):
            w = aircraft[a].wps[j].name
            wdue = aircraft[a].wps[j].due_map
            model.addConstr(gp.quicksum(x[a, w, t] * t for t in int_horizon) <= wdue)

    ### constraint 3.2.3a: no workpackage starts at blackout days
    for a in aircraft:
        for j in range(len(aircraft[a].wps)):
            w = aircraft[a].wps[j].name
            for t in blackout_map:
                model.addConstr(x[a, w, t] == 0)
    ### constraint 3.2.3b: each workpackage must be scheduled as a continuous block with respect to blackout days
    count=0
    for a in aircraft:
        for j in range(len(aircraft[a].wps)):
            w = aircraft[a].wps[j].name
            wd = aircraft[a].wps[j].dur
            count+=1
            print(w," ", wo_total - count)
            for t in blackout_map:
                T = [i for i in int_horizon if i not in blackout_map and i < t] 
                for ti in T: # time the workpackage can start
                    model.addConstr(x[a, w, ti] * wd <= x[a, w, ti]*(t - ti))
    ### constraint 3.2.4: workpackage completion day cannot exceed the last day of time horizon under consideration
    for a in aircraft:
        for j in range(len(aircraft[a].wps)):
            w = aircraft[a].wps[j].name
            wd = aircraft[a].wps[j].dur
            model.addConstr(gp.quicksum((t+wd) * x[a, w, t]  for t in int_horizon) <= max_day)

    ### constraint 3.2.5a: workpackage dependency 
    for a in aircraft:
        for i in range(len(aircraft[a].wps)):
            w1 = aircraft[a].wps[i].name
            wd1 = aircraft[a].wps[i].dur
            wdue1 = aircraft[a].wps[i].due_map

            for j in range(len(aircraft[a].wps)):
                w2 = aircraft[a].wps[j].name
                wd2 = aircraft[a].wps[j].dur
                wdue2 = aircraft[a].wps[j].due_map

                if wdue1 < wdue2:
                    model.addConstr(gp.quicksum(t * x[a, w2, t]  for t in int_horizon) >= gp.quicksum((t+wd1) * x[a, w1, t]  for t in int_horizon) - max_day * (1- gp.quicksum(x[a, w2, t]  for t in int_horizon)))
                
                    model.addConstr(gp.quicksum(x[a, w1, t]  for t in int_horizon) >= gp.quicksum(x[a, w2, t]  for t in int_horizon))
                    
    ### constraint: concurrent aircrafts under maintenance

    int_horizon_set = set(int_horizon)
    sum_expr = {}

    for t in int_horizon:
        sum_expr[t]=[]
        for a in aircraft:
            for i in range(len(aircraft[a].wps)):
                w = aircraft[a].wps[i].name
                wd = aircraft[a].wps[i].dur
                for t2 in range(t - wd + 1, t + 1):
                    if t2 in int_horizon_set:
                        sum_expr[t].append(x[a, w, t2])

    for t in sum_expr:
        model.addConstr(gp.quicksum(sum_expr[t]) <= max_concurrent_aircraft)

    ### constraint: task dependencies
    for a in aircraft:
        for i in range(len(aircraft[a].wps)):
            w1 = aircraft[a].wps[i].name
            wd1 = aircraft[a].wps[i].dur
            wdue1 = aircraft[a].wps[i].due_map
            
            for k in range(len(aircraft[a].wps[i].dependencies)): # dependencies contain WPs executed later in time
                w2 = aircraft[a].wps[i].dependencies[k][0].name
                wdue2 = aircraft[a].wps[i].dependencies[k][0].due_map
                
                for kk in range(len(aircraft[a].wps[i].dependencies[k][1])):
                    tas_util = int(aircraft[a].wps[i].dependencies[k][1][kk].util)
                    tas_freq = int(aircraft[a].wps[i].dependencies[k][1][kk].freq)

                    # this does not consider the calendar duration of WPs that are btw w1 and w2, which can add more remaining days to the task under consideration
                    # compare the number of days the previous WP moved back to the remaining days of the task 
                    model.addConstr(gp.quicksum((wdue1 + weekend_counts[wdue1] - t - weekend_counts[t])* x[a, w1, t]  for t in int_horizon) <= gp.quicksum((tas_freq - tas_util + wdue2 + weekend_counts[wdue2] -t - weekend_counts[t])*x[a, w2, t] + (max_day + weekend_counts[max_day]) *(x[a, w1, t] - x[a, w2, t]) for t in int_horizon))

                    model.addConstr(gp.quicksum((wdue2 + weekend_counts[wdue2] - t - weekend_counts[t])* x[a, w2, t]  for t in int_horizon) <= gp.quicksum(tas_util*x[a, w2, t] for t in int_horizon))

    ### Objective: Maximize the total number of workpackages as close to their due date as possible
    objective = gp.quicksum(x[a, aircraft[a].wps[i].name, t] * (time_lmt + t) for a in aircraft  for i in range(len(aircraft[a].wps)) for t in int_horizon)

    model.setObjective(objective, GRB.MAXIMIZE)


    model.Params.timeLimit = 150.0 # seconds
    model.Params.LogToConsole = 1
    model.Params.IntegralityFocus=1 # the solver tries to find solutions that are still (nearly) feasible if all integer variables are rounded to exact integral values. 

    return x



def get_results(model, x, aircraft, weekend_counts):
    """
    Extracts the results from the model and updates the work packages with new start times.
    Returns lists of scheduled work packages, their start and end times, and the loss in days.
    """
    ls = [] # list of WPs [startTime,endTime] 
    sch_wps = [] # list of tuples (aircraft, workpackage)
    loss = [] # deviation of start day from due day measured in calendar days

    if model.status in [GRB.OPTIMAL, GRB.SUBOPTIMAL, GRB.TIME_LIMIT]:
        for ac, wp, timei in x.keys():
            if (abs(x[ac, wp, timei].x) > 1e-1):
                workp = aircraft[ac].wps
                ind = next((i for i, wor in enumerate(workp) if wor.name == wp), None)
                ls.append([timei, timei + aircraft[ac].wps[ind].dur])
                aircraft[ac].wps[ind].update_new_start(timei)
                sch_wps.append((ac, wp))
                loss.append(aircraft[ac].wps[ind].due_map + weekend_counts[aircraft[ac].wps[ind].due_map] - timei - weekend_counts[timei])
    else:
        print('infeasible')
    return {"sch_wps": sch_wps, "ls": ls, "loss":loss}


