"""
Shared false-data injection utilities for OpenDSS/GRL restoration experiments.

The attack functions corrupt only the cyber observation seen by a controller.
OpenDSS remains the physical ground truth used to validate the selected action.
"""

import math
from time import perf_counter

import numpy as np


ATTACK_NAMES = ["clean", "voltage_masking", "branchflow_hiding", "energy_inflation", "topology_drop"]
DEFENSE_MODES = ["unmitigated", "mitigated", "fdia_aware"]
EPS = 1e-9

DEFAULT_THRESHOLDS = {
    "voltage_max_abs": 0.03,
    "voltage_changed_fraction": 0.02,
    "branchflow_relative_mae": 0.05,
    "energy_abs": 0.05,
    "topology_changed_edge_fraction": 0.01,
    "action_mask_changed_fraction": 0.0,
}

CHANNEL_TO_OBSERVATION_KEYS = {
    "voltage": ("NodeFeat(BusVoltage)",),
    "branchflow": ("EdgeFeat(Branchflow)",),
    "energy": ("EnergySupp",),
    "topology": ("Adjacency",),
    "action_mask": ("ActionMasking",),
}


def clone_observation(obs):
    return {key: np.array(value, copy=True) for key, value in obs.items()}


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
    attacked = clone_observation(obs)
    voltages = attacked["NodeFeat(BusVoltage)"]
    active_mask = np.isfinite(voltages) & (voltages > 0.01)
    deviation = np.abs(voltages - reported_voltage)
    selected = _select_top_fraction(deviation, active_mask, target_fraction, largest=True)

    flat = voltages.reshape(-1)
    original = flat[selected].copy()
    flat[selected] = reported_voltage

    return attacked, {
        "target": "NodeFeat(BusVoltage)",
        "changed_measurements": int(selected.size),
        "mean_abs_change": float(np.mean(np.abs(original - reported_voltage))) if selected.size else 0.0,
    }


def branchflow_hiding_fdia(obs, target_fraction=0.20, scale=0.25):
    attacked = clone_observation(obs)
    flows = attacked["EdgeFeat(Branchflow)"]
    valid_mask = np.isfinite(flows) & (flows > 0.0)
    selected = _select_top_fraction(flows, valid_mask, target_fraction, largest=True)

    flat = flows.reshape(-1)
    original = flat[selected].copy()
    flat[selected] = flat[selected] * scale

    return attacked, {
        "target": "EdgeFeat(Branchflow)",
        "changed_measurements": int(selected.size),
        "mean_abs_change": float(np.mean(np.abs(original - flat[selected]))) if selected.size else 0.0,
    }


def energy_inflation_fdia(obs, bias=0.25, max_reported=1.25):
    attacked = clone_observation(obs)
    original = np.array(attacked["EnergySupp"], copy=True)
    attacked["EnergySupp"] = np.clip(original + bias, 0.0, max_reported)
    return attacked, {
        "target": "EnergySupp",
        "old_value": float(original.reshape(-1)[0]),
        "new_value": float(attacked["EnergySupp"].reshape(-1)[0]),
    }


def topology_drop_fdia(obs, drop_fraction=0.05, seed=1234):
    attacked = clone_observation(obs)
    adjacency = attacked["Adjacency"]
    rng = np.random.default_rng(seed)
    upper_existing = np.argwhere(np.triu(adjacency, k=1) > 0.0)
    if upper_existing.size == 0:
        return attacked, {"target": "Adjacency", "dropped_edges": 0}

    count = max(1, int(math.ceil(len(upper_existing) * drop_fraction)))
    selected_rows = rng.choice(len(upper_existing), size=count, replace=False)
    selected_edges = upper_existing[selected_rows]
    for i, j in selected_edges:
        adjacency[i, j] = 0.0
        adjacency[j, i] = 0.0

    return attacked, {"target": "Adjacency", "dropped_edges": int(count)}


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


def _as_array(obs, key):
    return np.asarray(obs[key], dtype=float)


def _safe_mean(values):
    return float(np.mean(values)) if values.size else 0.0


def _safe_max(values):
    return float(np.max(values)) if values.size else 0.0


def compute_residuals(expected_obs, received_obs):
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

    return {
        "detected": bool(exceeded),
        "score": float(max(normalized_scores)) if normalized_scores else 0.0,
        "detected_channels": exceeded,
        "thresholds": dict(thresholds),
        "residuals": residuals,
    }


def _channel_from_metric(metric_name):
    if metric_name.startswith("voltage_"):
        return "voltage"
    if metric_name.startswith("branchflow_"):
        return "branchflow"
    if metric_name.startswith("energy_"):
        return "energy"
    if metric_name.startswith("topology_"):
        return "topology"
    if metric_name.startswith("action_mask_"):
        return "action_mask"
    return None


def mitigated_keys_from_detection(detection):
    channels = []
    keys = []
    for metric_name in detection.get("detected_channels", []):
        channel = _channel_from_metric(metric_name)
        if channel is None or channel in channels:
            continue
        channels.append(channel)
        keys.extend(CHANNEL_TO_OBSERVATION_KEYS[channel])
    return channels, keys


def mitigate_observation(reference_obs, received_obs, detection):
    mitigated = clone_observation(received_obs)
    channels, keys = mitigated_keys_from_detection(detection)
    for key in keys:
        if key in reference_obs and key in mitigated:
            mitigated[key] = reference_obs[key].copy()

    return mitigated, {
        "strategy": "replace_detected_channels_with_reference",
        "mitigation_applied": bool(keys),
        "mitigated_channels": channels,
        "mitigated_keys": keys,
        "reference_source": "OpenDSS/state-estimator observation",
    }


def restoration_action_quality(metrics):
    """Score a candidate restoration action for FDIA-aware screening."""
    return (
        float(metrics.get("reward", 0.0))
        + float(metrics.get("energy_ratio", 0.0))
        - float(metrics.get("voltage_violation", 0.0))
        - float(metrics.get("convergence_violation", 0.0))
    )


def _candidate_summary(candidate, num_switches):
    action = np.asarray(candidate["action"], dtype=int)
    metrics = candidate["metrics"]
    return {
        "name": candidate["name"],
        "quality": restoration_action_quality(metrics),
        "policy_time_ms": float(candidate["policy_time_ms"]),
        "energy_kw": float(metrics.get("energy_kw", 0.0)),
        "energy_ratio": float(metrics.get("energy_ratio", 0.0)),
        "voltage_violation": float(metrics.get("voltage_violation", 0.0)),
        "convergence_violation": float(metrics.get("convergence_violation", 0.0)),
        "reward": float(metrics.get("reward", 0.0)),
        "closed_switches": int(np.sum(action[:num_switches])),
        "loads_served": int(np.sum(action[num_switches:])),
        "action": action.tolist(),
    }


def _candidate_sort_key(candidate):
    metrics = candidate["metrics"]
    return (
        restoration_action_quality(metrics),
        float(metrics.get("reward", 0.0)),
        float(metrics.get("energy_ratio", 0.0)),
        -float(metrics.get("voltage_violation", 0.0)),
        -float(metrics.get("convergence_violation", 0.0)),
    )


def select_fdia_aware_grl_action(
    predict_action_fn,
    evaluate_action_fn,
    attacked_obs,
    mitigated_obs,
    detection,
    num_switches,
):
    """
    Detector-guided GRL mitigation layer.

    The trained GRL policy proposes candidate restoration actions from the
    attacked observation and, when FDIA is detected, from the detector-mitigated
    observation. A lightweight OpenDSS/digital-twin screen selects the action
    with the best physical restoration quality before dispatch.
    """
    decision_start = perf_counter()
    candidates = []
    total_policy_time_ms = 0.0

    raw_action, raw_policy_time_ms = predict_action_fn(attacked_obs)
    total_policy_time_ms += raw_policy_time_ms
    candidates.append(
        {
            "name": "attacked_observation_grl",
            "action": raw_action,
            "policy_time_ms": raw_policy_time_ms,
            "metrics": evaluate_action_fn(raw_action),
        }
    )

    if detection.get("detected", False):
        mitigated_action, mitigated_policy_time_ms = predict_action_fn(mitigated_obs)
        total_policy_time_ms += mitigated_policy_time_ms
        candidates.append(
            {
                "name": "detector_mitigated_observation_grl",
                "action": mitigated_action,
                "policy_time_ms": mitigated_policy_time_ms,
                "metrics": evaluate_action_fn(mitigated_action),
            }
        )

    selected = max(candidates, key=_candidate_sort_key)
    decision_time_ms = (perf_counter() - decision_start) * 1000.0
    screening_time_ms = max(0.0, decision_time_ms - total_policy_time_ms)
    candidate_summaries = [_candidate_summary(candidate, num_switches) for candidate in candidates]

    return {
        "action": np.asarray(selected["action"], dtype=int),
        "metrics": selected["metrics"],
        "policy_time_ms": float(selected["policy_time_ms"]),
        "decision_time_ms": float(decision_time_ms),
        "screening_time_ms": float(screening_time_ms),
        "selected_candidate": selected["name"],
        "candidate_actions": candidate_summaries,
        "fdia_aware_metadata": {
            "strategy": "detector_guided_grl_candidate_screening",
            "attack_aware": True,
            "screening_model": "OpenDSS/digital-twin physical validation",
            "selection_objective": "maximize reward + energy_ratio - voltage_violation - convergence_violation",
            "selected_candidate": selected["name"],
            "candidate_count": len(candidates),
            "candidate_names": [candidate["name"] for candidate in candidates],
            "detector_gate": bool(detection.get("detected", False)),
        },
    }
