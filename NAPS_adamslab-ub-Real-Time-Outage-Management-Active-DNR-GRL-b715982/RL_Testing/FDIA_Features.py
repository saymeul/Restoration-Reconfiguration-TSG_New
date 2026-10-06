"""
Feature utilities for learning-based FDIA detectors.
"""

import json
from pathlib import Path

import numpy as np


DEFAULT_FEATURE_KEYS = [
    "EnergySupp",
    "NodeFeat(BusVoltage)",
    "EdgeFeat(Branchflow)",
    "Adjacency",
    "VoltageViolation",
    "ConvergenceViolation",
    "ActionMasking",
]

BDD_RESIDUAL_FEATURE_KEYS = [
    "voltage_mae_active",
    "voltage_max_abs",
    "voltage_changed_fraction",
    "branchflow_mae",
    "branchflow_relative_mae",
    "branchflow_max_abs",
    "energy_abs",
    "voltage_violation_abs",
    "topology_changed_entry_fraction",
    "topology_changed_edge_fraction",
    "action_mask_changed_fraction",
]


def observation_to_feature_vector(obs, feature_keys=None):
    """Flatten selected observation fields into one numeric feature vector."""
    feature_keys = feature_keys or DEFAULT_FEATURE_KEYS
    chunks = []
    for key in feature_keys:
        values = np.asarray(obs[key], dtype=np.float32).reshape(-1)
        values = np.nan_to_num(values, nan=0.0, posinf=1e6, neginf=-1e6)
        chunks.append(values)
    return np.concatenate(chunks).astype(np.float32)


def feature_names_from_observation(obs, feature_keys=None):
    """Create stable feature names matching observation_to_feature_vector."""
    feature_keys = feature_keys or DEFAULT_FEATURE_KEYS
    names = []
    for key in feature_keys:
        size = int(np.asarray(obs[key]).size)
        safe_key = key.replace(" ", "_")
        names.extend([f"{safe_key}_{index}" for index in range(size)])
    return np.array(names, dtype=object)


def residuals_to_feature_vector(residuals, feature_keys=None):
    """Convert BDD residual channels into a compact learned-detector feature vector."""
    feature_keys = feature_keys or BDD_RESIDUAL_FEATURE_KEYS
    values = [float(residuals.get(key, 0.0)) for key in feature_keys]
    return np.nan_to_num(np.array(values, dtype=np.float32), nan=0.0, posinf=1e6, neginf=-1e6)


def feature_names_from_residuals(feature_keys=None):
    """Create stable feature names for residuals_to_feature_vector."""
    return np.array(list(feature_keys or BDD_RESIDUAL_FEATURE_KEYS), dtype=object)


def save_feature_manifest(path, feature_keys, feature_names):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    manifest = {
        "feature_keys": list(feature_keys),
        "num_features": int(len(feature_names)),
        "feature_names_preview": [str(name) for name in feature_names[:25]],
    }
    path.write_text(json.dumps(manifest, indent=2))
