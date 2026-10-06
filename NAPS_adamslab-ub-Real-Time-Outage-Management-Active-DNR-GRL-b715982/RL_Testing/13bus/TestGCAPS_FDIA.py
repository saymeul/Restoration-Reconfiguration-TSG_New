"""
Run clean, attacked, and cyber-resilient GCAPS tests on the 13-bus system.

FDIA is applied only to the cyber observation passed to the policy. The
selected action is always validated on the true OpenDSS feeder state.
"""

import argparse
import csv
import json
import sys
from pathlib import Path
from time import perf_counter

import numpy as np
import torch
from stable_baselines3 import PPO

BASE_DIR = Path(__file__).resolve().parent
RL_TESTING_DIR = BASE_DIR.parent
if str(RL_TESTING_DIR) not in sys.path:
    sys.path.insert(0, str(RL_TESTING_DIR))

from FDIA_Common import (
    ATTACK_NAMES,
    DEFENSE_MODES,
    apply_attack,
    mitigate_observation,
    select_fdia_aware_grl_action,
)
from FDIA_DetectorSuite import load_learning_detectors, run_detector_suite
from DSS_Initialize import dispatch_loads, n_actions
from DSS_OutCtrl_Env import DSS_OutCtrl_Env
from Policies.bus_13.Feature_Extractor import CustomGNN
from Policies.bus_13.CustomPolicies import ActorCriticGCAPSPolicy


FIXED_SCENARIOS = {
    "SC1": "test_func1",
    "SC2": "test_func2",
}
DEFAULT_MODEL = BASE_DIR / "TrainedModels" / "GCAPS_13.zip"
DEFAULT_OUTPUT = BASE_DIR / "paper_results" / "fdia_13_defended_results.csv"
DEFAULT_DETECTOR_DIR = BASE_DIR / "paper_results" / "learning_detectors"
NUM_SWITCHES = n_actions - len(dispatch_loads)


def resolve_local_path(path):
    candidate = Path(path)
    if candidate.is_absolute():
        return candidate
    return BASE_DIR / candidate


def observation_to_tensor(obs, device):
    return {
        key: torch.as_tensor(np.expand_dims(np.asarray(value), axis=0), dtype=torch.float32, device=device)
        for key, value in obs.items()
    }


def predict_action(model, obs):
    obs_tensor = observation_to_tensor(obs, model.device)
    start = perf_counter()
    with torch.no_grad():
        action, values, log_probs = model.policy.forward(obs_tensor)
    elapsed_ms = (perf_counter() - start) * 1000.0
    return action[0, :].detach().cpu().numpy().astype(int), elapsed_ms


def calculate_energy_kw(dssckt_obj):
    energy_supplied = 0.0
    total_demand = 0.0
    for load_name in list(dssckt_obj.dss.Loads.AllNames()):
        dssckt_obj.dss.Circuit.SetActiveElement(f"Load.{load_name}")
        powers = np.array(dssckt_obj.dss.CktElement.Powers())
        active_indices = 2 * np.array(range(0, min(int(powers.size / 2), 3)))
        active_power = np.nan_to_num(powers[active_indices], nan=0.0, posinf=0.0, neginf=0.0)
        energy_supplied += float(np.sum(active_power))
        total_demand += float(dssckt_obj.dss.Properties.Value("kW"))

    ratio = energy_supplied / total_demand if total_demand else 0.0
    return energy_supplied, total_demand, ratio


def split_action(action):
    switches = [int(value) for value in action[:NUM_SWITCHES]]
    load_values = [int(value) for value in action[NUM_SWITCHES:]]
    load_status = {load: load_values[index] for index, load in enumerate(dispatch_loads)}
    return switches, load_status


def evaluate_action(env, scenario_func_name, action):
    getattr(env, scenario_func_name)()
    obs_post_action, reward, done, info = env.step(action)
    energy_kw, total_demand_kw, energy_ratio = calculate_energy_kw(env.DSSCktObj)
    return {
        "reward": float(reward),
        "done": bool(done),
        "energy_kw": energy_kw,
        "total_demand_kw": total_demand_kw,
        "energy_ratio": energy_ratio,
        "voltage_violation": float(obs_post_action["VoltageViolation"].reshape(-1)[0]),
        "convergence_violation": float(obs_post_action["ConvergenceViolation"].reshape(-1)[0]),
    }


def physical_impact(metrics, loads_served, clean_reference):
    if clean_reference is None:
        energy_kw_delta = 0.0
        energy_ratio_delta = 0.0
        voltage_violation_delta = 0.0
        reward_delta = 0.0
        loads_served_delta = 0
    else:
        energy_kw_delta = metrics["energy_kw"] - clean_reference["energy_kw"]
        energy_ratio_delta = metrics["energy_ratio"] - clean_reference["energy_ratio"]
        voltage_violation_delta = metrics["voltage_violation"] - clean_reference["voltage_violation"]
        reward_delta = metrics["reward"] - clean_reference["reward"]
        loads_served_delta = loads_served - clean_reference["loads_served"]

    impact_score = (
        max(0.0, -energy_ratio_delta)
        + max(0.0, voltage_violation_delta)
        + max(0.0, -reward_delta)
    )
    return {
        "energy_kw_delta_vs_clean": energy_kw_delta,
        "energy_ratio_delta_vs_clean": energy_ratio_delta,
        "voltage_violation_delta_vs_clean": voltage_violation_delta,
        "reward_delta_vs_clean": reward_delta,
        "loads_served_delta_vs_clean": loads_served_delta,
        "physical_impact_score": impact_score,
    }


def run_case(
    env,
    model,
    scenario_name,
    scenario_func_name,
    attack_name,
    clean_action=None,
    clean_reference=None,
    defense_mode="unmitigated",
    learning_detectors=None,
    learning_vote_threshold=0.50,
):
    true_obs = getattr(env, scenario_func_name)()
    policy_obs, attack_metadata = apply_attack(true_obs, attack_name)
    detection = run_detector_suite(
        true_obs,
        policy_obs,
        learning_detectors,
        min_learning_vote_fraction=learning_vote_threshold,
    )
    post_mitigation_detection = detection
    mitigation_metadata = {
        "strategy": "none",
        "mitigation_applied": False,
        "mitigated_channels": [],
        "mitigated_keys": [],
        "reference_source": "none",
    }
    fdia_aware_metadata = {
        "strategy": "none",
        "attack_aware": False,
        "screening_model": "none",
        "selection_objective": "none",
        "selected_candidate": "none",
        "candidate_count": 0,
        "candidate_names": [],
        "detector_gate": False,
    }
    candidate_actions = []
    inference_obs = policy_obs

    if defense_mode in ("mitigated", "fdia_aware") and attack_name != "clean":
        inference_obs, mitigation_metadata = mitigate_observation(true_obs, policy_obs, detection)
        post_mitigation_detection = run_detector_suite(
            true_obs,
            inference_obs,
            learning_detectors,
            min_learning_vote_fraction=learning_vote_threshold,
        )

    if defense_mode == "fdia_aware" and attack_name != "clean":
        decision = select_fdia_aware_grl_action(
            lambda obs: predict_action(model, obs),
            lambda action: evaluate_action(env, scenario_func_name, action),
            policy_obs,
            inference_obs,
            detection,
            NUM_SWITCHES,
        )
        action = decision["action"]
        metrics = decision["metrics"]
        policy_time_ms = decision["policy_time_ms"]
        decision_time_ms = decision["decision_time_ms"]
        screening_time_ms = decision["screening_time_ms"]
        selected_candidate = decision["selected_candidate"]
        candidate_actions = decision["candidate_actions"]
        fdia_aware_metadata = decision["fdia_aware_metadata"]
        mitigation_metadata = dict(mitigation_metadata)
        mitigation_metadata["action_screening"] = fdia_aware_metadata
    else:
        action, policy_time_ms = predict_action(model, inference_obs)
        metrics = evaluate_action(env, scenario_func_name, action)
        decision_time_ms = policy_time_ms
        screening_time_ms = 0.0
        if attack_name == "clean":
            selected_candidate = "clean_observation_grl"
        elif defense_mode == "mitigated":
            selected_candidate = "detector_mitigated_observation_grl"
        else:
            selected_candidate = "attacked_observation_grl"

    switches, load_status = split_action(action)

    if clean_action is None:
        switch_changes = 0
        load_changes = 0
        action_changed = 0
    else:
        switch_changes = int(np.sum(action[:NUM_SWITCHES] != clean_action[:NUM_SWITCHES]))
        load_changes = int(np.sum(action[NUM_SWITCHES:] != clean_action[NUM_SWITCHES:]))
        action_changed = int(np.any(action != clean_action))

    loads_served = int(np.sum(action[NUM_SWITCHES:]))
    loads_shed = len(dispatch_loads) - loads_served
    impact = physical_impact(metrics, loads_served, clean_reference)

    return {
        "method": "GRL",
        "system": "13bus",
        "scenario": scenario_name,
        "case": attack_name,
        "defense_mode": "clean" if attack_name == "clean" else defense_mode,
        "energy_kw": metrics["energy_kw"],
        "total_demand_kw": metrics["total_demand_kw"],
        "energy_ratio": metrics["energy_ratio"],
        "voltage_violation": metrics["voltage_violation"],
        "convergence_violation": metrics["convergence_violation"],
        "reward": metrics["reward"],
        "policy_time_ms": policy_time_ms,
        "decision_time_ms": decision_time_ms,
        "screening_time_ms": screening_time_ms,
        "loads_served": loads_served,
        "loads_shed": loads_shed,
        **impact,
        "closed_switches": int(np.sum(action[:NUM_SWITCHES])),
        "open_switches": NUM_SWITCHES - int(np.sum(action[:NUM_SWITCHES])),
        "action_changed": action_changed,
        "switch_changes_vs_clean": switch_changes,
        "load_changes_vs_clean": load_changes,
        "switch_vector": switches,
        "load_status": load_status,
        "attack_metadata": attack_metadata,
        "mitigation_metadata": mitigation_metadata,
        "mitigation_applied": int(mitigation_metadata["mitigation_applied"]),
        "mitigated_channels": mitigation_metadata["mitigated_channels"],
        "mitigated_keys": mitigation_metadata["mitigated_keys"],
        "selected_candidate": selected_candidate,
        "candidate_actions": candidate_actions,
        "fdia_aware_metadata": fdia_aware_metadata,
        "fdia_detected": int(detection["detected"]),
        "detector_score": detection["score"],
        "detected_channels": detection["detected_channels"],
        "detector_residuals": detection["residuals"],
        "bdd_fdia_detected": int(detection["bdd_report"]["detected"]),
        "bdd_detector_score": detection["bdd_report"]["score"],
        "bdd_detected_channels": detection["bdd_report"]["detected_channels"],
        "bdd_detector_residuals": detection["bdd_report"]["residuals"],
        "learning_fdia_detected": int(detection["learning_detected"]),
        "learning_any_fdia_detected": int(detection["learning_any_detected"]),
        "learning_vote_fraction": detection["learning_vote_fraction"],
        "learning_vote_threshold": detection["learning_vote_threshold"],
        "learning_detected_count": detection["learning_detected_count"],
        "learning_detector_count": detection["learning_detector_count"],
        "learning_predicted_attacks": detection["learning_predicted_attacks"],
        "learning_detected_channels": detection["learning_detected_channels"],
        "learning_raw_detected_channels": detection["learning_raw_detected_channels"],
        "learning_detector_reports": detection["learning_reports"],
        "post_mitigation_fdia_detected": int(post_mitigation_detection["detected"]),
        "post_mitigation_detector_score": post_mitigation_detection["score"],
        "post_mitigation_detected_channels": post_mitigation_detection["detected_channels"],
        "post_mitigation_detector_residuals": post_mitigation_detection["residuals"],
        "post_mitigation_bdd_fdia_detected": int(post_mitigation_detection["bdd_report"]["detected"]),
        "post_mitigation_learning_fdia_detected": int(post_mitigation_detection["learning_detected"]),
        "post_mitigation_learning_any_fdia_detected": int(post_mitigation_detection["learning_any_detected"]),
        "post_mitigation_learning_vote_fraction": post_mitigation_detection["learning_vote_fraction"],
        "post_mitigation_learning_detected_count": post_mitigation_detection["learning_detected_count"],
        "post_mitigation_learning_detector_reports": post_mitigation_detection["learning_reports"],
        "action_array": action,
    }


FIELDS = [
    "method",
    "system",
    "scenario",
    "case",
    "defense_mode",
    "energy_kw",
    "total_demand_kw",
    "energy_ratio",
    "voltage_violation",
    "convergence_violation",
    "reward",
    "policy_time_ms",
    "decision_time_ms",
    "screening_time_ms",
    "loads_served",
    "loads_shed",
    "energy_kw_delta_vs_clean",
    "energy_ratio_delta_vs_clean",
    "voltage_violation_delta_vs_clean",
    "reward_delta_vs_clean",
    "loads_served_delta_vs_clean",
    "physical_impact_score",
    "closed_switches",
    "open_switches",
    "action_changed",
    "switch_changes_vs_clean",
    "load_changes_vs_clean",
    "switch_vector",
    "load_status",
    "attack_metadata",
    "mitigation_metadata",
    "mitigation_applied",
    "mitigated_channels",
    "mitigated_keys",
    "selected_candidate",
    "candidate_actions",
    "fdia_aware_metadata",
    "fdia_detected",
    "detector_score",
    "detected_channels",
    "detector_residuals",
    "bdd_fdia_detected",
    "bdd_detector_score",
    "bdd_detected_channels",
    "bdd_detector_residuals",
    "learning_fdia_detected",
    "learning_any_fdia_detected",
    "learning_vote_fraction",
    "learning_vote_threshold",
    "learning_detected_count",
    "learning_detector_count",
    "learning_predicted_attacks",
    "learning_detected_channels",
    "learning_raw_detected_channels",
    "learning_detector_reports",
    "post_mitigation_fdia_detected",
    "post_mitigation_detector_score",
    "post_mitigation_detected_channels",
    "post_mitigation_detector_residuals",
    "post_mitigation_bdd_fdia_detected",
    "post_mitigation_learning_fdia_detected",
    "post_mitigation_learning_any_fdia_detected",
    "post_mitigation_learning_vote_fraction",
    "post_mitigation_learning_detected_count",
    "post_mitigation_learning_detector_reports",
]


def print_result(row):
    print(
        f"{row['scenario']:>3} | {row['case']:<18} | {row['defense_mode']:<11} | "
        f"energy_ratio={row['energy_ratio']:.6f} | "
        f"voltage_violation={row['voltage_violation']:.6f} | "
        f"impact={row['physical_impact_score']:.6f} | "
        f"loads_served={row['loads_served']:>2}/{len(dispatch_loads)} | "
        f"bdd={row['bdd_fdia_detected']} | "
        f"learn={row['learning_fdia_detected']}({row['learning_detected_count']}/{row['learning_detector_count']}) | "
        f"fused={row['fdia_detected']} | mitigated={row['mitigation_applied']} | "
        f"selected={row['selected_candidate']} | "
        f"action_changed={row['action_changed']} | decision_ms={row['decision_time_ms']:.3f}"
    )


def write_csv(rows, output_path):
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        for row in rows:
            csv_row = {field: row[field] for field in FIELDS}
            for key in (
                "switch_vector",
                "load_status",
                "attack_metadata",
                "mitigation_metadata",
                "mitigated_channels",
                "mitigated_keys",
                "candidate_actions",
                "fdia_aware_metadata",
                "detected_channels",
                "detector_residuals",
                "bdd_detected_channels",
                "bdd_detector_residuals",
                "learning_predicted_attacks",
                "learning_detected_channels",
                "learning_raw_detected_channels",
                "learning_detector_reports",
                "post_mitigation_detected_channels",
                "post_mitigation_detector_residuals",
                "post_mitigation_learning_detector_reports",
            ):
                csv_row[key] = json.dumps(csv_row[key])
            writer.writerow(csv_row)


def parse_args():
    parser = argparse.ArgumentParser(description="13-bus cyber-resilient GCAPS FDIA test")
    parser.add_argument("--scenarios", nargs="+", default=["SC1", "SC2"], choices=sorted(FIXED_SCENARIOS))
    parser.add_argument("--attacks", nargs="+", default=ATTACK_NAMES, choices=ATTACK_NAMES)
    parser.add_argument("--defense-modes", nargs="+", default=DEFENSE_MODES, choices=DEFENSE_MODES)
    parser.add_argument("--model", default=str(DEFAULT_MODEL), help="Path to trained GCAPS model")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT), help="CSV output path")
    parser.add_argument(
        "--learning-detector-dir",
        default=str(DEFAULT_DETECTOR_DIR),
        help="Directory containing trained learning-based FDIA detectors",
    )
    parser.add_argument(
        "--learning-detector-tasks",
        nargs="+",
        default=["binary", "multiclass"],
        choices=["binary", "multiclass"],
        help="Learning detector task groups to load",
    )
    parser.add_argument(
        "--learning-detector-models",
        nargs="+",
        default=["centroid", "knn", "linear_torch", "mlp_torch"],
        choices=["centroid", "knn", "linear_torch", "mlp_torch"],
        help="Learning detector model types to load",
    )
    parser.add_argument(
        "--disable-learning-detectors",
        action="store_true",
        help="Use only residual BDD detection",
    )
    parser.add_argument(
        "--learning-vote-threshold",
        type=float,
        default=0.50,
        help="Minimum fraction of learning detectors that must vote attack before fused detection trusts learning evidence",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    env = DSS_OutCtrl_Env()
    model = PPO.load(str(resolve_local_path(args.model)), env=env)
    learning_detectors = []
    if not args.disable_learning_detectors:
        learning_detectors = load_learning_detectors(
            resolve_local_path(args.learning_detector_dir),
            tasks=args.learning_detector_tasks,
            model_names=args.learning_detector_models,
        )

    rows = []
    print("\n13-bus cyber-resilient GCAPS FDIA test")
    print(f"Loaded learning detectors: {len(learning_detectors)} | vote_threshold={args.learning_vote_threshold:.2f}")
    print("Scenario | Case               | Defense     | Metrics")
    print("-" * 136)

    for scenario_name in args.scenarios:
        scenario_func_name = FIXED_SCENARIOS[scenario_name]
        clean_row = run_case(
            env,
            model,
            scenario_name,
            scenario_func_name,
            "clean",
            learning_detectors=learning_detectors,
            learning_vote_threshold=args.learning_vote_threshold,
        )
        rows.append(clean_row)
        print_result(clean_row)
        clean_action = clean_row["action_array"]

        for attack_name in args.attacks:
            if attack_name == "clean":
                continue
            for defense_mode in args.defense_modes:
                row = run_case(
                    env,
                    model,
                    scenario_name,
                    scenario_func_name,
                    attack_name,
                    clean_action=clean_action,
                    clean_reference=clean_row,
                    defense_mode=defense_mode,
                    learning_detectors=learning_detectors,
                    learning_vote_threshold=args.learning_vote_threshold,
                )
                rows.append(row)
                print_result(row)

    output_path = resolve_local_path(args.output)
    write_csv(rows, output_path)
    print(f"\nSaved paper-ready CSV: {output_path}")


if __name__ == "__main__":
    main()
