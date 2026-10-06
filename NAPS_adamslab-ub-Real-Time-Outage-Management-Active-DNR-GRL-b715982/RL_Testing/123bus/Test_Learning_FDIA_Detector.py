"""
Apply a trained learning-based FDIA detector to fresh 123-bus observations.
"""

import argparse
import pickle

import numpy as np

from DSS_OutCtrl_Env import DSS_OutCtrl_Env
from FDIA_Attacks import apply_attack, random_attack_kwargs
from FDIA_Config import ATTACK_NAMES, DATASET_SCENARIOS, DEFAULT_LEARNING_MODEL, resolve_local_path
from FDIA_Features import DEFAULT_FEATURE_KEYS, observation_to_feature_vector
from FDIA_Learning_Models import predict_detector_model


ATTACKS = ATTACK_NAMES
SCENARIOS = DATASET_SCENARIOS


def parse_args():
    parser = argparse.ArgumentParser(description="Test a trained learning-based FDIA detector")
    parser.add_argument(
        "--model",
        default=str(DEFAULT_LEARNING_MODEL),
        help="Model file from Train_FDIA_Detectors.py",
    )
    parser.add_argument("--scenario", default="SC1", choices=sorted(SCENARIOS))
    parser.add_argument("--attacks", nargs="+", default=ATTACKS, choices=ATTACKS)
    parser.add_argument("--seed", type=int, default=2025)
    return parser.parse_args()


def main():
    args = parse_args()
    rng = np.random.default_rng(args.seed)
    model_path = resolve_local_path(args.model)
    with model_path.open("rb") as handle:
        bundle = pickle.load(handle)
    model = bundle["model"]
    label_names = bundle["label_names"]

    env = DSS_OutCtrl_Env()
    clean_obs = getattr(env, SCENARIOS[args.scenario])()

    print(f"Learning detector model: {model_path}")
    print(f"Scenario: {args.scenario}")
    print("Actual case          Predicted case")
    print("-" * 42)

    for attack_name in args.attacks:
        kwargs = random_attack_kwargs(attack_name, rng)
        received_obs, metadata = apply_attack(clean_obs, attack_name, **kwargs)
        X = observation_to_feature_vector(received_obs, DEFAULT_FEATURE_KEYS).reshape(1, -1)
        pred = predict_detector_model(model, X)
        pred_label = label_names[int(pred[0])]
        print(f"{attack_name:<20} {pred_label}")


if __name__ == "__main__":
    main()
