"""
Residual-based FDIA detector for the 123-bus GCAPS tests.

In this simulation, the expected observation is the OpenDSS/reference
observation before attack injection. In a field deployment, this reference
would need to come from a state estimator, redundant measurements, or a
trusted model-based observer.
"""

import numpy as np


EPS = 1e-9

DEFAULT_THRESHOLDS = {
    "voltage_max_abs": 0.03,
    "voltage_changed_fraction": 0.02,
    "branchflow_relative_mae": 0.05,
    "energy_abs": 0.05,
    "topology_changed_edge_fraction": 0.01,
    "action_mask_changed_fraction": 0.0,
}


def _as_array(obs, key):
    return np.asarray(obs[key], dtype=float)


def _safe_mean(values):
    if values.size == 0:
        return 0.0
    return float(np.mean(values))


def _safe_max(values):
    if values.size == 0:
        return 0.0
    return float(np.max(values))


def compute_residuals(expected_obs, received_obs):
    """Compute residual features between expected and received observations."""
    expected_voltage = _as_array(expected_obs, "NodeFeat(BusVoltage)")
    received_voltage = _as_array(received_obs, "NodeFeat(BusVoltage)")
    voltage_active = np.isfinite(expected_voltage) & np.isfinite(received_voltage) & (expected_voltage > 0.01)
    voltage_abs_diff = np.abs(received_voltage - expected_voltage)[voltage_active]

    expected_flow = _as_array(expected_obs, "EdgeFeat(Branchflow)")
    received_flow = _as_array(received_obs, "EdgeFeat(Branchflow)")
    flow_valid = np.isfinite(expected_flow) & np.isfinite(received_flow)
    flow_abs_diff = np.abs(received_flow - expected_flow)[flow_valid]
    flow_scale = np.mean(np.abs(expected_flow[flow_valid])) + EPS if np.any(flow_valid) else 1.0

    expected_energy = _as_array(expected_obs, "EnergySupp").reshape(-1)[0]
    received_energy = _as_array(received_obs, "EnergySupp").reshape(-1)[0]

    expected_voltage_violation = _as_array(expected_obs, "VoltageViolation").reshape(-1)[0]
    received_voltage_violation = _as_array(received_obs, "VoltageViolation").reshape(-1)[0]

    expected_adjacency = _as_array(expected_obs, "Adjacency")
    received_adjacency = _as_array(received_obs, "Adjacency")
    adjacency_changed = np.abs(received_adjacency - expected_adjacency) > 1e-6
    upper_mask = np.triu(np.ones_like(expected_adjacency, dtype=bool), k=1)
    existing_edges = (expected_adjacency > 0.0) & upper_mask
    changed_edges = adjacency_changed & upper_mask
    edge_denominator = max(int(np.sum(existing_edges)), 1)

    expected_action_mask = _as_array(expected_obs, "ActionMasking")
    received_action_mask = _as_array(received_obs, "ActionMasking")
    action_mask_changed = np.abs(received_action_mask - expected_action_mask) > 1e-6

    return {
        "voltage_mae_active": _safe_mean(voltage_abs_diff),
        "voltage_max_abs": _safe_max(voltage_abs_diff),
        "voltage_changed_fraction": float(np.mean(voltage_abs_diff > 1e-6)) if voltage_abs_diff.size else 0.0,
        "branchflow_mae": _safe_mean(flow_abs_diff),
        "branchflow_relative_mae": _safe_mean(flow_abs_diff) / flow_scale,
        "branchflow_max_abs": _safe_max(flow_abs_diff),
        "energy_abs": float(abs(received_energy - expected_energy)),
        "voltage_violation_abs": float(abs(received_voltage_violation - expected_voltage_violation)),
        "topology_changed_entry_fraction": float(np.mean(adjacency_changed)),
        "topology_changed_edge_fraction": float(np.sum(changed_edges) / edge_denominator),
        "action_mask_changed_fraction": float(np.mean(action_mask_changed)),
    }


def detect_fdia(expected_obs, received_obs, thresholds=None):
    """
    Flag FDIA when one or more residual metrics exceeds its threshold.

    Returns a serializable dictionary with the overall decision, score, and
    per-channel residuals.
    """
    thresholds = thresholds or DEFAULT_THRESHOLDS
    residuals = compute_residuals(expected_obs, received_obs)

    exceeded = []
    normalized_scores = []
    for metric, threshold in thresholds.items():
        value = residuals.get(metric, 0.0)
        if value > threshold:
            exceeded.append(metric)
        if threshold > 0:
            normalized_scores.append(value / threshold)
        elif value > 0:
            normalized_scores.append(float("inf"))
        else:
            normalized_scores.append(0.0)

    score = float(max(normalized_scores)) if normalized_scores else 0.0
    return {
        "detected": bool(exceeded),
        "score": score,
        "detected_channels": exceeded,
        "thresholds": dict(thresholds),
        "residuals": residuals,
    }
