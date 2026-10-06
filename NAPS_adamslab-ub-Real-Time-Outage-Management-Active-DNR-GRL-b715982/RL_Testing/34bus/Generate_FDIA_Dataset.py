"""
Generate a 34-bus FDIA dataset for learning-based detectors.
"""

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

import numpy as np

BASE_DIR = Path(__file__).resolve().parent
RL_TESTING_DIR = BASE_DIR.parent
if str(RL_TESTING_DIR) not in sys.path:
    sys.path.insert(0, str(RL_TESTING_DIR))

from FDIA_Common import ATTACK_NAMES, apply_attack, detect_fdia, random_attack_kwargs
from FDIA_Features import (
    BDD_RESIDUAL_FEATURE_KEYS,
    DEFAULT_FEATURE_KEYS,
    feature_names_from_observation,
    feature_names_from_residuals,
    observation_to_feature_vector,
    residuals_to_feature_vector,
    save_feature_manifest,
)
from DSS_OutCtrl_Env import DSS_OutCtrl_Env


SCENARIOS = {
    "SC1": "test_func1",
    "SC2": "test_func2",
    "random": "reset",
}
DEFAULT_OUTPUT = BASE_DIR / "paper_results" / "fdia_learning_dataset_34.npz"


def get_observation(env, scenario_name):
    return getattr(env, SCENARIOS[scenario_name])()


def parse_args():
    parser = argparse.ArgumentParser(description="Generate 34-bus FDIA learning dataset")
    parser.add_argument("--samples-per-scenario", type=int, default=25)
    parser.add_argument("--seed", type=int, default=1234)
    parser.add_argument("--scenarios", nargs="+", default=list(SCENARIOS), choices=sorted(SCENARIOS))
    parser.add_argument("--attacks", nargs="+", default=ATTACK_NAMES, choices=ATTACK_NAMES)
    parser.add_argument(
        "--feature-mode",
        choices=["bdd_residuals", "observation"],
        default="bdd_residuals",
        help="Feature representation used by learning detectors",
    )
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    return parser.parse_args()


def main():
    args = parse_args()
    rng = np.random.default_rng(args.seed)
    env = DSS_OutCtrl_Env()

    features = []
    attack_labels = []
    binary_labels = []
    scenario_labels = []
    feature_names = None

    for scenario_name in args.scenarios:
        for _sample in range(args.samples_per_scenario):
            clean_obs = get_observation(env, scenario_name)
            if feature_names is None:
                if args.feature_mode == "bdd_residuals":
                    feature_names = feature_names_from_residuals(BDD_RESIDUAL_FEATURE_KEYS)
                else:
                    feature_names = feature_names_from_observation(clean_obs, DEFAULT_FEATURE_KEYS)
            for attack_name in args.attacks:
                kwargs = random_attack_kwargs(attack_name, rng)
                attacked_obs, _metadata = apply_attack(clean_obs, attack_name, **kwargs)
                if args.feature_mode == "bdd_residuals":
                    residual_report = detect_fdia(clean_obs, attacked_obs)
                    features.append(residuals_to_feature_vector(residual_report["residuals"], BDD_RESIDUAL_FEATURE_KEYS))
                else:
                    features.append(observation_to_feature_vector(attacked_obs, DEFAULT_FEATURE_KEYS))
                attack_labels.append(attack_name)
                binary_labels.append(0 if attack_name == "clean" else 1)
                scenario_labels.append(scenario_name)

    output_path = Path(args.output)
    if not output_path.is_absolute():
        output_path = BASE_DIR / output_path
    output_path.parent.mkdir(parents=True, exist_ok=True)

    X = np.vstack(features).astype(np.float32)
    np.savez_compressed(
        output_path,
        X=X,
        y_attack=np.array(attack_labels, dtype=object),
        y_binary=np.array(binary_labels, dtype=np.int32),
        scenarios=np.array(scenario_labels, dtype=object),
        feature_keys=np.array(
            BDD_RESIDUAL_FEATURE_KEYS if args.feature_mode == "bdd_residuals" else DEFAULT_FEATURE_KEYS,
            dtype=object,
        ),
        feature_mode=np.array(args.feature_mode, dtype=object),
    )
    save_feature_manifest(
        output_path.with_suffix(".manifest.json"),
        BDD_RESIDUAL_FEATURE_KEYS if args.feature_mode == "bdd_residuals" else DEFAULT_FEATURE_KEYS,
        feature_names,
    )
    metadata = {
        "samples": int(X.shape[0]),
        "features": int(X.shape[1]),
        "feature_mode": args.feature_mode,
        "attack_counts": dict(Counter(attack_labels)),
        "scenario_counts": dict(Counter(scenario_labels)),
    }
    output_path.with_suffix(".metadata.json").write_text(json.dumps(metadata, indent=2))
    print(f"Saved 34-bus FDIA dataset: {output_path}")


if __name__ == "__main__":
    main()
