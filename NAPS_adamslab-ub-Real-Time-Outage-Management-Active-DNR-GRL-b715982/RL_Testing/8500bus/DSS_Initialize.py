"""Initialize the PowerBench IEEE 8500 feeder for restoration studies."""

import os
import re
from pathlib import Path

try:
    from .DSS_CircuitSetup import CktModSetup, graph_struct
except ImportError:
    from DSS_CircuitSetup import CktModSetup, graph_struct


def _find_repo_root():
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / "Datasets" / "IEEE8500_PowerBench").exists():
            return parent
    raise FileNotFoundError("Could not find Datasets/IEEE8500_PowerBench above {}".format(current))


REPO_ROOT = _find_repo_root()
IEEE8500_DATA_DIR = (
    REPO_ROOT
    / "Datasets"
    / "IEEE8500_PowerBench"
    / "source"
    / "PowerBench"
    / "Datasets"
    / "State Estimation"
    / "8500 Node"
)
DSS_FILE = Path(os.environ.get("TSG_IEEE8500_MASTER_DSS", IEEE8500_DATA_DIR / "Master.dss"))
LINES_FILE = IEEE8500_DATA_DIR / "Lines.dss"
LOADS_FILE = IEEE8500_DATA_DIR / "Loads.dss"

MAX_SWITCH_ACTIONS = int(os.environ.get("TSG_IEEE8500_MAX_SWITCH_ACTIONS", "0"))
MAX_LOAD_ACTIONS = int(os.environ.get("TSG_IEEE8500_MAX_LOAD_ACTIONS", "40"))


def _strip_comment(line):
    return line.split("!", 1)[0].strip()


def _parse_assignments(line):
    return {key.lower(): value.strip('"') for key, value in re.findall(r"([A-Za-z0-9_]+)=([^\s]+)", line)}


def _base_bus(bus):
    return str(bus).split(".", 1)[0]


def _parse_switch_lines(path):
    switches = []
    pattern = re.compile(r"^\s*new\s+line\.([^\s]+)", re.IGNORECASE)
    for raw_line in Path(path).read_text(errors="ignore").splitlines():
        if raw_line.lstrip().startswith("!"):
            continue
        line = _strip_comment(raw_line)
        if "switch=y" not in line.lower():
            continue
        if "enabled=false" in line.lower():
            continue
        match = pattern.search(line)
        if not match:
            continue
        fields = _parse_assignments(line)
        bus1 = fields.get("bus1", "")
        bus2 = fields.get("bus2", "")
        if not bus1 or not bus2:
            continue
        switches.append(
            {
                "no": len(switches) + 1,
                "line": match.group(1),
                "name": "swSec{}".format(len(switches) + 1),
                "from node": _base_bus(bus1),
                "to node": _base_bus(bus2),
                "from conn": "",
                "to conn": "",
            }
        )
    if MAX_SWITCH_ACTIONS > 0:
        switches = switches[:MAX_SWITCH_ACTIONS]
    return switches


def _parse_loads(path):
    loads = []
    pattern = re.compile(r"^\s*new\s+load\.([^\s]+)", re.IGNORECASE)
    for raw_line in Path(path).read_text(errors="ignore").splitlines():
        if raw_line.lstrip().startswith("!"):
            continue
        line = _strip_comment(raw_line)
        match = pattern.search(line)
        if not match:
            continue
        fields = _parse_assignments(line)
        bus = fields.get("bus1", "")
        try:
            kw = float(fields.get("kw", "0"))
        except ValueError:
            kw = 0.0
        loads.append(
            {
                "name": "Load.{}".format(match.group(1)),
                "short_name": match.group(1),
                "bus": _base_bus(bus),
                "kw": kw,
            }
        )
    loads.sort(key=lambda item: (item["kw"], item["name"]), reverse=True)
    if MAX_LOAD_ACTIONS > 0:
        loads = loads[:MAX_LOAD_ACTIONS]
    return loads


sectional_swt = _parse_switch_lines(LINES_FILE)
tie_swt = []
generators = []
_load_entries = _parse_loads(LOADS_FILE)
dispatch_loads = [entry["name"] for entry in _load_entries]
Load_Buses = {entry["name"]: entry["bus"] for entry in _load_entries}
Load_kW = {entry["name"]: entry["kw"] for entry in _load_entries}
Gen_Info = {}


def initialize():
    DSSCktobj = CktModSetup(str(DSS_FILE), sectional_swt, tie_swt, generators)
    graph = graph_struct(DSSCktobj)
    conv_flag = 1 if DSSCktobj.dss.Solution.Converged() else 0
    return DSSCktobj, graph, conv_flag


DSSCktObj, G_init, conv_flag = initialize()
G_base = G_init.copy()
node_list = list(G_init.nodes())
edge_list = list(G_init.edges())
substatn_id = "sourcebus" if "sourcebus" in G_init.nodes else (node_list[0] if node_list else "")

AllSwitches = []
SwitchLines = []
for switch in sectional_swt:
    edge = (_base_bus(switch["from node"]), _base_bus(switch["to node"]))
    AllSwitches.append(
        {
            "switch name": switch["name"],
            "edge name": "Line.{}".format(switch["line"]),
            "line": switch["line"],
            "from bus": edge[0],
            "to bus": edge[1],
            "edge": edge,
            "status": 1,
        }
    )
    SwitchLines.append(edge)

n_actions = len(AllSwitches) + len(dispatch_loads)
total_load_kw = sum(Load_kW.values())
