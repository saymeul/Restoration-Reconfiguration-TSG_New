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


def save_feature_manifest(path, feature_keys, feature_names):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    manifest = {
        "feature_keys": list(feature_keys),
        "num_features": int(len(feature_names)),
        "feature_names_preview": [str(name) for name in feature_names[:25]],
    }
    path.write_text(json.dumps(manifest, indent=2))
