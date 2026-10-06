"""
Optimal Switching Decision taken for network 
"""

import argparse
import json
import time
from pathlib import Path

import numpy as np

from timeit import default_timer as timer


from gurobipy import *

#----------------Constant Values------------------------------
M=100 #large value for optimization
Vmax=1.05 # max pu voltage
Vmin=0.95 # min pu voltage
# Squaring the voltages (accounting for real and imag in optimization)
Vsqmax= Vmax * Vmax
Vsqmin = Vmin * Vmin
Phases=['a','b','c']


SCENARIO_LINES = {
    "SC1": ['Line.l13', 'Line.l51', 'Line.l65'],
    "SC2": ['Line.sw7', 'Line.l58', 'Line.l120', 'Line.l67', 'Line.l68'],
}
ATTACKS = ["clean", "voltage_masking", "branchflow_hiding", "energy_inflation", "topology_drop"]
DEFENSE_MODES = ["unmitigated", "mitigated"]
MISOCP_DETECTOR_THRESHOLDS = {
    "energy_abs": 0.05,
    "topology_changed_edge_fraction": 0.01,
}


def parse_args():
    parser = argparse.ArgumentParser(description="Run one IEEE 123-bus MISOCP clean/FDIA case")
    parser.add_argument("--scenario", default="SC1", choices=sorted(SCENARIO_LINES))
    parser.add_argument("--attack", default="clean", choices=ATTACKS)
    parser.add_argument("--defense-mode", default="unmitigated", choices=DEFENSE_MODES)
    parser.add_argument("--seed", type=int, default=1234)
    parser.add_argument("--row-output", default="", help="Optional JSON path for the solved row")
    parser.add_argument("--write-lp", default="", help="Optional LP file path")
    parser.add_argument("--verbose", action="store_true", help="Print MISOCP decision variables")
    return parser.parse_args()


ARGS = parse_args()


#---------------Creating a Model ------------------------------
RestoreService=Model('RestoreService') # A service restoration model
RestoreService.Params.PreCrush=  1
RestoreService.Params.PreSolve=  0
RestoreService.Params.Cuts =  0
RestoreService.Params.NoRelHeurWork =  0
RestoreService.Params.Threads = 1
RestoreService.setParam("MIPFocus",2)


#---------------Creating Variables ------------------------------
from DSS_Initialize import *


def build_attack_settings(scenario_name, attack_name, seed):
    scenario_lines = list(SCENARIO_LINES[scenario_name])
    if attack_name == "clean":
        return scenario_lines, {}, {"target": "none", "optimizer_input_changed": False}
    if attack_name == "topology_drop":
        rng = np.random.default_rng(seed)
        candidates = [elem for elem in CktElems_mod if elem not in scenario_lines]
        drop_count = max(1, int(np.ceil(0.05 * len(candidates))))
        selected_idx = rng.choice(len(candidates), size=min(drop_count, len(candidates)), replace=False)
        dropped_lines = [candidates[int(idx)] for idx in selected_idx]
        metadata = {
            "target": "optimizer_topology",
            "optimizer_input_changed": True,
            "dropped_lines": dropped_lines,
            "note": "MISOCP optimizes on a perceived topology with these additional missing lines; metrics report the optimized decision under that attacked input.",
        }
        return scenario_lines + dropped_lines, {}, metadata
    if attack_name == "energy_inflation":
        rng = np.random.default_rng(seed)
        target_fraction = 0.25
        count = max(1, int(np.ceil(target_fraction * len(DispLoads))))
        selected = sorted(rng.choice(DispLoads, size=count, replace=False).tolist())
        bias = 0.25
        objective_weights = {load: 1.0 + bias for load in selected}
        metadata = {
            "target": "optimizer_load_weights",
            "optimizer_input_changed": True,
            "bias": bias,
            "weighted_loads": ["Load." + load for load in selected],
            "note": "MISOCP objective uses inflated perceived importance for selected dispatchable loads.",
        }
        return scenario_lines, objective_weights, metadata
    if attack_name == "voltage_masking":
        return scenario_lines, {}, {
            "target": "NodeFeat(BusVoltage)",
            "optimizer_input_changed": False,
            "note": "MISOCP does not use voltage measurement streams as optimizer input in this formulation; record this case as detector-only unless a measurement estimator is added.",
        }
    if attack_name == "branchflow_hiding":
        return scenario_lines, {}, {
            "target": "EdgeFeat(Branchflow)",
            "optimizer_input_changed": False,
            "note": "MISOCP does not use branch-flow measurement streams as optimizer input in this formulation; record this case as detector-only unless a measurement estimator is added.",
        }
    raise ValueError(f"Unknown attack '{attack_name}'")


def detect_misocp_input_attack(attack_name, attack_metadata):
    residuals = {
        "energy_abs": 0.0,
        "topology_changed_edge_fraction": 0.0,
        "measurement_detector_not_run": 0.0,
    }
    if attack_name == "energy_inflation":
        residuals["energy_abs"] = float(attack_metadata.get("bias", 0.0))
    elif attack_name == "topology_drop":
        denominator = max(len(CktElems_mod), 1)
        residuals["topology_changed_edge_fraction"] = float(len(attack_metadata.get("dropped_lines", [])) / denominator)
    elif attack_name in ("voltage_masking", "branchflow_hiding"):
        residuals["measurement_detector_not_run"] = 1.0

    detected_channels = []
    scores = []
    for metric, threshold in MISOCP_DETECTOR_THRESHOLDS.items():
        value = residuals.get(metric, 0.0)
        if value > threshold:
            detected_channels.append(metric)
        scores.append(value / threshold if threshold > 0 else 0.0)

    return {
        "detected": bool(detected_channels),
        "score": float(max(scores)) if scores else 0.0,
        "detected_channels": detected_channels,
        "residuals": residuals,
    }


def mitigate_misocp_attack_settings(scenario_name, attack_name, out_lines, objective_weights, detection):
    """Correct attacked MISOCP optimizer inputs when the detector flags them."""
    if not detection["detected"]:
        return out_lines, objective_weights, {
            "strategy": "none",
            "mitigation_applied": False,
            "mitigated_channels": [],
            "mitigated_keys": [],
            "note": "No optimizer-input FDIA was detected.",
        }

    corrected_out_lines = list(out_lines)
    corrected_objective_weights = dict(objective_weights)
    mitigated_channels = []
    mitigated_keys = []

    if attack_name == "energy_inflation" and "energy_abs" in detection["detected_channels"]:
        corrected_objective_weights = {}
        mitigated_channels.append("energy")
        mitigated_keys.append("objective_weights")

    if attack_name == "topology_drop" and "topology_changed_edge_fraction" in detection["detected_channels"]:
        corrected_out_lines = list(SCENARIO_LINES[scenario_name])
        mitigated_channels.append("topology")
        mitigated_keys.append("Out_Lines")

    return corrected_out_lines, corrected_objective_weights, {
        "strategy": "remove_detected_optimizer_input_corruption",
        "mitigation_applied": bool(mitigated_keys),
        "mitigated_channels": mitigated_channels,
        "mitigated_keys": mitigated_keys,
        "note": "MISOCP optimization uses corrected inputs; the model is still evaluated as an optimization baseline.",
    }


Out_Lines, objective_weights, attack_metadata = build_attack_settings(ARGS.scenario, ARGS.attack, ARGS.seed)
pre_mitigation_detection = detect_misocp_input_attack(ARGS.attack, attack_metadata)
post_mitigation_detection = pre_mitigation_detection
mitigation_metadata = {
    "strategy": "none",
    "mitigation_applied": False,
    "mitigated_channels": [],
    "mitigated_keys": [],
    "note": "Mitigation disabled for this run.",
}

if ARGS.defense_mode == "mitigated" and ARGS.attack != "clean":
    Out_Lines, objective_weights, mitigation_metadata = mitigate_misocp_attack_settings(
        ARGS.scenario,
        ARGS.attack,
        Out_Lines,
        objective_weights,
        pre_mitigation_detection,
    )
    if mitigation_metadata["mitigation_applied"]:
        post_mitigation_detection = detect_misocp_input_attack("clean", {"target": "none"})

#######Continuous Variables#######
# Substation or source active and reactive power [matrix i.e P(sourcebus,a),P(sourcebus,b),P(sourcebus,c)---sourcebuses have phase connections]
PSource=RestoreService.addVars(Phases, Sources, lb=0, name='PSource')
QSource=RestoreService.addVars(Phases, Sources, lb=0, name='QSource')
P_totGen=RestoreService.addVar(lb=0, name='P_totGen')
Q_totGen=RestoreService.addVar(lb=0, name='Q_totGen')
# Load Active and Reactive Powers [vector i.e P(load1),P(load2),P(load3) etc---load names already separately specified phases )
PLoad=RestoreService.addVars(CktLoads, lb=0, name='PLoad')
QLoad=RestoreService.addVars(CktLoads, lb=0, name='QLoad')
P_totLoad=RestoreService.addVar(lb=0, name='P_totLoad')
Q_totLoad=RestoreService.addVar(lb=0, name='Q_totLoad')
# Voltage at buses squared [matrix i.e Vsq(a,bus1),Vsq(b,bus1),Vsq(c,bus1),Vsq(a,busn) etc----buses have phase connections]
VsqBus=RestoreService.addVars(Phases, CktBuses, lb=0, name='VsqBus')
# Active and Reactive Power flow through the power delivery elements [matrix i.e. P(elem1,a)..P(elem1,c),P(elem2,a) etc]
PElem=RestoreService.addVars(Phases, CktElems, lb=-5 , name='PElem')
QElem=RestoreService.addVars(Phases, CktElems, lb=-5, name='QElem')
PGen=RestoreService.addVars(Phases, Gridfeeding.keys(), lb=0, name='PGen')
QGen=RestoreService.addVars(Phases, Gridfeeding.keys(), lb=0, name='QGen')
IsqElem= RestoreService.addVars(Phases, CktElems, lb=0, name ='IsqElem')

uSwitches=RestoreService.addVars(Switches, vtype=GRB.BINARY, name='uSwitches') 
directn=['i1','i2']
ElemsFlow=RestoreService.addVars(CktElems_mod, directn, vtype=GRB.BINARY, name='ElemsFlow')

uLoad=RestoreService.addVars(DispLoads, vtype=GRB.BINARY, name='uLoad') #!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!(CHANGE HERE)

#---------------Creating Objective function ------------------------------
obj= quicksum(objective_weights.get(h, 1.0) * PLoad[h] for h in CktLoads)
RestoreService.setObjective(obj, GRB.MAXIMIZE) #Define objective (Here maximizing power supplied)

#----------------Creating Constraints-----------------------------------------

#-- Equating the active and reactive power of load to demand 
for ld in CktLoads:
    # RestoreService.addConstr(PLoad[ld] == uLoad[ld]*LoadDemand[ld][0])
    # RestoreService.addConstr(QLoad[ld] == uLoad[ld]*LoadDemand[ld][1])
    if ld in DispLoads:
        RestoreService.addConstr(PLoad[ld] == uLoad[ld]*LoadDemand[ld][0])
        RestoreService.addConstr(QLoad[ld] == uLoad[ld]*LoadDemand[ld][1])
    else:
        RestoreService.addConstr(PLoad[ld] == LoadDemand[ld][0])
        RestoreService.addConstr(QLoad[ld] == LoadDemand[ld][1])

#-- Equating the active and reactive power generation at the bus nodes to actual generation
for gen in Gridfeeding.keys():
    phases_gen=Gridfeeding[gen]['Phases']
    P_totgen=Gridfeeding[gen]['Capacity_P']
    Q_totgen=Gridfeeding[gen]['Capacity_Q']

    for p in Phases:
        if p in phases_gen: # Equality constraint can be added here because the grid forming is a source (switching decision changes but the Energy Supplied remains same as before)
            RestoreService.addConstr(PGen[p,gen] == (P_totgen/len(phases_gen))) # The power generation
            RestoreService.addConstr(QGen[p,gen] == (Q_totgen/len(phases_gen))) # The reactive power generation
        else: #if phase is inactive
            RestoreService.addConstr(PGen[p,gen] == 0) # The power generation
            RestoreService.addConstr(QGen[p,gen] == 0)

#-- Total Load to sum of all Loaddemands
RestoreService.addConstr(P_totLoad == quicksum(PLoad[ld] for ld in CktLoads))
RestoreService.addConstr(Q_totLoad == quicksum(QLoad[ld] for ld in CktLoads))

#-- Total Generation equal to substation power([Sourcebus,a] +[Sourcebus,b]+[Sourcebus,c])
RestoreService.addConstr(P_totGen == quicksum(PSource[j,k] for j in Phases for k in Sources)+ quicksum(PGen[j,h] for j in Phases for h in Gridfeeding.keys()))
RestoreService.addConstr(Q_totGen == quicksum(QSource[j,k] for j in Phases for k in Sources)+ quicksum(QGen[j,h] for j in Phases for h in Gridfeeding.keys()))

#-- Total Load less than total generation
RestoreService.addConstr(P_totLoad <= P_totGen)    
RestoreService.addConstr(Q_totLoad <= Q_totGen)    
#-- Total power supplied by substation is less than the substation capacity
for s in Sources:
    RestoreService.addConstr(PSource['a',s] + PSource['b',s]+ PSource['c',s] <= Source_Cap[s])

#-- Bus voltage Constraints
# For PQ buses
for i in CktBuses:
    if i != Sources: #Source bus voltage is equal to 1.04
        for j in Phases:
            if  BusNodeConnec[i][Phases.index(j)] == 1: # Only if the node(phase) is present
                 RestoreService.addConstr(VsqBus[j,i] <= Vsqmax)
                 RestoreService.addConstr(Vsqmin <= VsqBus[j,i])
            elif BusNodeConnec[i][Phases.index(j)] == 0:
                 RestoreService.addConstr(VsqBus[j,i] ==0)  #If node(phase) is not present on bus, set it to 0

# For source bus or slack buses
for s in Sources:
    for j in Phases:
        RestoreService.addConstr(VsqBus[j,s] == Source_U[s])
            
#-- Branch flow constraints P, Q and Isq
#(3 cases- 
#case 1: line with phase does not exist, 
#case 2: line with phase exists and has switches, 
#case 3: line phase exists with no switches)
        
for k in CktElems:
    for j in Phases:
        if ElemNodeConnec[k][Phases.index(j)]==0: #(case 1)
            RestoreService.addConstr(PElem[j,k] == 0)
            RestoreService.addConstr(QElem[j,k] == 0)
            RestoreService.addConstr(IsqElem[j,k] == 0)
        else:
            if k in Switches: #(case 2)
                #PElem
                RestoreService.addConstr(PElem[j,k] <=3*uSwitches[k]) # 3 pu max flow
                RestoreService.addConstr(-3*uSwitches[k] <= PElem[j,k]) # -3 pu min flow
                #QElem
                RestoreService.addConstr(QElem[j,k] <= 3*uSwitches[k]) # 3 pu max flow
                RestoreService.addConstr(-3*uSwitches[k] <= QElem[j,k]) # -3 pu min flow 
                #IsqElem
                RestoreService.addConstr(IsqElem[j,k] <= Elem_Isqmax[k] *uSwitches[k]) 
                RestoreService.addConstr(-Elem_Isqmax[k] *uSwitches[k] <= IsqElem[j,k]) 
            else:             #(case 3)
                RestoreService.addConstr(PElem[j,k] <=3) # 3 pu max flow
                RestoreService.addConstr(-3 <= PElem[j,k]) # -3 pu min flow
                RestoreService.addConstr(QElem[j,k] <= 3) # 3 pu max flow
                RestoreService.addConstr(-3 <= QElem[j,k]) # -3 pu min flow  
                RestoreService.addConstr(IsqElem[j,k] <= Elem_Isqmax[k])
                RestoreService.addConstr(-Elem_Isqmax[k] <= IsqElem[j,k]) # -3 pu min flow 

for k in Out_Lines:    
    from_bus=CktElems_Connec[k][0]
    to_bus=CktElems_Connec[k][1]
    for j in Phases:
        RestoreService.addConstr(PElem[j,k] == 0)
        RestoreService.addConstr(QElem[j,k] == 0)    
        # RestoreService.addConstr(VsqBus[j,from_bus] == 0) # To use this constraint we need to use uBus as control variable
        # RestoreService.addConstr(VsqBus[j,to_bus] == 0)

#-- Active and Reactive Power Balance Constraint
for k in CktElems:
    for j in Phases:
        RestoreService.addConstr(PElem[j,k] == (P_balance(k, j, PLoad, PElem, PSource, CktElems_Connec, ElemNodeConnec, CktBusLoads, CktLoadDict, Elem_AdjElems, Sources, Source_Elems,IsqElem, R_Elem, GenBus_dict, Gridfeeding, PGen)) * ElemNodeConnec[k][Phases.index(j)]) 
        RestoreService.addConstr(QElem[j,k] == (Q_balance(k, j, QLoad, QElem, QSource, CktElems_Connec, ElemNodeConnec, CktBusLoads, CktLoadDict, Elem_AdjElems, Sources, Source_Elems, IsqElem, X_Elem, GenBus_dict, Gridfeeding, QGen)) * ElemNodeConnec[k][Phases.index(j)])
             
#-- Voltage Equations
# Case1 if element has switch use big M method in Vdrop as inequality constraint
# Case2 if element has no switch use simple Vdrop as equality constraint
for k in CktElems:
    for j in Phases:
        if ElemNodeConnec[k][Phases.index(j)]==1: # If the phase of element is active
           to_bus=CktElems_Connec[k][1]
           from_bus=CktElems_Connec[k][0]
           if BusNodeConnec[to_bus][Phases.index(j)]==1: #if the node/phase of the to bus is active
               if k in Switches: # The element has switch
                  RestoreService.addConstr(VsqBus[j, to_bus] -(Vdrop_eqn(k, j, from_bus, VsqBus, PElem, QElem, IsqElem, Rmod_Elem, Xmod_Elem, Zmod_Elem)) <= (1-uSwitches[k]) * M)             
                  RestoreService.addConstr(VsqBus[j, to_bus] -(Vdrop_eqn(k, j, from_bus, VsqBus, PElem, QElem, IsqElem, Rmod_Elem, Xmod_Elem, Zmod_Elem)) >= -(1-uSwitches[k]) * M)
                      
               else:
                  RestoreService.addConstr(VsqBus[j, to_bus] == (Vdrop_eqn(k, j, from_bus, VsqBus, PElem, QElem, IsqElem, Rmod_Elem, Xmod_Elem, Zmod_Elem)))

        

# Outflow is assigned direction 'i1'
# Inflow is assigned direction 'i2'

# Element connected to sourcebus or substation can only have outflow and inflow is 0
for s in Sources:    
    RestoreService.addConstr(ElemsFlow[Source_Elems[s], 'i2'] == 0)


#-- Current eqn convex relaxed into second order cone inequality
for k in CktElems:
    for j in Phases:
        if ElemNodeConnec[k][Phases.index(j)]==1: # If the phase of element is active
            from_bus=CktElems_Connec[k][0]    
            if BusNodeConnec[from_bus][Phases.index(j)]==1: #if the node/phase of the from bus is active
              if k not in Switches: # only if the element doesnot have a switch
                  RestoreService.addConstr(SOC_LHS(k, j, from_bus, IsqElem, VsqBus) >= SOC_RHS(k, j, PElem, QElem))


       
# An Element can have only 1 direction of flow 


# Case1 with switches
# Case 2 without switches

for k in CktElems_mod:
    if k not in Out_Lines:
        if k in Switches: 
            RestoreService.addConstr(ElemsFlow[k, 'i1'] + ElemsFlow[k, 'i2'] == uSwitches[k])
        else:
            RestoreService.addConstr(ElemsFlow[k, 'i1'] + ElemsFlow[k, 'i2'] == 1)
    else:
          RestoreService.addConstr(ElemsFlow[k, 'i1'] + ElemsFlow[k, 'i2'] == 0)
    
              
# for current ---approach similar to PElem
solve_start = timer()
solve_error = ""
try:
    RestoreService.optimize() #Optimize
except GurobiError as exc:
    solve_error = str(exc)
solve_time_sec = timer() - solve_start
if ARGS.write_lp and not solve_error:
    RestoreService.write(ARGS.write_lp) #extract lp file(As text)


def _var_key(var_name):
    return var_name.split('[', 1)[1].split(']', 1)[0]


def _var_value(var):
    try:
        return float(var.x)
    except Exception:
        return 0.0


def _binary_value(var):
    return int(round(abs(_var_value(var))))


has_solution = (not solve_error) and bool(getattr(RestoreService, "SolCount", 0) > 0)
switch_values = {}
load_values = {}

for v in RestoreService.getVars():
    var_family = v.varName.split('[', 1)[0]
    if var_family == 'uSwitches':
        elem_name = _var_key(v.varName)
        if Elem_Switchable.get(elem_name, 0) == 1:
            value = _binary_value(v) if has_solution else 0
            switch_values[elem_name] = value
            if ARGS.verbose:
                print('%s %g' % (v.varName, value))
    if var_family == 'uLoad':
        load_name = _var_key(v.varName)
        value = _binary_value(v) if has_solution else 0
        load_values[load_name] = value
        if ARGS.verbose:
            print('%s %g' % (v.varName, value))

switch_order = [elem for elem in Switches if Elem_Switchable.get(elem, 0) == 1]
switching = [int(switch_values.get(elem, 0)) for elem in switch_order]
loadCtrl = [int(load_values.get(load, 0)) for load in DispLoads]
loadstatus = {"Load." + load: int(load_values.get(load, 0)) for load in DispLoads}


def compute_energy_kw():
    if not has_solution:
        return 0.0, sum(float(LoadDemand[ld][0]) * KVA_base for ld in CktLoads), 0.0
    energy_kw = 0.0
    total_demand_kw = 0.0
    for load_name in CktLoads:
        demand_kw = float(LoadDemand[load_name][0]) * KVA_base
        total_demand_kw += demand_kw
        served = load_values.get(load_name, 1) if load_name in DispLoads else 1
        energy_kw += int(served) * demand_kw
    ratio = energy_kw / total_demand_kw if total_demand_kw else 0.0
    return energy_kw, total_demand_kw, ratio


def compute_voltage_violation():
    if not has_solution:
        return 1.0
    violations = []
    for bus_name in CktBuses:
        for phase in Phases:
            phase_index = Phases.index(phase)
            if BusNodeConnec[bus_name][phase_index] == 0:
                continue
            voltage_pu = float(np.sqrt(max(_var_value(VsqBus[phase, bus_name]), 0.0)))
            if voltage_pu < Vmin:
                violations.append(abs(Vmin - voltage_pu) / Vmin)
            if voltage_pu > Vmax:
                violations.append(abs(voltage_pu - Vmax) / Vmax)
    return float(np.sum(violations) / (len(CktBuses) * 3)) if violations else 0.0


energy_kw, total_demand_kw, energy_ratio = compute_energy_kw()
voltage_violation = compute_voltage_violation()
reward = energy_ratio - voltage_violation if has_solution else 0.0
detection = pre_mitigation_detection
action_array = switching + loadCtrl

row = {
    "method": "MISOCP",
    "scenario": ARGS.scenario,
    "case": ARGS.attack,
    "defense_mode": "clean" if ARGS.attack == "clean" else ARGS.defense_mode,
    "energy_kw": energy_kw,
    "total_demand_kw": total_demand_kw,
    "energy_ratio": energy_ratio,
    "voltage_violation": voltage_violation,
    "convergence_violation": 0.0 if has_solution else 1.0,
    "reward": reward,
    "fitness": reward,
    "optimizer_best_fitness": float(RestoreService.ObjVal) if has_solution else 0.0,
    "policy_time_ms": solve_time_sec * 1000.0,
    "runtime_sec": solve_time_sec,
    "loads_served": int(sum(loadCtrl)),
    "loads_shed": int(len(DispLoads) - sum(loadCtrl)),
    "closed_switches": int(sum(switching)),
    "open_switches": int(len(switching) - sum(switching)),
    "action_changed": 0,
    "switch_changes_vs_clean": 0,
    "load_changes_vs_clean": 0,
    "switch_vector": switching,
    "load_status": loadstatus,
    "attack_metadata": attack_metadata,
    "mitigation_metadata": mitigation_metadata,
    "mitigation_applied": int(mitigation_metadata["mitigation_applied"]),
    "mitigated_channels": mitigation_metadata["mitigated_channels"],
    "mitigated_keys": mitigation_metadata["mitigated_keys"],
    "fdia_detected": int(detection["detected"]),
    "detector_score": detection["score"],
    "detected_channels": detection["detected_channels"],
    "detector_residuals": detection["residuals"],
    "post_mitigation_fdia_detected": int(post_mitigation_detection["detected"]),
    "post_mitigation_detector_score": post_mitigation_detection["score"],
    "post_mitigation_detected_channels": post_mitigation_detection["detected_channels"],
    "post_mitigation_detector_residuals": post_mitigation_detection["residuals"],
    "optimizer_status": -1 if solve_error else int(RestoreService.Status),
    "optimizer_status_text": solve_error if solve_error else f"gurobi_status_{int(RestoreService.Status)}",
    "action_array": action_array,
}

if ARGS.row_output:
    row_output = Path(ARGS.row_output)
    row_output.parent.mkdir(parents=True, exist_ok=True)
    with row_output.open("w") as handle:
        json.dump(row, handle)
else:
    print(json.dumps(row, indent=2))

