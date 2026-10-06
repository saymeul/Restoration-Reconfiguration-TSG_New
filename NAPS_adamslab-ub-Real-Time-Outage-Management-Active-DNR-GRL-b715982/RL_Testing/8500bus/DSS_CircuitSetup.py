"""OpenDSS setup helpers for the PowerBench IEEE 8500 feeder."""

import math

import networkx as nx
import numpy as np
import opendssdirect as dss


class DSS:
    def __init__(self, filename):
        self.filename = filename
        self.dss = dss

    def compile_ckt_dss(self):
        self.dss.Basic.ClearAll()
        self.dss.Text.Command("compile [{}]".format(self.filename))


class Bus:
    def __init__(self, DSSCktobj, bus_name):
        vmag = np.zeros(3)
        DSSCktobj.dss.Circuit.SetActiveBus(bus_name)
        voltages = DSSCktobj.dss.Bus.puVmagAngle()
        nodes = np.array(DSSCktobj.dss.Bus.Nodes(), dtype=int)
        for index, node in enumerate(nodes):
            if 1 <= int(node) <= 3 and int(index * 2) < len(voltages):
                vmag[int(node) - 1] = voltages[int(index * 2)]
        self.Vmag = np.nan_to_num(vmag, nan=0.0, posinf=0.0, neginf=0.0)
        self.nodes = nodes


class Branch:
    def __init__(self, DSSCktobj, branch_fullname):
        DSSCktobj.dss.Transformers.First()
        kva_base = float(DSSCktobj.dss.Transformers.kVA() or 1000.0)
        kv_base = float(DSSCktobj.dss.Transformers.kV() or 12.47)
        i_base = kva_base / max(math.sqrt(3.0) * kv_base, 1.0e-9)

        DSSCktobj.dss.Circuit.SetActiveElement(branch_fullname)
        bus_connections = DSSCktobj.dss.CktElement.BusNames()
        bus1 = bus_connections[0] if bus_connections else ""
        bus2 = bus_connections[1] if len(bus_connections) > 1 else ""
        currents = np.asarray(DSSCktobj.dss.CktElement.CurrentsMagAng(), dtype=float)
        current_indices = 2 * np.array(range(0, min(int(currents.size / 4), 3)))
        current_magnitudes = currents[current_indices] if current_indices.size else np.asarray([0.0])
        current_magnitudes = np.nan_to_num(current_magnitudes, nan=0.0, posinf=0.0, neginf=0.0)
        self.bus_fr = bus1
        self.bus_to = bus2
        self.Cap = float(np.sum(current_magnitudes) / max(i_base, 1.0e-9))


def CktModSetup(DSSfile, sectional_swt, tie_swt, generators):
    DSSCktobj = DSS(DSSfile)
    DSSCktobj.compile_ckt_dss()
    DSSCktobj.dss.Text.Command("Set Maxiterations=5000")
    DSSCktobj.dss.Text.Command("Set maxcontroliter=5000")
    DSSCktobj.dss.Basic.AllowForms(0)

    for switch in sectional_swt:
        DSSCktobj.dss.Text.Command(
            "New swtcontrol.swSec{} SwitchedObj=Line.{} Normal=c SwitchedTerm=1 Action=c".format(
                switch["no"],
                switch["line"],
            )
        )

    for switch in tie_swt:
        DSSCktobj.dss.Text.Command(
            "New Line.{} Bus1={}{} Bus2={}{} r1=1e-3 r0=1e-3 x1=0 x0=0 c1=0 c0=0 Length=0.001".format(
                switch["name"],
                switch["from node"],
                switch.get("from conn", ""),
                switch["to node"],
                switch.get("to conn", ""),
            )
        )
        DSSCktobj.dss.Text.Command(
            "New swtcontrol.swTie{} SwitchedObj=Line.{} Normal=o SwitchedTerm=1 Action=o".format(
                switch["no"],
                switch["name"],
            )
        )

    for gen in generators:
        DSSCktobj.dss.Text.Command(
            "New Generator.G{} bus1={}{} Phases={} Kv={} Kw={} Pf=0.8 Model=1".format(
                gen["no"],
                gen["bus"],
                gen.get("phaseconn", ""),
                gen.get("numphase", 3),
                gen.get("kV", 12.47),
                gen.get("size", 0.0),
            )
        )

    try:
        DSSCktobj.dss.Text.Command("redirect LoadShape1.DSS")
        DSSCktobj.dss.Text.Command("BatchEdit Load..* Daily=LoadShape1")
    except Exception:
        pass
    DSSCktobj.dss.Solution.Solve()
    return DSSCktobj


def graph_struct(DSSCktobj):
    graph = nx.Graph()
    index = DSSCktobj.dss.PDElements.First()
    while index > 0:
        element_name = DSSCktobj.dss.PDElements.Name()
        element_type = element_name.split(".")[0].lower()
        if element_type in ("line", "transformer"):
            try:
                branch = Branch(DSSCktobj, element_name)
                source = branch.bus_fr.split(".")[0]
                target = branch.bus_to.split(".")[0]
                if source and target:
                    if graph.has_edge(source, target):
                        labels = list(graph.edges[source, target].get("label", []))
                        labels.append(element_name)
                        graph.edges[source, target]["label"] = labels
                    elif graph.has_edge(target, source):
                        labels = list(graph.edges[target, source].get("label", []))
                        labels.append(element_name)
                        graph.edges[target, source]["label"] = labels
                    else:
                        graph.add_edge(source, target, label=[element_name])
            except Exception:
                pass
        index = DSSCktobj.dss.PDElements.Next()
    return graph
