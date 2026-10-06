"""
False data injection attack helpers for the 123-bus GCAPS tests.

These functions corrupt only the observation passed to the RL policy. They do
not modify the OpenDSS circuit, so OpenDSS remains the physical ground truth.
"""

import math

import numpy as np


def clone_observation(obs):
    """Return a deep copy of an observation dictionary with independent arrays."""
    copied = {}
    for key, value in obs.items():
        copied[key] = np.array(value, copy=True)
    return copied


def _select_top_fraction(values, valid_mask, fraction, largest=True):
    flat_values = values.reshape(-1)
    flat_mask = valid_mask.reshape(-1)
    candidate_indices = np.where(flat_mask)[0]
    if candidate_indices.size == 0:
        return np.array([], dtype=int)

    count = max(1, int(math.ceil(candidate_indices.size * fraction)))
    scores = flat_values[candidate_indices]
    order = np.argsort(scores)
    if largest:
        order = order[::-1]
    return candidate_indices[order[:count]]


def voltage_masking_fdia(obs, target_fraction=0.20, reported_voltage=1.0):
    """
    Hide abnormal voltage measurements by reporting selected active phases as
    nominal voltage.
    """
    attacked = clone_observation(obs)
    voltages = attacked["NodeFeat(BusVoltage)"]
    active_mask = np.isfinite(voltages) & (voltages > 0.01)
    deviation = np.abs(voltages - reported_voltage)
    selected = _select_top_fraction(deviation, active_mask, target_fraction, largest=True)

    flat = voltages.reshape(-1)
    original = flat[selected].copy()
    flat[selected] = reported_voltage

    metadata = {
        "target": "NodeFeat(BusVoltage)",
        "changed_measurements": int(selected.size),
        "mean_abs_change": float(np.mean(np.abs(original - reported_voltage))) if selected.size else 0.0,
    }
    return attacked, metadata


def branchflow_hiding_fdia(obs, target_fraction=0.20, scale=0.25):
    """Report the largest branch-flow measurements as much smaller values."""
    attacked = clone_observation(obs)
    flows = attacked["EdgeFeat(Branchflow)"]
    valid_mask = np.isfinite(flows) & (flows > 0.0)
    selected = _select_top_fraction(flows, valid_mask, target_fraction, largest=True)

    flat = flows.reshape(-1)
    original = flat[selected].copy()
    flat[selected] = flat[selected] * scale

    metadata = {
        "target": "EdgeFeat(Branchflow)",
        "changed_measurements": int(selected.size),
        "mean_abs_change": float(np.mean(np.abs(original - flat[selected]))) if selected.size else 0.0,
    }
    return attacked, metadata


def energy_inflation_fdia(obs, bias=0.25, max_reported=1.25):
    """Inflate the reported energy-supplied feature seen by the policy."""
    attacked = clone_observation(obs)
    original = np.array(attacked["EnergySupp"], copy=True)
    attacked["EnergySupp"] = np.clip(original + bias, 0.0, max_reported)

    metadata = {
        "target": "EnergySupp",
        "old_value": float(original.reshape(-1)[0]),
        "new_value": float(attacked["EnergySupp"].reshape(-1)[0]),
    }
    return attacked, metadata


def topology_drop_fdia(obs, drop_fraction=0.05, seed=1234):
    """
    Remove a fraction of reported graph edges from the adjacency matrix.

    This is a topology-data attack on the graph seen by GCAPS, not a physical
    switching operation in OpenDSS.
    """
    attacked = clone_observation(obs)
    adjacency = attacked["Adjacency"]
    rng = np.random.default_rng(seed)

    upper_existing = np.argwhere(np.triu(adjacency, k=1) > 0.0)
    if upper_existing.size == 0:
        metadata = {"target": "Adjacency", "dropped_edges": 0}
        return attacked, metadata

    count = max(1, int(math.ceil(len(upper_existing) * drop_fraction)))
    selected_rows = rng.choice(len(upper_existing), size=count, replace=False)
    selected_edges = upper_existing[selected_rows]

    for i, j in selected_edges:
        adjacency[i, j] = 0.0
        adjacency[j, i] = 0.0

    metadata = {
        "target": "Adjacency",
        "dropped_edges": int(count),
    }
    return attacked, metadata


def random_attack_kwargs(attack_name, rng):
    """Generate randomized but bounded parameters for a named FDIA case."""
    if attack_name == "voltage_masking":
        return {
            "target_fraction": float(rng.uniform(0.05, 0.40)),
            "reported_voltage": float(rng.uniform(0.96, 1.04)),
        }
    if attack_name == "branchflow_hiding":
        return {
            "target_fraction": float(rng.uniform(0.05, 0.40)),
            "scale": float(rng.uniform(0.05, 0.70)),
        }
    if attack_name == "energy_inflation":
        return {
            "bias": float(rng.uniform(0.05, 0.35)),
            "max_reported": float(rng.uniform(1.05, 1.30)),
        }
    if attack_name == "topology_drop":
        return {
            "drop_fraction": float(rng.uniform(0.01, 0.15)),
            "seed": int(rng.integers(0, 2**31 - 1)),
        }
    return {}


ATTACKS = {
    "voltage_masking": voltage_masking_fdia,
    "branchflow_hiding": branchflow_hiding_fdia,
    "energy_inflation": energy_inflation_fdia,
    "topology_drop": topology_drop_fdia,
}


def apply_attack(obs, attack_name, **attack_kwargs):
    if attack_name == "clean":
        return clone_observation(obs), {"target": "none"}
    if attack_name not in ATTACKS:
        raise ValueError(f"Unknown attack '{attack_name}'. Available: {sorted(ATTACKS)}")
    return ATTACKS[attack_name](obs, **attack_kwargs)
