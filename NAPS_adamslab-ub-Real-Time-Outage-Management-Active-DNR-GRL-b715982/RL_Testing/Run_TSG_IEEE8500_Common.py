"""IEEE 8500 runner helpers shared by the TSG study scripts."""

import math
import os

import networkx as nx
import numpy as np


def canonical_edge(edge):
    u, v = edge
    return tuple(sorted((str(u), str(v))))


def _arg_or_env(args, attr, env_name, default, cast):
    if hasattr(args, attr):
        return cast(getattr(args, attr))
    return cast(os.environ.get(env_name, default))


def add_ieee8500_scenario_args(parser):
    parser.add_argument(
        "--max-scenario-radius",
        type=int,
        default=int(os.environ.get("TSG_IEEE8500_SCENARIO_RADIUS", "4")),
        help="Maximum random ego-subgraph radius for IEEE 8500 deterministic outage scenarios.",
    )
    parser.add_argument(
        "--max-outage-edges",
        type=int,
        default=int(os.environ.get("TSG_IEEE8500_MAX_OUTAGE_EDGES", "25")),
        help="Maximum outage edges per scenario; use 0 for no cap.",
    )


def generate_outage_scenario(experiment, scenario_seed, args):
    graph = experiment.init_module.G_init
    base_graph = experiment.init_module.G_base
    nodes = sorted([node for node in graph.nodes() if graph.degree(node) > 0])
    if not nodes:
        raise RuntimeError("IEEE 8500 graph has no candidate outage nodes.")

    max_radius = max(1, _arg_or_env(args, "max_scenario_radius", "TSG_IEEE8500_SCENARIO_RADIUS", 4, int))
    max_outage_edges = _arg_or_env(args, "max_outage_edges", "TSG_IEEE8500_MAX_OUTAGE_EDGES", 25, int)
    max_attempts = int(getattr(args, "max_scenario_generation_attempts", 100))
    max_fraction = float(getattr(args, "max_outage_fraction", 0.50))

    for attempt in range(max_attempts):
        rng = np.random.default_rng(int(scenario_seed) + 1_000_003 * attempt)
        root_node = nodes[int(rng.integers(0, len(nodes)))]
        radius = int(rng.integers(1, max_radius + 1))
        subgraph = nx.ego_graph(base_graph, root_node, radius=radius, undirected=False)
        sub_edges = sorted(set(canonical_edge(edge) for edge in subgraph.edges()))
        if not sub_edges:
            continue
        outage_fraction = float(rng.uniform(0.0, max_fraction))
        outage_count = int(math.ceil(len(sub_edges) * outage_fraction))
        outage_count = max(1, min(outage_count, len(sub_edges)))
        if max_outage_edges > 0:
            outage_count = min(outage_count, max_outage_edges)
        selected_indices = np.sort(
            rng.choice(len(sub_edges), size=outage_count, replace=False).astype(int)
        )
        outage_edges = sorted(sub_edges[int(index)] for index in selected_indices)
        return {
            "scenario": "deterministic_outage_edges",
            "scenario_seed": int(scenario_seed),
            "generation_attempt": int(attempt),
            "root_node": str(root_node),
            "radius": int(radius),
            "subgraph_edge_count": int(len(sub_edges)),
            "outage_fraction": outage_fraction,
            "outage_edges": outage_edges,
            "outage_edge_count": int(len(outage_edges)),
            "ieee8500_max_scenario_radius": int(max_radius),
            "ieee8500_max_outage_edges": int(max_outage_edges),
        }

    raise RuntimeError(
        "Could not generate a non-empty IEEE 8500 outage scenario for seed {} after {} attempts.".format(
            scenario_seed,
            max_attempts,
        )
    )
