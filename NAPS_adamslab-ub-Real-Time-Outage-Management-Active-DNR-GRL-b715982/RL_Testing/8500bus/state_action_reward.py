"""State, action, and reward functions for IEEE 8500 restoration studies."""

import math

import networkx as nx
import numpy as np

try:
    from .DSS_CircuitSetup import Branch, Bus
    from .DSS_Initialize import *
except ImportError:
    from DSS_CircuitSetup import Branch, Bus
    from DSS_Initialize import *


def _canonical_edge(edge):
    u, v = edge
    return tuple(sorted((str(u), str(v))))


def switchInfo(DSSCktobj):
    switches = []
    index = DSSCktobj.dss.SwtControls.First()
    while index > 0:
        name = DSSCktobj.dss.SwtControls.Name()
        line = DSSCktobj.dss.SwtControls.SwitchedObj()
        sw_status = DSSCktobj.dss.SwtControls.Action() - 1
        switches.append({"switch name": name, "edge name": line, "status": sw_status})
        index = DSSCktobj.dss.SwtControls.Next()
    return switches


def _energy_supplied_ratio(DSSCktobj):
    energy_supplied = 0.0
    total_demand = 0.0
    for load_name in list(DSSCktobj.dss.Loads.AllNames()):
        DSSCktobj.dss.Circuit.SetActiveElement("Load.{}".format(load_name))
        powers = np.asarray(DSSCktobj.dss.CktElement.Powers(), dtype=float)
        active_indices = 2 * np.array(range(0, min(int(powers.size / 2), 3)))
        active_power = powers[active_indices] if active_indices.size else np.asarray([0.0])
        active_power = np.nan_to_num(active_power, nan=0.0, posinf=0.0, neginf=0.0)
        energy_supplied += float(np.sum(active_power))
        try:
            total_demand += float(DSSCktobj.dss.Properties.Value("kW"))
        except ValueError:
            pass
    if total_demand <= 0.0:
        return 0.0
    return float(energy_supplied / total_demand)


def _branch_flow(DSSCktobj, edge):
    if not G_init.has_edge(*edge):
        return 0.0
    branch_name = G_init.edges[edge]["label"][0]
    try:
        return float(Branch(DSSCktobj, branch_name).Cap)
    except Exception:
        return 0.0


def _action_mask(G, edgesout):
    removed = {_canonical_edge(edge) for edge in edgesout}
    mask = []
    graph_edges = {_canonical_edge(edge) for edge in G.edges()}
    for switch in AllSwitches:
        edge = _canonical_edge(switch["edge"])
        mask.append(1.0 if edge in removed or edge not in graph_edges else 0.0)
    mask.extend([0.0 for _load in dispatch_loads])
    return np.asarray(mask, dtype=float)


def get_state(DSSCktobj, G, edgesout):
    adjacency = nx.to_numpy_array(G, nodelist=node_list, dtype=np.float32)
    energy_supply = _energy_supplied_ratio(DSSCktobj)

    voltage_rows = []
    active_conn = []
    for bus_name in node_list:
        try:
            bus = Bus(DSSCktobj, bus_name)
            voltage = np.nan_to_num(bus.Vmag, nan=0.0, posinf=0.0, neginf=0.0)
            active = np.asarray([node for node in bus.nodes if 1 <= int(node) <= 3], dtype=int)
        except Exception:
            voltage = np.zeros(3)
            active = np.asarray([], dtype=int)
        voltage_rows.append(voltage)
        active_conn.append(active)

    branch_flows = [
        _branch_flow(DSSCktobj, edge) if G.has_edge(*edge) else 0.0
        for edge in edge_list
    ]
    branch_flows = np.nan_to_num(np.asarray(branch_flows, dtype=float), nan=0.0, posinf=0.0, neginf=0.0)

    conv_const = 0.0 if DSSCktobj.dss.Solution.Converged() else 10.0
    v_viol = Volt_Constr(voltage_rows, active_conn)

    return {
        "EnergySupp": np.asarray([energy_supply], dtype=float),
        "NodeFeat(BusVoltage)": np.asarray(voltage_rows, dtype=float),
        "EdgeFeat(Branchflow)": branch_flows,
        "Adjacency": adjacency,
        "VoltageViolation": np.asarray([v_viol], dtype=float),
        "ConvergenceViolation": np.asarray([conv_const], dtype=float),
        "ActionMasking": _action_mask(G, edgesout),
    }


def take_action(action, out_edges):
    DSSCktObj, graph, _conv_flag = initialize()
    graph_scenario = graph.copy()
    action = np.asarray(action, dtype=int).reshape(-1)

    for action_index, switch in enumerate(AllSwitches):
        if action_index >= action.size:
            break
        command_action = "c" if int(action[action_index]) == 1 else "o"
        DSSCktObj.dss.Text.Command("Swtcontrol.{}.Action={}".format(switch["switch name"], command_action))
    DSSCktObj.dss.Solution.Solve()

    first_load_index = len(AllSwitches)
    for offset, load_name in enumerate(dispatch_loads):
        action_index = first_load_index + offset
        if action_index < action.size and int(action[action_index]) == 0:
            DSSCktObj.dss.Text.Command('{}.enabled="False"'.format(load_name))
    DSSCktObj.dss.Solution.Solve()

    for outage_edge in out_edges:
        u, v = outage_edge
        if graph_scenario.has_edge(u, v):
            graph_scenario.remove_edge(u, v)
        elif graph_scenario.has_edge(v, u):
            graph_scenario.remove_edge(v, u)
        edge = (u, v) if graph.has_edge(u, v) else (v, u)
        try:
            branch_name = graph.edges[edge]["label"][0]
            DSSCktObj.dss.Text.Command("Open {} term=1".format(branch_name))
            DSSCktObj.dss.Solution.Solve()
        except Exception:
            pass

    for switch in AllSwitches:
        if switch["switch name"] == "":
            continue
        try:
            DSSCktObj.dss.Circuit.SetActiveElement(switch["edge name"])
            DSSCktObj.dss.SwtControls.Name(switch["switch name"])
            if DSSCktObj.dss.SwtControls.Action() == 1:
                edge = switch["edge"]
                if graph_scenario.has_edge(*edge):
                    graph_scenario.remove_edge(*edge)
                elif graph_scenario.has_edge(edge[1], edge[0]):
                    graph_scenario.remove_edge(edge[1], edge[0])
        except Exception:
            pass

    DSSCktObj.dss.Solution.Solve()
    return DSSCktObj, graph_scenario


def Volt_Constr(Vmagpu, active_conn):
    vmax = 1.10
    vmin = 0.90
    violations = []
    for index, active in enumerate(active_conn):
        for phase in active:
            value = float(Vmagpu[index][int(phase) - 1])
            if value <= 0.01:
                continue
            if value < vmin:
                violations.append(abs(vmin - value) / vmin)
            elif value > vmax:
                violations.append(abs(value - vmax) / vmax)
    if not violations:
        return 0.0
    return float(np.sum(violations) / max(len(node_list) * 3, 1))


def get_reward(observ_dict):
    if observ_dict["ConvergenceViolation"] > 0 or math.isinf(float(observ_dict["VoltageViolation"])):
        return np.asarray([0.0], dtype=float)
    return np.asarray(observ_dict["EnergySupp"] - observ_dict["VoltageViolation"], dtype=float)
