"""
Generate a supervised dataset for learning-based FDIA detection.

Each clean OpenDSS outage observation is paired with multiple corrupted
observations. The saved dataset can be used for binary detection
(clean vs attacked) or multiclass attack identification.
"""

import argparse
import json
import random
from collections import Counter

import numpy as np

from DSS_OutCtrl_Env import DSS_OutCtrl_Env
from FDIA_Attacks import apply_attack, random_attack_kwargs
from FDIA_Config import ATTACK_NAMES, DATASET_SCENARIOS, DEFAULT_FDIA_DATASET, resolve_local_path
from FDIA_Features import (
    DEFAULT_FEATURE_KEYS,
    feature_names_from_observation,
    observation_to_feature_vector,
    save_feature_manifest,
)


ATTACKS = ATTACK_NAMES
SCENARIOS = DATASET_SCENARIOS


def get_observation(env, scenario_name):
    return getattr(env, SCENARIOS[scenario_name])()


def parse_args():
    parser = argparse.ArgumentParser(description="Generate 123-bus FDIA learning dataset")
    parser.add_argument("--samples", type=int, default=100, help="Clean samples per scenario")
    parser.add_argument(
        "--scenarios",
        nargs="+",
        default=["SC1", "SC2", "random"],
        choices=sorted(SCENARIOS),
        help="Scenario sources to sample",
    )
    parser.add_argument(
        "--attacks",
        nargs="+",
        default=ATTACKS,
        choices=ATTACKS,
        help="Labels to generate",
    )
    parser.add_argument(
        "--output",
        default=str(DEFAULT_FDIA_DATASET),
        help="Compressed dataset output path",
    )
    parser.add_argument("--seed", type=int, default=1234, help="Random seed")
    return parser.parse_args()


def main():
    args = parse_args()
    random.seed(args.seed)
    np.random.seed(args.seed)
    rng = np.random.default_rng(args.seed)

    env = DSS_OutCtrl_Env()

    features = []
    attack_labels = []
    binary_labels = []
    scenario_labels = []
    sample_ids = []
    attack_metadata = []
    feature_names = None

    for scenario_name in args.scenarios:
        for sample_index in range(args.samples):
            clean_obs = get_observation(env, scenario_name)
            if feature_names is None:
                feature_names = feature_names_from_observation(clean_obs, DEFAULT_FEATURE_KEYS)

            for attack_name in args.attacks:
                kwargs = random_attack_kwargs(attack_name, rng)
                attacked_obs, metadata = apply_attack(clean_obs, attack_name, **kwargs)
                features.append(observation_to_feature_vector(attacked_obs, DEFAULT_FEATURE_KEYS))
                attack_labels.append(attack_name)
                binary_labels.append(0 if attack_name == "clean" else 1)
                scenario_labels.append(scenario_name)
                sample_ids.append(f"{scenario_name}_{sample_index:05d}")
                attack_metadata.append(json.dumps({"params": kwargs, "metadata": metadata}))

            if (sample_index + 1) % 10 == 0:
                print(f"{scenario_name}: generated {sample_index + 1}/{args.samples} clean samples")

    output_path = resolve_local_path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    X = np.vstack(features).astype(np.float32)
    y_attack = np.array(attack_labels, dtype=object)
    y_binary = np.array(binary_labels, dtype=np.int32)
    scenarios = np.array(scenario_labels, dtype=object)

    np.savez_compressed(
        output_path,
        X=X,
        y_attack=y_attack,
        y_binary=y_binary,
        scenarios=scenarios,
        sample_ids=np.array(sample_ids, dtype=object),
        attack_metadata=np.array(attack_metadata, dtype=object),
        feature_keys=np.array(DEFAULT_FEATURE_KEYS, dtype=object),
        feature_names=feature_names,
    )

    save_feature_manifest(output_path.with_suffix(".manifest.json"), DEFAULT_FEATURE_KEYS, feature_names)

    summary = {
        "output": str(output_path),
        "samples": int(X.shape[0]),
        "features": int(X.shape[1]),
        "attack_counts": dict(Counter(attack_labels)),
        "scenario_counts": dict(Counter(scenario_labels)),
    }
    output_path.with_suffix(".summary.json").write_text(json.dumps(summary, indent=2))

    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
